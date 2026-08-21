#!/usr/bin/env python3
"""Freeze a proof manifest as a minimal auditable chain-state snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROOF_SCHEMA = "ramsey55.materialized-cube-proofs.v1"
STATE_SCHEMA = "ramsey55.materialized-proof-chain.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def freeze(manifest_path: Path, round_number: int) -> dict[str, Any]:
    if round_number < 0:
        raise ValueError("round must be nonnegative")
    if not manifest_path.is_file():
        raise ValueError(f"proof manifest does not exist: {manifest_path}")
    manifest = load_object(manifest_path)
    if manifest.get("schema") != PROOF_SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    results = manifest.get("results")
    summary = manifest.get("summary")
    if not isinstance(results, list) or not isinstance(summary, dict):
        raise ValueError("proof manifest has no results or summary")
    statuses = [int(result["status"]) for result in results]
    if any(status not in (0, 20) for status in statuses):
        raise ValueError("chain state cannot contain SAT or invalid results")
    expected = {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": 0,
        "complete_unsat": all(status == 20 for status in statuses),
    }
    if summary != expected:
        raise ValueError("proof summary disagrees with result statuses")
    return {
        "schema": STATE_SCHEMA,
        "round": round_number,
        "current_manifest": str(manifest_path),
        "current_manifest_sha256": file_sha256(manifest_path),
        "complete": bool(expected["complete_unsat"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("round", type=int)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    try:
        state = freeze(arguments.manifest, arguments.round)
    except ValueError as error:
        parser.error(str(error))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(arguments.output)
    print(json.dumps(state, sort_keys=True))


if __name__ == "__main__":
    main()
