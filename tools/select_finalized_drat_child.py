#!/usr/bin/env python3
"""Select one checker-verified finalized DRAT child without ambiguity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


SCHEMA = "ramsey55.finalized-drat-child-selection.v1"
FINALIZATION_SCHEMAS = {
    "ramsey55.cadical-dfs-checkpoint-finalization.v1",
    "ramsey55.checked-binary-drat-fragment-promotion.v1",
}
NOT_READY = 4


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def validate_file_record(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"finalization manifest lacks {label} file record")
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


def inspect_candidate(proof: Path, evidence: Path) -> dict[str, Any] | None:
    proof_ready = proof.is_file() and proof.stat().st_size > 0
    evidence_ready = evidence.is_file() and evidence.stat().st_size > 0
    if not proof_ready or not evidence_ready:
        return None

    try:
        document = json.loads(evidence.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid candidate finalization manifest: {evidence}") from error
    if not isinstance(document, dict) or document.get("schema") not in FINALIZATION_SCHEMAS:
        raise ValueError(f"unexpected candidate finalization schema: {evidence}")
    if document.get("checker_verified") is not True:
        raise ValueError(f"candidate is not checker-verified: {evidence}")

    proof_record = file_record(proof)
    output = validate_file_record(document.get("output_fragment"), "output_fragment")
    if output.get("contains_empty_addition") is not False:
        raise ValueError(f"candidate output contains an empty addition: {evidence}")
    if output["sha256"] != proof_record["sha256"] or output["size"] != proof_record["size"]:
        raise ValueError(f"candidate proof does not match its manifest: {evidence}")

    standalone = validate_file_record(document.get("standalone_proof"), "standalone_proof")
    if standalone.get("appended_empty_clause") is not True:
        raise ValueError(f"candidate lacks a standalone empty-clause marker: {evidence}")

    return {
        "proof": proof_record,
        "evidence": file_record(evidence),
        "finalization_schema": document["schema"],
    }


def candidate_specs(candidates: list[tuple[Path, Path]]) -> list[dict[str, str]]:
    return [
        {"proof_path": str(proof), "evidence_path": str(evidence)}
        for proof, evidence in candidates
    ]


def verify_existing(path: Path, candidates: list[tuple[Path, Path]]) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid existing selection: {path}") from error
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError(f"unexpected existing selection schema: {path}")
    if document.get("candidates") != candidate_specs(candidates):
        raise ValueError("existing selection candidate list does not match the request")
    selected_index = document.get("selected_index")
    if not isinstance(selected_index, int) or not 0 <= selected_index < len(candidates):
        raise ValueError("existing selection has an invalid selected_index")
    selected = inspect_candidate(*candidates[selected_index])
    if selected is None or selected != document.get("selected"):
        raise ValueError("existing selection no longer matches its selected candidate")
    return document


def atomic_create(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ValueError(f"selection appeared concurrently: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="append", nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    candidates = [
        (Path(proof), Path(evidence)) for proof, evidence in arguments.candidate
    ]

    if arguments.output.exists():
        document = verify_existing(arguments.output, candidates)
        print(json.dumps(document, sort_keys=True))
        return

    selected_index = None
    selected = None
    for index, candidate in enumerate(candidates):
        inspected = inspect_candidate(*candidate)
        if inspected is not None and selected is None:
            selected_index = index
            selected = inspected
    if selected is None:
        print("no checker-verified finalized candidate is ready", file=sys.stderr)
        raise SystemExit(NOT_READY)

    document = {
        "schema": SCHEMA,
        "candidates": candidate_specs(candidates),
        "selected_index": selected_index,
        "selected": selected,
    }
    atomic_create(arguments.output, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
