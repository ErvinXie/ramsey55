#!/usr/bin/env python3
"""Remove exactly one directory after re-auditing its recoverable archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from typing import Any

from archive_zstd_directory import fsync_directory, write_json_atomic
from audit_zstd_directory_archive import (
    AUDIT_SCHEMA,
    audit,
    file_record,
    load_document,
)


RECEIPT_SCHEMA = "ramsey55.zstd-directory-source-removal.v1"


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def process_references(source: Path) -> list[dict[str, object]]:
    references: list[dict[str, object]] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return references
    for process in proc.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        hits: list[str] = []
        try:
            cwd = Path(os.readlink(process / "cwd"))
            if cwd == source or _under(cwd, source):
                hits.append("cwd")
        except OSError:
            pass
        try:
            for descriptor in (process / "fd").iterdir():
                try:
                    target = Path(os.readlink(descriptor))
                except OSError:
                    continue
                if target == source or _under(target, source):
                    hits.append("fd")
                    break
        except OSError:
            pass
        if hits:
            try:
                command = (process / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                    "utf-8", errors="replace"
                )
            except OSError:
                command = ""
            references.append(
                {"pid": int(process.name), "references": hits, "command": command}
            )
    return references


def nested_mounts(source: Path) -> list[str]:
    mountinfo = Path("/proc/self/mountinfo")
    if not mountinfo.is_file():
        return []
    mounts = []
    for line in mountinfo.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 5:
            continue
        mount = Path(
            fields[4]
            .replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )
        if mount == source or _under(mount, source):
            mounts.append(str(mount))
    return mounts


def remove_source(
    manifest: Path,
    prior_audit_path: Path,
    allowed_parent: Path,
    receipt: Path,
    zstd: Path | None = None,
    tar: Path | None = None,
) -> dict[str, Any]:
    if not allowed_parent.is_absolute() or allowed_parent.is_symlink() or not allowed_parent.is_dir():
        raise ValueError(f"invalid allowed parent: {allowed_parent}")
    if allowed_parent.resolve(strict=True) != allowed_parent:
        raise ValueError(f"allowed parent has symbolic-link components: {allowed_parent}")
    if not receipt.is_absolute() or not receipt.parent.is_dir():
        raise ValueError(f"invalid receipt path: {receipt}")

    prior = load_document(prior_audit_path)
    if (
        prior.get("schema") != AUDIT_SCHEMA
        or prior.get("verified") is not True
        or prior.get("source_compared") is not True
    ):
        raise ValueError("prior audit did not compare and verify the source")
    if prior.get("manifest") != file_record(manifest):
        raise ValueError("prior audit is not bound to this manifest")

    current = audit(manifest, zstd, tar, require_source=True)
    if not current.get("verified") or not current.get("source_compared"):
        raise ValueError("current archive audit did not compare and verify the source")
    for field in ("source", "archive", "provenance", "payload"):
        if current.get(field) != prior.get(field):
            raise ValueError(f"current audit disagrees with prior audit: {field}")

    source = Path(current["source"]["path"])
    if source.parent != allowed_parent:
        raise ValueError(
            f"source is not an immediate child of allowed parent: {source}"
        )
    if source.is_symlink() or not source.is_dir() or source.resolve(strict=True) != source:
        raise ValueError(f"source is not an exact non-symlink directory: {source}")
    references = process_references(source)
    if references:
        raise ValueError(f"active processes reference source: {references}")
    mounts = nested_mounts(source)
    if mounts:
        raise ValueError(f"refusing to cross mounted filesystems: {mounts}")

    source_stats = source.stat()
    shutil.rmtree(source)
    if source.exists() or source.is_symlink():
        raise RuntimeError(f"source still exists after removal: {source}")
    fsync_directory(allowed_parent)
    document = {
        "schema": RECEIPT_SCHEMA,
        "removed_at": datetime.now(timezone.utc).isoformat(),
        "source": current["source"],
        "source_inode_before": source_stats.st_ino,
        "source_device_before": source_stats.st_dev,
        "archive": current["archive"],
        "manifest": current["manifest"],
        "prior_audit": file_record(prior_audit_path),
        "current_audit": current,
        "recoverable": True,
        "source_absent_after": True,
    }
    write_json_atomic(receipt, document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("prior_audit", type=Path)
    parser.add_argument("--allowed-parent", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--zstd", type=Path)
    parser.add_argument("--tar", type=Path)
    parser.add_argument(
        "--acknowledge-verified-source-removal",
        required=True,
        choices=["YES"],
    )
    arguments = parser.parse_args()
    print(
        json.dumps(
            remove_source(
                arguments.manifest,
                arguments.prior_audit,
                arguments.allowed_parent,
                arguments.receipt,
                arguments.zstd,
                arguments.tar,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
