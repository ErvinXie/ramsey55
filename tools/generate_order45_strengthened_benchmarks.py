#!/usr/bin/env python3
"""Generate order-45 fixed-star CNFs strengthened by every degree bound."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ramsey55.cardinality import cardinality_range_encoding
from ramsey55.order45 import ORDER45_BRANCH_DEGREES
from ramsey55.sat import (
    edge_variable,
    fixed_star_clauses,
    ramsey55_clauses,
    variable_count,
)


SCHEMA = "ramsey55.order45-strengthened-benchmarks.v1"
RAW_HASHES = {
    20: "57984e902587656e67c88c6394fdb58c6f72d5e0ac8deda9c9d839b05957f12b",
    22: "1675b35934f64d3f3af15550eec3b510b359be2cd69d1d6a5f2bffb1ccb52d15",
}


def degree_bound_clauses(
    order: int, lower: int, upper: int, maximum_variable: int
) -> tuple[int, tuple[tuple[int, ...], ...]]:
    clauses: list[tuple[int, ...]] = []
    variable = maximum_variable
    # Vertex zero already has an exact fixed degree.  Encoding it again would
    # only add auxiliaries without propagation value.
    for vertex in range(1, order):
        incident = tuple(
            edge_variable(vertex, other)
            for other in range(order)
            if other != vertex
        )
        variable, encoded = cardinality_range_encoding(
            incident, lower, upper, variable
        )
        clauses.extend(encoded)
    return variable, tuple(clauses)


def write_strengthened_dimacs(path: Path, degree: int) -> tuple[int, int]:
    order = 45
    primary_variables = variable_count(order)
    variables, bounded = degree_bound_clauses(order, 20, 24, primary_variables)
    base_clause_count = 2 * _binomial(order, 5) + order - 1
    clause_count = base_clause_count + len(bounded)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for clauses in (
            ramsey55_clauses(order),
            fixed_star_clauses(order, degree),
            bounded,
        ):
            for clause in clauses:
                output.write(" ".join(map(str, clause)))
                output.write(" 0\n")
    return variables, clause_count


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _binomial(n: int, k: int) -> int:
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/order45-strengthened")
    )
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    manifest_path = arguments.manifest or arguments.output_dir / "manifest.json"

    records = []
    for degree in ORDER45_BRANCH_DEGREES:
        path = arguments.output_dir / f"r55-n45-d{degree}-deg20-24.cnf"
        variables, clauses = write_strengthened_dimacs(path, degree)
        records.append(
            {
                "degree": degree,
                "path": path.name,
                "variables": variables,
                "clauses": clauses,
                "sha256": file_sha256(path),
                "raw_sha256": RAW_HASHES[degree],
            }
        )
        print(f"generated {path}: variables={variables} clauses={clauses}")

    document = {
        "schema": SCHEMA,
        "order": 45,
        "degree_window": [20, 24],
        "fixed_star_branches": list(ORDER45_BRANCH_DEGREES),
        "bounded_vertices": [1, 44],
        "encoding": "bidirectional at-least sequential counter",
        "coverage_dependency": "R(4,5)=25 implies every degree is in [20,24]",
        "files": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
