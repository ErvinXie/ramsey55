#!/usr/bin/env python3
"""Independently audit a checked binary-DRAT fragment promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


AUDIT_SCHEMA = "ramsey55.checked-binary-drat-fragment-promotion-audit.v1"
PROMOTION_SCHEMA = "ramsey55.checked-binary-drat-fragment-promotion.v1"
COMPOSITION_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition.v1"
SOURCE_AUDIT_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition-audit.v1"
SOURCE_COUNT_KEYS = {
    "additions",
    "retained_deletions",
    "dropped_protected_deletions",
    "empty_additions",
    "empty_deletions",
}
BINARY_COUNT_KEYS = {
    "additions",
    "deletions",
    "empty_additions",
    "empty_deletions",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def validate_file_record(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest lacks {label} file record")
    if not isinstance(value.get("path"), str) or not value["path"]:
        raise ValueError(f"manifest has invalid {label} path")
    digest = value.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"manifest has invalid {label} hash")
    if not isinstance(value.get("size"), int) or value["size"] < 0:
        raise ValueError(f"manifest has invalid {label} size")
    return value


def resolve_path(root: Path, recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else root / path


def checked_file_record(
    value: Any, label: str, root: Path
) -> tuple[dict[str, Any], Path]:
    record = validate_file_record(value, label)
    path = resolve_path(root, record["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != record["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    if file_sha256(path) != record["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    return record, path


def same_content(left: Any, right: Any, label: str) -> None:
    left_record = validate_file_record(left, f"{label} left")
    right_record = validate_file_record(right, f"{label} right")
    if any(left_record[key] != right_record[key] for key in ("sha256", "size")):
        raise ValueError(f"{label} records do not bind the same file content")


def validate_counts(value: Any, keys: set[str], label: str) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"invalid {label} counts")
    if not all(isinstance(value[key], int) and value[key] >= 0 for key in keys):
        raise ValueError(f"invalid {label} count value")
    return value


def exact_verified_line(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return any(line.strip("\r") == "s VERIFIED" for line in text.splitlines())


def scan_binary_drat(path: Path) -> tuple[dict[str, int], str, int, str]:
    counts = {key: 0 for key in BINARY_COUNT_KEYS}
    digest = hashlib.sha256()
    size = 0
    pending = b""
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
            size += len(block)
            framed = (pending + block).split(b"\0")
            pending = framed.pop()
            for clause in framed:
                if not clause or clause[0] not in (ord("a"), ord("d")):
                    raise ValueError(f"invalid binary DRAT framing in {path}")
                addition = clause[0] == ord("a")
                counts["additions" if addition else "deletions"] += 1
                if len(clause) == 1:
                    counts["empty_additions" if addition else "empty_deletions"] += 1
    if pending:
        raise ValueError(f"unterminated binary DRAT clause in {path}")
    observed_hash = digest.hexdigest()
    digest.update(b"a\0")
    return counts, observed_hash, size, digest.hexdigest()


def checked_binary_record(
    value: Any, label: str, root: Path
) -> tuple[dict[str, Any], Path, dict[str, int], str]:
    record = validate_file_record(value, label)
    path = resolve_path(root, record["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != record["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    counts, digest, size, plus_empty_digest = scan_binary_drat(path)
    if size != record["size"] or digest != record["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    if validate_counts(record.get("binary_drat"), BINARY_COUNT_KEYS, label) != counts:
        raise ValueError(f"{label} binary-DRAT counts mismatch: {path}")
    return record, path, counts, plus_empty_digest


def load_json(path: Path, label: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{label} is not a JSON object")
    return document


def check_source_chain(
    promotion: dict[str, Any], root: Path
) -> tuple[Path, Path, Path, Path, dict[str, int]]:
    composition_record, composition_path = checked_file_record(
        promotion.get("source_composition_manifest"),
        "source composition manifest",
        root,
    )
    audit_record, audit_path = checked_file_record(
        promotion.get("source_composition_audit"), "source composition audit", root
    )
    composition = load_json(composition_path, "source composition manifest")
    audit = load_json(audit_path, "source composition audit")
    if composition.get("schema") != COMPOSITION_SCHEMA:
        raise ValueError("unexpected source composition schema")
    if composition.get("append_empty") is not True:
        raise ValueError("source composition lacks appended-empty policy")
    if audit.get("schema") != SOURCE_AUDIT_SCHEMA:
        raise ValueError("unexpected source composition audit schema")
    for field in ("verified", "structurally_verified", "checker_verified"):
        if audit.get(field) is not True:
            raise ValueError(f"source composition audit lacks {field}=true")
    same_content(audit.get("manifest"), composition_record, "source manifest audit")
    same_content(audit.get("cnf"), composition.get("cnf"), "source CNF audit")
    same_content(audit.get("output"), composition.get("output"), "source proof audit")

    counts = validate_counts(
        composition.get("composition_counts"), SOURCE_COUNT_KEYS, "source composition"
    )
    if counts["empty_additions"] != 1 or counts["additions"] < 1:
        raise ValueError("source composition lacks exactly one empty addition")
    if (
        validate_counts(
            audit.get("composition_counts"), SOURCE_COUNT_KEYS, "source audit"
        )
        != counts
    ):
        raise ValueError("source composition audit count mismatch")
    if (
        validate_counts(
            promotion.get("source_composition_counts"),
            SOURCE_COUNT_KEYS,
            "promotion source composition",
        )
        != counts
    ):
        raise ValueError("promotion source composition count mismatch")

    same_content(promotion.get("cnf"), composition.get("cnf"), "promotion CNF")
    checked_file_record(promotion.get("cnf"), "cnf", root)
    same_content(
        promotion.get("standalone_proof"),
        composition.get("output"),
        "promotion standalone proof",
    )
    same_content(promotion.get("checker"), audit.get("checker"), "promotion checker")
    same_content(
        promotion.get("checker_log"), audit.get("checker_log"), "promotion checker log"
    )
    checker_record, checker_path = checked_file_record(
        promotion.get("checker"), "checker", root
    )
    checker_log_record, checker_log_path = checked_file_record(
        promotion.get("checker_log"), "checker log", root
    )
    if audit["checker_log"].get("verified") is not True:
        raise ValueError("source audit does not mark checker log verified")
    if not exact_verified_line(checker_log_path):
        raise ValueError("checker log lacks an exact s VERIFIED line")
    if promotion.get("checker_verified") is not True:
        raise ValueError("promotion is not checker-verified")
    if promotion.get("checker_options") != []:
        raise ValueError("promotion checker options are not the expected empty list")
    if (
        promotion.get("derivation")
        != "exact standalone byte prefix excluding final a\\0"
    ):
        raise ValueError("unexpected promotion derivation")
    # Keep the validated records live for callers and catch accidental omission
    # of their hashes even though their content equality was already checked.
    assert checker_record and checker_log_record and audit_record
    return composition_path, audit_path, checker_path, checker_log_path, counts


def audit_promotion(
    manifest_path: Path,
    root: Path,
    rerun_checker: bool,
    rerun_source_audit: bool,
    source_auditor: Path,
) -> dict[str, Any]:
    promotion = load_json(manifest_path, "promotion manifest")
    if promotion.get("schema") != PROMOTION_SCHEMA:
        raise ValueError("unexpected promotion manifest schema")
    (
        composition_path,
        source_audit_path,
        checker_path,
        checker_log_path,
        source_counts,
    ) = check_source_chain(promotion, root)

    (
        fragment_record,
        _,
        fragment_counts,
        fragment_plus_empty_hash,
    ) = checked_binary_record(promotion.get("output_fragment"), "output fragment", root)
    standalone_record, standalone_path, standalone_counts, _ = checked_binary_record(
        promotion.get("standalone_proof"), "standalone proof", root
    )
    if fragment_record.get("contains_empty_addition") is not False:
        raise ValueError("output fragment lacks a no-empty marker")
    if fragment_counts["empty_additions"]:
        raise ValueError("output fragment contains an empty addition")
    if standalone_record.get("appended_empty_clause") is not True:
        raise ValueError("standalone proof lacks appended-empty marker")
    expected_fragment_counts = {
        "additions": source_counts["additions"] - 1,
        "deletions": source_counts["retained_deletions"],
        "empty_additions": 0,
        "empty_deletions": source_counts["empty_deletions"],
    }
    expected_standalone_counts = {
        **expected_fragment_counts,
        "additions": expected_fragment_counts["additions"] + 1,
        "empty_additions": 1,
    }
    if fragment_counts != expected_fragment_counts:
        raise ValueError("output fragment counts do not match source composition")
    if standalone_counts != expected_standalone_counts:
        raise ValueError("standalone counts do not match source composition")
    if standalone_record["size"] != fragment_record["size"] + 2:
        raise ValueError("standalone proof size is not fragment size plus two")
    if fragment_plus_empty_hash != standalone_record["sha256"]:
        raise ValueError("standalone proof is not fragment plus one empty addition")

    source_audit_rerun: dict[str, Any] | None = None
    if rerun_source_audit:
        if not source_auditor.is_file():
            raise ValueError(f"source auditor does not exist: {source_auditor}")
        completed = subprocess.run(
            [
                sys.executable,
                str(source_auditor),
                str(composition_path),
                "--root",
                str(root),
                "--checker-log",
                str(checker_log_path),
                "--checker",
                str(checker_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                "source composition audit rerun failed "
                f"(exit {completed.returncode}): {completed.stderr}"
            )
        observed = json.loads(completed.stdout)
        recorded = load_json(source_audit_path, "recorded source composition audit")
        for field in (
            "schema",
            "cnf_exact_unique_clauses",
            "fragments",
            "composition_counts",
            "structurally_verified",
            "checker_verified",
            "verified",
        ):
            if observed.get(field) != recorded.get(field):
                raise ValueError(f"source audit rerun mismatch for {field}")
        for field in ("manifest", "cnf", "output", "checker", "checker_log"):
            same_content(observed.get(field), recorded.get(field), f"rerun {field}")
        source_audit_rerun = {
            "auditor": file_record(source_auditor),
            "verified": True,
            "output_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
        }

    checker_rerun: dict[str, Any] | None = None
    if rerun_checker:
        completed = subprocess.run(
            [
                str(checker_path),
                str(resolve_path(root, promotion["cnf"]["path"])),
                str(standalone_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode or not any(
            line.strip("\r") == "s VERIFIED" for line in completed.stdout.splitlines()
        ):
            raise RuntimeError(
                f"checker rerun rejected proof (exit {completed.returncode})"
            )
        checker_rerun = {
            "returncode": completed.returncode,
            "verified": True,
            "output_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
        }

    return {
        "schema": AUDIT_SCHEMA,
        "manifest": file_record(manifest_path),
        "source_composition_manifest": file_record(composition_path),
        "source_composition_audit": file_record(source_audit_path),
        "output_fragment_sha256": fragment_record["sha256"],
        "standalone_proof_sha256": standalone_record["sha256"],
        "checker_log_sha256": file_sha256(checker_log_path),
        "source_audit_rerun": source_audit_rerun,
        "checker_rerun": checker_rerun,
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--rerun-checker", action="store_true")
    parser.add_argument("--rerun-source-audit", action="store_true")
    parser.add_argument(
        "--source-auditor",
        type=Path,
        default=Path(__file__).with_name("audit_binary_drat_protect_cnf.py"),
    )
    arguments = parser.parse_args()
    if not arguments.manifest.is_file():
        parser.error(f"manifest does not exist: {arguments.manifest}")
    report = audit_promotion(
        arguments.manifest,
        arguments.root,
        arguments.rerun_checker,
        arguments.rerun_source_audit,
        arguments.source_auditor,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
