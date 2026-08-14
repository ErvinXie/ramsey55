#!/usr/bin/env python3
"""Generate degree-bounded order-45 CNFs with safe cross-row lex leaders."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ramsey55.lex import lex_leq_encoding
from ramsey55.order45 import ORDER45_BRANCH_DEGREES
from ramsey55.sat import edge_variable, fixed_star_clauses, ramsey55_clauses
from generate_order45_strengthened_benchmarks import degree_bound_clauses


SCHEMA = "ramsey55.order45-lex-benchmarks.v1"


def lex_clauses(degree: int, maximum_variable: int):
    left_vertices = range(1, degree + 1)
    right_vertices = range(degree + 1, 45)
    rows = [
        tuple(edge_variable(left, right) for right in right_vertices)
        for left in left_vertices
    ]
    variable = maximum_variable
    clauses: list[tuple[int, ...]] = []
    for left, right in zip(rows, rows[1:]):
        variable, encoded = lex_leq_encoding(left, right, variable)
        clauses.extend(encoded)
    return variable, tuple(clauses)


def write_formula(path: Path, degree: int) -> tuple[int, int]:
    variables, bounded = degree_bound_clauses(45, 20, 24, 990)
    variables, lex = lex_clauses(degree, variables)
    clause_count = 2 * 1_221_759 + 44 + len(bounded) + len(lex)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for source in (
            ramsey55_clauses(45),
            fixed_star_clauses(45, degree),
            bounded,
            lex,
        ):
            for clause in source:
                output.write(" ".join(map(str, clause)) + " 0\n")
    return variables, clause_count


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/order45-lex"))
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    manifest_path = arguments.manifest or arguments.output_dir / "manifest.json"
    records = []
    for degree in ORDER45_BRANCH_DEGREES:
        path = arguments.output_dir / f"r55-n45-d{degree}-deg20-24-lexA.cnf"
        variables, clauses = write_formula(path, degree)
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
    document = {
        "schema": SCHEMA,
        "order": 45,
        "degree_window": [20, 24],
        "fixed_star_branches": list(ORDER45_BRANCH_DEGREES),
        "symmetry": "neighbour-to-nonneighbour rows are lexicographically sorted",
        "coverage": "permute the fixed apex neighbours to sort their cross rows",
        "files": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
