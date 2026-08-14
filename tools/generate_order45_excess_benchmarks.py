#!/usr/bin/env python3
"""Generate the complete three-branch nonpositive-excess witness cover."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from ramsey55.cardinality import cardinality_range_encoding
from ramsey55.order45 import (
    ORDER45_EXCESS_WITNESS_DEGREES,
    order45_excess_minimum_edge_sum,
)
from ramsey55.sat import edge_variable, fixed_star_clauses, ramsey55_clauses
from generate_order45_lex_benchmarks import lex_clauses
from generate_order45_strengthened_benchmarks import degree_bound_clauses


SCHEMA = "ramsey55.order45-excess-witness-benchmarks.v1"


def local_excess_literals(degree: int) -> tuple[int, ...]:
    neighbours = range(1, degree + 1)
    nonneighbours = range(degree + 1, 45)
    edges_h = tuple(
        edge_variable(u, v) for u, v in itertools.combinations(neighbours, 2)
    )
    # A false edge in the nonneighbour subgraph is an edge of J, its complement.
    edges_j = tuple(
        -edge_variable(u, v)
        for u, v in itertools.combinations(nonneighbours, 2)
    )
    return edges_h + edges_j


def write_formula(path: Path, degree: int) -> tuple[int, int]:
    variables, bounded = degree_bound_clauses(45, 20, 24, 990)
    variables, lex = lex_clauses(degree, variables)
    local_inputs = local_excess_literals(degree)
    variables, excess = cardinality_range_encoding(
        local_inputs,
        order45_excess_minimum_edge_sum(degree),
        len(local_inputs),
        variables,
    )
    sources = (
        ramsey55_clauses(45),
        fixed_star_clauses(45, degree),
        bounded,
        lex,
        excess,
    )
    clause_count = 2 * 1_221_759 + 44 + len(bounded) + len(lex) + len(excess)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for source in sources:
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
    parser.add_argument("--output-dir", type=Path, default=Path("build/order45-excess"))
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    manifest_path = arguments.manifest or arguments.output_dir / "manifest.json"
    records = []
    for degree in ORDER45_EXCESS_WITNESS_DEGREES:
        path = arguments.output_dir / f"r55-n45-excess-d{degree}.cnf"
        variables, clauses = write_formula(path, degree)
        records.append(
            {
                "degree": degree,
                "minimum_local_edge_sum": order45_excess_minimum_edge_sum(degree),
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
        "normalized_witness_degrees": list(ORDER45_EXCESS_WITNESS_DEGREES),
        "coverage_dependencies": [
            "the global three-vertex excess contributions sum to zero",
            "some vertex therefore has nonpositive contribution",
            "colour complementation maps witness degree d to 44-d and swaps H,J",
            "R(4,5)=25 gives the degree window [20,24]",
        ],
        "files": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
