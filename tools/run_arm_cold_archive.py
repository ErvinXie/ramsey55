#!/usr/bin/env python3
"""Run the resumable, audited ARM cold-archive plan one directory at a time."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import time
from typing import Any

from archive_zstd_directory import create_archive, write_json_atomic
from audit_zstd_directory_archive import file_record, file_sha256, load_document
from remove_verified_directory_archive_source import (
    RECEIPT_SCHEMA,
    remove_source,
)


PLAN_SCHEMA = "ramsey55.arm-cold-archive-plan.v1"
COMPLETION_SCHEMA = "ramsey55.arm-cold-archive-completion.v1"
GIB = 1 << 30


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_absolute(path: Path, label: str) -> None:
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute: {path}")


def load_plan(path: Path, expected_sha256: str) -> dict[str, Any]:
    require_absolute(path, "plan")
    if file_sha256(path) != expected_sha256:
        raise ValueError("archive plan SHA-256 mismatch")
    document = load_document(path)
    if document.get("schema") != PLAN_SCHEMA:
        raise ValueError("unexpected archive plan schema")
    snapshot_record = document.get("snapshot")
    if not isinstance(snapshot_record, dict):
        raise ValueError("archive plan has no snapshot record")
    snapshot_path = Path(str(snapshot_record.get("path", "")))
    if file_record(snapshot_path) != snapshot_record:
        raise ValueError("archive plan snapshot mismatch")
    phases = document.get("phases")
    if not isinstance(phases, list) or not phases:
        raise ValueError("archive plan has no phases")
    names: set[str] = set()
    sources: set[str] = set()
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("invalid archive phase")
        name = phase.get("name")
        if not isinstance(name, str) or not name or name in names or "/" in name:
            raise ValueError("invalid or duplicate archive phase name")
        names.add(name)
        kind = phase.get("kind")
        if kind == "children":
            parent = Path(str(phase.get("parent", "")))
            require_absolute(parent, "phase parent")
            children = phase.get("children")
            if not isinstance(children, list) or not children:
                raise ValueError(f"children phase is empty: {name}")
            for child in children:
                if (
                    not isinstance(child, str)
                    or not child
                    or child in (".", "..")
                    or "/" in child
                ):
                    raise ValueError(f"invalid child name in phase {name}")
                source = str(parent / child)
                if source in sources:
                    raise ValueError(f"duplicate archive source: {source}")
                sources.add(source)
        elif kind == "directory":
            source_path = Path(str(phase.get("source", "")))
            require_absolute(source_path, "phase source")
            source = str(source_path)
            if source in sources:
                raise ValueError(f"duplicate archive source: {source}")
            sources.add(source)
        else:
            raise ValueError(f"invalid archive phase kind: {kind}")
    return document


def iter_phase_sources(phase: dict[str, Any]):
    if phase["kind"] == "children":
        parent = Path(phase["parent"])
        for child in phase["children"]:
            yield parent / child
    else:
        yield Path(phase["source"])


def append_event(path: Path, event: dict[str, Any]) -> None:
    payload = (json.dumps(event, sort_keys=True) + "\n").encode()
    with path.open("ab") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def available_bytes(path: Path) -> int:
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize


def source_allocated_bytes(source: Path) -> int:
    total = source.lstat().st_blocks * 512
    pending = [source]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                stat = entry.stat(follow_symlinks=False)
                total += stat.st_blocks * 512
                if entry.is_dir(follow_symlinks=False) and not entry.is_symlink():
                    pending.append(Path(entry.path))
    return total


def validate_completed_receipt(receipt_path: Path, source: Path) -> dict[str, Any]:
    receipt = load_document(receipt_path)
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("recoverable") is not True
        or receipt.get("source_absent_after") is not True
        or not isinstance(receipt.get("source"), dict)
        or receipt["source"].get("path") != str(source)
    ):
        raise ValueError(f"invalid source-removal receipt: {receipt_path}")
    return receipt


def archive_one(
    source: Path,
    phase_name: str,
    archive_root: Path,
    provenance: Path,
    zstd: Path,
    tar: Path,
    level: int,
    threads: int,
    ledger: Path,
) -> dict[str, Any]:
    shard_root = archive_root / "shards" / phase_name / source.name
    archive = shard_root / "payload.tar.zst"
    manifest = shard_root / "manifest.json"
    audit_path = shard_root / "audit.json"
    receipt = shard_root / "removal.json"
    temporary = archive.with_name(archive.name + ".tmp")

    if receipt.exists():
        if source.exists() or source.is_symlink():
            raise ValueError(f"source exists despite removal receipt: {source}")
        document = validate_completed_receipt(receipt, source)
        for path in (archive, manifest, audit_path):
            if not path.is_file():
                raise ValueError(f"completed shard is missing artifact: {path}")
        return {"status": "already-complete", "receipt": document}

    if not source.is_dir() or source.is_symlink():
        raise ValueError(f"unarchived source directory is missing: {source}")
    shard_root.mkdir(parents=True, exist_ok=True)
    if temporary.exists():
        if archive.exists() or manifest.exists() or audit_path.exists():
            raise ValueError(f"ambiguous interrupted archive state: {shard_root}")
        temporary.unlink()
        append_event(
            ledger,
            {
                "at": utc_now(),
                "event": "removed-incomplete-temporary",
                "phase": phase_name,
                "source": str(source),
            },
        )

    outputs = [archive.exists(), manifest.exists(), audit_path.exists()]
    if any(outputs) and not all(outputs):
        raise ValueError(f"partial published archive state: {shard_root}")

    allocated = source_allocated_bytes(source)
    free_before = available_bytes(archive_root)
    if not all(outputs):
        if free_before < allocated + GIB:
            raise RuntimeError(
                f"insufficient free space for worst-case shard: source={allocated} "
                f"available={free_before} path={source}"
            )
        append_event(
            ledger,
            {
                "at": utc_now(),
                "event": "archive-start",
                "phase": phase_name,
                "source": str(source),
                "allocated_bytes": allocated,
                "available_bytes": free_before,
            },
        )
        create_archive(
            source,
            provenance,
            archive,
            manifest,
            audit_path,
            zstd,
            tar,
            level,
            threads,
        )
        append_event(
            ledger,
            {
                "at": utc_now(),
                "event": "archive-audited",
                "phase": phase_name,
                "source": str(source),
                "archive": file_record(archive),
                "manifest": file_record(manifest),
                "audit": file_record(audit_path),
            },
        )

    removal = remove_source(
        manifest,
        audit_path,
        source.parent,
        receipt,
        zstd,
        tar,
    )
    append_event(
        ledger,
        {
            "at": utc_now(),
            "event": "source-removed",
            "phase": phase_name,
            "source": str(source),
            "archive": removal["archive"],
            "receipt": file_record(receipt),
            "available_bytes": available_bytes(archive_root),
        },
    )
    return {"status": "completed", "receipt": removal}


def run(
    plan_path: Path,
    expected_plan_sha256: str,
    archive_root: Path,
    zstd: Path,
    tar: Path,
    level: int,
    threads: int,
    check_only: bool = False,
) -> dict[str, Any]:
    plan = load_plan(plan_path, expected_plan_sha256)
    if Path(plan.get("archive_root", "")) != archive_root:
        raise ValueError("archive root does not match plan")
    if not archive_root.is_dir() or archive_root.is_symlink():
        raise ValueError(f"invalid archive root: {archive_root}")
    if plan_path.parent != archive_root:
        raise ValueError("plan must be stored directly in archive root")

    total = sum(
        1 for phase in plan["phases"] for _ in iter_phase_sources(phase)
    )
    if check_only:
        return {
            "schema": PLAN_SCHEMA,
            "plan": file_record(plan_path),
            "phases": len(plan["phases"]),
            "shards": total,
            "verified": True,
        }

    ledger = archive_root / "ledger.jsonl"
    completion = archive_root / "completion.json"
    if completion.exists():
        return load_document(completion)

    started = time.monotonic()
    completed = 0
    skipped = 0
    for phase in plan["phases"]:
        for source in iter_phase_sources(phase):
            result = archive_one(
                source,
                phase["name"],
                archive_root,
                plan_path,
                zstd,
                tar,
                level,
                threads,
                ledger,
            )
            if result["status"] == "already-complete":
                skipped += 1
            else:
                completed += 1

    receipts = sorted((archive_root / "shards").glob("*/*/removal.json"))
    if len(receipts) != total:
        raise ValueError(f"completion receipt count mismatch: {len(receipts)} != {total}")
    for phase in plan["phases"]:
        for source in iter_phase_sources(phase):
            if source.exists() or source.is_symlink():
                raise ValueError(f"source remains after archive completion: {source}")

    document = {
        "schema": COMPLETION_SCHEMA,
        "completed_at": utc_now(),
        "elapsed_seconds_this_run": time.monotonic() - started,
        "plan": file_record(plan_path),
        "snapshot": plan["snapshot"],
        "ledger": file_record(ledger),
        "shards": total,
        "completed_this_run": completed,
        "already_complete_this_run": skipped,
        "archive_payload_bytes": sum(
            path.stat().st_size
            for path in (archive_root / "shards").glob("*/*/payload.tar.zst")
        ),
        "available_bytes_after": available_bytes(archive_root),
        "verified": True,
    }
    write_json_atomic(completion, document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--zstd", type=Path, default=Path("/usr/bin/zstd"))
    parser.add_argument("--tar", type=Path, default=Path("/usr/bin/tar"))
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--check-plan-only", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            run(
                arguments.plan,
                arguments.plan_sha256,
                arguments.archive_root,
                arguments.zstd,
                arguments.tar,
                arguments.level,
                arguments.threads,
                arguments.check_plan_only,
            ),
            sort_keys=True,
        )
    )


def _raise_interrupted(signum, frame) -> None:
    del frame
    raise InterruptedError(f"received signal {signum}")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _raise_interrupted)
    signal.signal(signal.SIGINT, _raise_interrupted)
    main()
