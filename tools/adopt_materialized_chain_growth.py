#!/usr/bin/env python3
"""Create an auditable chain-state snapshot that accepts a guarded growth."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HALT_SCHEMA = "ramsey55.materialized-proof-chain-halt.v1"
STATE_SCHEMA = "ramsey55.materialized-proof-chain.v1"
PROOF_SCHEMA = "ramsey55.materialized-cube-proofs.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def adopt(halt_path: Path) -> dict[str, Any]:
    halt = load_object(halt_path)
    if halt.get("schema") != HALT_SCHEMA or halt.get("reason") != "frontier_growth":
        raise ValueError("not a guarded frontier-growth record")
    round_number = int(halt["round"])
    parent_unknown = int(halt["parent_unknown"])
    candidate_unknown = int(halt["candidate_unknown"])
    if round_number < 0 or parent_unknown < 0 or candidate_unknown <= parent_unknown:
        raise ValueError("invalid guarded-growth counts")
    parent_path = Path(halt["parent_manifest"])
    candidate_path = Path(halt["candidate_manifest"])
    manifests = (
        ("parent", parent_path, parent_unknown),
        ("candidate", candidate_path, candidate_unknown),
    )
    loaded: dict[str, dict[str, Any]] = {}
    for label, path, expected_unknown in manifests:
        if not path.is_file():
            raise ValueError(f"{label} manifest does not exist: {path}")
        document = load_object(path)
        if document.get("schema") != PROOF_SCHEMA:
            raise ValueError(f"unexpected {label} proof schema")
        summary = document.get("summary")
        if not isinstance(summary, dict):
            raise ValueError(f"{label} proof has no summary")
        if int(summary.get("sat", -1)) != 0:
            raise ValueError(f"{label} contains a SAT result")
        if int(summary.get("unknown", -1)) != expected_unknown:
            raise ValueError(f"{label} UNKNOWN count differs from the halt record")
        loaded[label] = document
    if parent_path == candidate_path:
        raise ValueError("parent and candidate manifests must differ")
    if bool(loaded["candidate"]["summary"].get("complete_unsat")):
        raise ValueError("a complete candidate should not be adopted as growth")
    return {
        "schema": STATE_SCHEMA,
        "round": round_number + 1,
        "current_manifest": str(candidate_path),
        "current_manifest_sha256": file_sha256(candidate_path),
        "complete": False,
        "adopted_growth": {
            "halt_path": str(halt_path),
            "halt_sha256": file_sha256(halt_path),
            "parent_manifest": str(parent_path),
            "parent_manifest_sha256": file_sha256(parent_path),
            "parent_unknown": parent_unknown,
            "candidate_manifest": str(candidate_path),
            "candidate_manifest_sha256": file_sha256(candidate_path),
            "candidate_unknown": candidate_unknown,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("halt", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    state = adopt(arguments.halt)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(arguments.output)
    print(json.dumps(state, sort_keys=True))


if __name__ == "__main__":
    main()
