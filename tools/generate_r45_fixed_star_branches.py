#!/usr/bin/env python3
"""Generate a complete fixed-star branch family for the R(4,5,25) CNF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ramsey55.sat import edge_variable
from tools.generate_r45_upper_bound_cnf import (
    CLAUSES as BASE_CLAUSES,
    ORDER,
    SCHEMA as BASE_SCHEMA,
    VARIABLES,
    r45_upper_bound_clauses,
)


SCHEMA = "ramsey55.r45-fixed-star-branches.v1"


def fixed_star_clauses(degree: int):
    if not 0 <= degree < ORDER:
        raise ValueError("fixed-star degree outside graph")
    for vertex in range(1, ORDER):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/r45-fixed-star")
    )
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    clause_count = BASE_CLAUSES + ORDER - 1
    for degree in range(ORDER):
        path = arguments.output_dir / f"r45-n25-fixed-d{degree:02d}.cnf"
        with path.open("w", encoding="ascii", newline="\n") as output:
            output.write(f"p cnf {VARIABLES} {clause_count}\n")
            count = 0
            for source in (r45_upper_bound_clauses(), fixed_star_clauses(degree)):
                for count, clause in enumerate(source, count + 1):
                    output.write(" ".join(map(str, clause)))
                    output.write(" 0\n")
        if count != clause_count:
            raise RuntimeError(f"d{degree}: generated {count}, expected {clause_count}")
        records.append(
            {
                "degree": degree,
                "path": path.name,
                "variables": VARIABLES,
                "clauses": clause_count,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": SCHEMA,
        "base_schema": BASE_SCHEMA,
        "order": ORDER,
        "records": records,
    }
    manifest_path = arguments.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(records)} branches to {arguments.output_dir}")


if __name__ == "__main__":
    main()
