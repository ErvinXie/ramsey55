#!/usr/bin/env python3
"""Promote a checked standalone binary DRAT proof to an embeddable fragment.

The source proof must be an independently audited protected-CNF composition
whose only empty addition is the final two-byte ``a\0`` record.  Promotion is
then the exact byte-prefix operation that removes that record; it does not run
or alter the proof checker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, BinaryIO


SCHEMA = "ramsey55.checked-binary-drat-fragment-promotion.v1"
COMPOSITION_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition.v1"
AUDIT_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition-audit.v1"
COUNT_KEYS = {
    "additions",
    "retained_deletions",
    "dropped_protected_deletions",
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


def validate_counts(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != COUNT_KEYS:
        raise ValueError(f"invalid {label} composition counts")
    if not all(isinstance(value[key], int) and value[key] >= 0 for key in COUNT_KEYS):
        raise ValueError(f"invalid {label} composition count value")
    return value


def exact_verified_line(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return any(line.strip("\r") == "s VERIFIED" for line in text.splitlines())


def load_json(path: Path, label: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{label} is not a JSON object")
    return document


def copy_prefix_without_final_empty(
    source: BinaryIO, target: BinaryIO, source_size: int
) -> tuple[str, str, int]:
    if source_size < 2:
        raise ValueError("standalone proof is too short to end in an empty addition")
    remaining = source_size - 2
    source_digest = hashlib.sha256()
    fragment_digest = hashlib.sha256()
    fragment_size = 0
    while remaining:
        block = source.read(min(1 << 23, remaining))
        if not block:
            raise ValueError("standalone proof ended before its recorded size")
        source_digest.update(block)
        fragment_digest.update(block)
        target.write(block)
        fragment_size += len(block)
        remaining -= len(block)
    final = source.read(2)
    source_digest.update(final)
    if final != b"a\0":
        raise ValueError("standalone proof does not end in a binary empty addition")
    if source.read(1):
        raise ValueError("standalone proof grew while being promoted")
    return source_digest.hexdigest(), fragment_digest.hexdigest(), fragment_size


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("composition_manifest", type=Path)
    parser.add_argument("composition_audit", type=Path)
    parser.add_argument("output_fragment", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="base directory for relative paths recorded in source manifests",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    for path in (arguments.composition_manifest, arguments.composition_audit):
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    if arguments.output_fragment.exists() or arguments.manifest.exists():
        parser.error("refusing to overwrite an output")
    fragment_temporary = arguments.output_fragment.with_suffix(
        arguments.output_fragment.suffix + ".tmp"
    )
    manifest_temporary = arguments.manifest.with_suffix(
        arguments.manifest.suffix + ".tmp"
    )
    if fragment_temporary.exists() or manifest_temporary.exists():
        parser.error("refusing to overwrite a temporary output")

    composition = load_json(arguments.composition_manifest, "composition manifest")
    if composition.get("schema") != COMPOSITION_SCHEMA:
        raise ValueError("unexpected composition manifest schema")
    if composition.get("append_empty") is not True:
        raise ValueError("source composition did not append a final empty addition")
    counts = validate_counts(composition.get("composition_counts"), "source")
    if counts["empty_additions"] != 1 or counts["additions"] < 1:
        raise ValueError("source composition lacks exactly one empty addition")

    cnf_record, _ = checked_file_record(composition.get("cnf"), "cnf", arguments.root)
    standalone_record, standalone_path = checked_file_record(
        composition.get("output"), "standalone proof", arguments.root
    )

    audit = load_json(arguments.composition_audit, "composition audit")
    if audit.get("schema") != AUDIT_SCHEMA:
        raise ValueError("unexpected composition audit schema")
    for field in ("verified", "structurally_verified", "checker_verified"):
        if audit.get(field) is not True:
            raise ValueError(f"composition audit lacks {field}=true")
    same_content(
        audit.get("manifest"),
        file_record(arguments.composition_manifest),
        "composition manifest audit",
    )
    same_content(audit.get("cnf"), cnf_record, "audited CNF")
    same_content(audit.get("output"), standalone_record, "audited standalone proof")
    if validate_counts(audit.get("composition_counts"), "audited") != counts:
        raise ValueError("composition audit count mismatch")

    checker_record, _ = checked_file_record(
        audit.get("checker"), "checker", arguments.root
    )
    checker_log_record, checker_log_path = checked_file_record(
        audit.get("checker_log"), "checker log", arguments.root
    )
    if audit["checker_log"].get("verified") is not True:
        raise ValueError("composition audit does not mark the checker log verified")
    if not exact_verified_line(checker_log_path):
        raise ValueError("checker log lacks an exact s VERIFIED line")

    try:
        with (
            standalone_path.open("rb") as source,
            fragment_temporary.open("wb") as target,
        ):
            observed_standalone_hash, fragment_hash, fragment_size = (
                copy_prefix_without_final_empty(
                    source, target, standalone_record["size"]
                )
            )
        if observed_standalone_hash != standalone_record["sha256"]:
            raise ValueError("standalone proof hash changed while being promoted")
        if fragment_temporary.stat().st_size != fragment_size:
            raise ValueError("promoted fragment size changed while being written")
        fragment_temporary.replace(arguments.output_fragment)
    finally:
        if fragment_temporary.exists():
            fragment_temporary.unlink()

    fragment_counts = {
        "additions": counts["additions"] - 1,
        "deletions": counts["retained_deletions"],
        "empty_additions": 0,
        "empty_deletions": counts["empty_deletions"],
    }
    standalone_counts = {
        **fragment_counts,
        "additions": fragment_counts["additions"] + 1,
        "empty_additions": 1,
    }
    fragment_record = {
        "path": str(arguments.output_fragment),
        "sha256": fragment_hash,
        "size": fragment_size,
    }
    document = {
        "schema": SCHEMA,
        "source_composition_manifest": file_record(arguments.composition_manifest),
        "source_composition_audit": file_record(arguments.composition_audit),
        "source_composition_counts": counts,
        "cnf": cnf_record,
        "output_fragment": {
            **fragment_record,
            "binary_drat": fragment_counts,
            "contains_empty_addition": False,
        },
        "standalone_proof": {
            **standalone_record,
            "binary_drat": standalone_counts,
            "appended_empty_clause": True,
        },
        "derivation": "exact standalone byte prefix excluding final a\\0",
        "checker": checker_record,
        "checker_options": [],
        "checker_log": checker_log_record,
        "checker_verified": True,
    }
    atomic_json(arguments.manifest, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
