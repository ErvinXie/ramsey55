#!/usr/bin/env python3
"""Independently audit a finalized CaDiCaL DFS checkpoint composition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

AUDIT_SCHEMA = "ramsey55.cadical-dfs-checkpoint-finalization-audit.v1"
FINALIZATION_SCHEMA = "ramsey55.cadical-dfs-checkpoint-finalization.v1"
PROMOTION_SCHEMA = "ramsey55.checked-binary-drat-fragment-promotion.v1"
REPLAY_SCHEMA = "ramsey55.cadical-dfs-prefix-replay.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_file_record(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"finalization manifest lacks {label} file record")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise ValueError(f"finalization manifest has invalid {label} path")
    digest = record.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"finalization manifest has invalid {label} hash")
    if not isinstance(record.get("size"), int) or record["size"] < 0:
        raise ValueError(f"finalization manifest has invalid {label} size")
    return record


def read_producer_log(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        fields = raw.split("\t", 1)
        if len(fields) != 2 or not fields[0] or fields[0] in records:
            raise ValueError(f"invalid producer log row {line_number}: {path}")
        records[fields[0]] = fields[1]
    required = {
        "proof_fragment": "1",
        "root_index": "all",
        "status": "20",
        "cubes": "1",
    }
    for key, expected in required.items():
        if records.get(key) != expected:
            raise ValueError(f"producer log {path} lacks {key}={expected}")
    for key in ("attempts", "splits", "maximum_extra_depth"):
        value = records.get(key)
        if value is None:
            raise ValueError(f"producer log {path} lacks {key}")
        try:
            nonnegative = int(value) >= 0
        except ValueError as error:
            raise ValueError(f"producer log {path} has invalid {key}") from error
        if not nonnegative:
            raise ValueError(f"producer log {path} has invalid {key}")
    return records


def expected_scan(
    scans: list[dict[str, int]], drop_deletions: bool, append_empty: bool
) -> dict[str, int]:
    additions = sum(scan["additions"] for scan in scans)
    empty_additions = sum(scan["empty_additions"] for scan in scans)
    if append_empty:
        additions += 1
        empty_additions += 1
    return {
        "additions": additions,
        "deletions": 0 if drop_deletions else sum(scan["deletions"] for scan in scans),
        "empty_additions": empty_additions,
        "empty_deletions": 0
        if drop_deletions
        else sum(scan["empty_deletions"] for scan in scans),
    }


def resolve_path(root: Path, recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else root / path


def checked_file_record(
    record: Any, label: str, root: Path
) -> tuple[dict[str, Any], Path]:
    validated = validate_file_record(record, label)
    path = resolve_path(root, validated["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != validated["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    if file_sha256(path) != validated["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    return validated, path


def scan_and_hash_emitted(
    path: Path, digest: Any, drop_deletions: bool
) -> tuple[dict[str, int], int, str]:
    """Scan one binary proof and extend the digest with its emitted clauses."""
    counts = {
        "additions": 0,
        "deletions": 0,
        "empty_additions": 0,
        "empty_deletions": 0,
    }
    emitted_size = 0
    source_digest = hashlib.sha256()
    pending = b""
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            source_digest.update(block)
            if not drop_deletions:
                digest.update(block)
                emitted_size += len(block)
            clauses = (pending + block).split(b"\0")
            pending = clauses.pop()
            for clause in clauses:
                if not clause or clause[0] not in (ord("a"), ord("d")):
                    raise ValueError(f"invalid binary DRAT framing in {path}")
                addition = clause[0] == ord("a")
                key = "additions" if addition else "deletions"
                counts[key] += 1
                if len(clause) == 1:
                    counts["empty_additions" if addition else "empty_deletions"] += 1
                if drop_deletions and addition:
                    digest.update(clause)
                    digest.update(b"\0")
                    emitted_size += len(clause) + 1
    if pending:
        raise ValueError(f"unterminated binary DRAT clause in {path}")
    return counts, emitted_size, source_digest.hexdigest()


def checked_binary_record(
    record: Any,
    label: str,
    root: Path,
    digest: Any | None = None,
    drop_deletions: bool = False,
) -> tuple[dict[str, Any], Path, dict[str, int], int]:
    validated = validate_file_record(record, label)
    path = resolve_path(root, validated["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != validated["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    sink = digest if digest is not None else hashlib.sha256()
    scan, emitted_size, source_sha256 = scan_and_hash_emitted(
        path, sink, drop_deletions
    )
    if source_sha256 != validated["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    if validated.get("binary_drat") != scan:
        raise ValueError(f"{label} binary-DRAT counts mismatch: {path}")
    return validated, path, scan, emitted_size


def checked_child_finalization(
    record: Any,
    proof_record: dict[str, Any],
    root: Path,
) -> Path:
    validated, path = checked_file_record(record, "child finalization manifest", root)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") not in (
        FINALIZATION_SCHEMA,
        PROMOTION_SCHEMA,
    ):
        raise ValueError(f"unexpected child finalization manifest schema: {path}")
    if document.get("checker_verified") is not True:
        raise ValueError(f"child finalization manifest is not checker-verified: {path}")
    output = validate_file_record(document.get("output_fragment"), "output_fragment")
    if output.get("contains_empty_addition") is not False:
        raise ValueError(f"child finalization output is not embeddable: {path}")
    if (
        output["sha256"] != proof_record["sha256"]
        or output["size"] != proof_record["size"]
    ):
        raise ValueError(f"child proof does not match finalization manifest: {path}")
    expected = {
        "schema": document["schema"],
        "checker_verified": True,
        "output_fragment_sha256": output["sha256"],
        "output_fragment_size": output["size"],
    }
    for key, value in expected.items():
        if validated.get(key) != value:
            raise ValueError(f"child finalization summary mismatch for {key}: {path}")
    return path


def audit_manifest(
    manifest_path: Path,
    root: Path,
    recursive: bool,
    rerun_checker: bool,
    active: set[Path],
) -> dict[str, Any]:
    resolved_manifest = manifest_path.resolve()
    if resolved_manifest in active:
        raise ValueError(f"cyclic finalization manifests: {resolved_manifest}")
    active.add(resolved_manifest)
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(document, dict)
            or document.get("schema") != FINALIZATION_SCHEMA
        ):
            raise ValueError(
                f"unexpected finalization manifest schema: {manifest_path}"
            )
        if document.get("checker_verified") is not True:
            raise ValueError(
                f"finalization manifest is not checker-verified: {manifest_path}"
            )

        _, cnf = checked_file_record(document.get("cnf"), "cnf", root)
        _, replay_path = checked_file_record(
            document.get("replay_manifest"), "replay_manifest", root
        )
        _, checker = checked_file_record(document.get("checker"), "checker", root)
        _, checker_log = checked_file_record(
            document.get("checker_log"), "checker_log", root
        )
        if "s VERIFIED" not in checker_log.read_text(encoding="utf-8"):
            raise ValueError(f"checker log lacks s VERIFIED: {checker_log}")

        checker_options = document.get("checker_options")
        if not isinstance(checker_options, list) or not all(
            isinstance(option, str) for option in checker_options
        ):
            raise ValueError("invalid checker_options")
        composition = document.get("composition")
        if not isinstance(composition, dict) or not isinstance(
            composition.get("drop_deletions"), bool
        ):
            raise ValueError("invalid composition policy")
        drop_deletions = composition["drop_deletions"]

        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        if not isinstance(replay, dict) or replay.get("schema") != REPLAY_SCHEMA:
            raise ValueError(f"unexpected replay manifest schema: {replay_path}")

        expected_digest = hashlib.sha256()
        prefix_record, _, prefix_scan, prefix_size = checked_binary_record(
            document.get("prefix"),
            "prefix",
            root,
            expected_digest,
            drop_deletions,
        )
        if replay.get("proof_prefix_sha256") != prefix_record["sha256"]:
            raise ValueError("replay manifest prefix hash mismatch")
        if prefix_scan["empty_additions"]:
            raise ValueError("prefix contains an embedded empty addition")

        children = document.get("children")
        if not isinstance(children, list) or not children:
            raise ValueError("finalization manifest has no children")
        if replay.get("output_count") != len(children):
            raise ValueError("replay output count does not match children")
        component_scans = [prefix_scan]
        expected_size = prefix_size
        recursive_children = 0
        for index, child in enumerate(children):
            if not isinstance(child, dict) or child.get("index") != index:
                raise ValueError(f"invalid child index {index}")
            proof_record, _, proof_scan, emitted_size = checked_binary_record(
                child.get("proof"),
                f"child {index} proof",
                root,
                expected_digest,
                drop_deletions,
            )
            if proof_scan["empty_additions"]:
                raise ValueError(f"child {index} contains an embedded empty addition")
            component_scans.append(proof_scan)
            expected_size += emitted_size
            producer = child.get("producer_log")
            finalized = child.get("finalization_manifest")
            if (producer is None) == (finalized is None):
                raise ValueError(f"child {index} needs exactly one evidence record")
            if producer is not None:
                producer_record, producer_path = checked_file_record(
                    producer, f"child {index} producer log", root
                )
                telemetry = read_producer_log(producer_path)
                if producer_record.get("telemetry") != telemetry:
                    raise ValueError(f"child {index} producer telemetry mismatch")
            else:
                child_manifest = checked_child_finalization(
                    finalized, proof_record, root
                )
                if recursive:
                    child_document = json.loads(
                        child_manifest.read_text(encoding="utf-8")
                    )
                    if child_document.get("schema") == FINALIZATION_SCHEMA:
                        audit_manifest(
                            child_manifest,
                            root,
                            recursive=True,
                            rerun_checker=False,
                            active=active,
                        )
                    else:
                        from audit_checked_binary_drat_fragment_promotion import (
                            audit_promotion,
                        )

                        audit_promotion(
                            child_manifest,
                            root,
                            rerun_checker=False,
                            rerun_source_audit=False,
                            source_auditor=Path(__file__).with_name(
                                "audit_binary_drat_protect_cnf.py"
                            ),
                        )
                    recursive_children += 1

        expected_fragment_scan = expected_scan(
            component_scans, drop_deletions, append_empty=False
        )
        expected_fragment_sha256 = expected_digest.hexdigest()
        fragment_record, fragment_path, fragment_scan, _ = checked_binary_record(
            document.get("output_fragment"), "output_fragment", root
        )
        if fragment_record.get("contains_empty_addition") is not False:
            raise ValueError("output fragment lacks no-empty marker")
        if fragment_scan["empty_additions"]:
            raise ValueError("output fragment contains an empty addition")
        if fragment_scan != expected_fragment_scan:
            raise ValueError("output fragment clause counts do not match components")
        if fragment_record["sha256"] != expected_fragment_sha256:
            raise ValueError("output fragment is not the exact component composition")
        if fragment_record["size"] != expected_size:
            raise ValueError("output fragment size does not match components")

        standalone_digest = expected_digest.copy()
        standalone_digest.update(b"a\0")
        expected_standalone_scan = expected_scan(
            component_scans, drop_deletions, append_empty=True
        )
        standalone_record, standalone_path, standalone_scan, _ = checked_binary_record(
            document.get("standalone_proof"), "standalone_proof", root
        )
        if standalone_record.get("appended_empty_clause") is not True:
            raise ValueError("standalone proof lacks appended-empty marker")
        if standalone_scan != expected_standalone_scan:
            raise ValueError("standalone proof clause counts do not match components")
        if standalone_record["sha256"] != standalone_digest.hexdigest():
            raise ValueError("standalone proof is not fragment plus one empty addition")
        if standalone_record["size"] != expected_size + 2:
            raise ValueError("standalone proof size is not fragment size plus two")

        rerun: dict[str, Any] | None = None
        if rerun_checker:
            completed = subprocess.run(
                [str(checker), str(cnf), str(standalone_path), *checker_options],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if completed.returncode or "s VERIFIED" not in completed.stdout:
                raise RuntimeError(
                    "checker rerun rejected the standalone proof "
                    f"(exit {completed.returncode})"
                )
            rerun = {
                "returncode": completed.returncode,
                "verified": True,
                "output_sha256": hashlib.sha256(
                    completed.stdout.encode("utf-8")
                ).hexdigest(),
            }

        return {
            "schema": AUDIT_SCHEMA,
            "manifest": {
                "path": str(manifest_path),
                "sha256": file_sha256(manifest_path),
                "size": manifest_path.stat().st_size,
            },
            "children": len(children),
            "recursively_audited_children": recursive_children,
            "drop_deletions": drop_deletions,
            "output_fragment_sha256": fragment_record["sha256"],
            "standalone_proof_sha256": standalone_record["sha256"],
            "checker_log_sha256": file_sha256(checker_log),
            "checker_rerun": rerun,
            "verified": True,
        }
    finally:
        active.remove(resolved_manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="base directory for relative paths recorded in manifests",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not structurally audit checker-verified child manifests",
    )
    parser.add_argument(
        "--rerun-checker",
        action="store_true",
        help="rerun the top-level checker after the structural audit",
    )
    arguments = parser.parse_args()
    if not arguments.manifest.is_file():
        parser.error(f"manifest does not exist: {arguments.manifest}")
    report = audit_manifest(
        arguments.manifest,
        arguments.root,
        recursive=not arguments.no_recursive,
        rerun_checker=arguments.rerun_checker,
        active=set(),
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
