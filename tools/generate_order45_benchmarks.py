#!/usr/bin/env python3
"""Generate the two canonical Ramsey(5,5,45) fixed-degree benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ramsey55.order45 import ORDER45_BRANCH_DEGREES
from ramsey55.sat import write_dimacs


SCHEMA = "ramsey55.order45-benchmarks.v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/order45"))
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    output_dir = arguments.output_dir
    manifest_path = arguments.manifest or output_dir / "manifest.json"

    records: list[dict[str, int | str]] = []
    for degree in ORDER45_BRANCH_DEGREES:
        path = output_dir / f"r55-n45-d{degree}.cnf"
        variables, clauses = write_dimacs(path, 45, fixed_star_degree=degree)
        records.append(
            {
                "degree": degree,
                "path": path.name,
                "variables": variables,
                "clauses": clauses,
                "sha256": sha256(path),
            }
        )
        print(f"generated {path}: variables={variables} clauses={clauses}")

    manifest = {
        "schema": SCHEMA,
        "order": 45,
        "degree_window": [20, 24],
        "normalized_degree_branches": list(ORDER45_BRANCH_DEGREES),
        "coverage_dependencies": [
            "R(4,5)=25 gives 20 <= d(v) <= 24",
            "the handshake identity gives an even-degree vertex",
            "colour complementation maps degree 24 to degree 20",
            "vertex relabelling fixes the distinguished star",
        ],
        "files": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
