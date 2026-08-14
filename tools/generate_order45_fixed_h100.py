#!/usr/bin/env python3
"""Fix the unique H100 neighbourhood throughout the d20 excess branch."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path

from ramsey55 import Graph
from ramsey55.cardinality import cardinality_range_encoding
from ramsey55.sat import edge_variable, fixed_star_clauses, ramsey55_clauses
from generate_order45_strengthened_benchmarks import degree_bound_clauses


SCHEMA = "ramsey55.order45-fixed-h100.v1"


def first_record(path: Path) -> str:
    with path.open(encoding="ascii") as stream:
        return next(
            line.strip()
            for line in stream
            if line.strip() and not line.startswith("#")
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=Path("data/reference/r4520.100.g6"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("build/order45-fixed-h100.cnf")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("build/order45-fixed-h100.json")
    )
    arguments = parser.parse_args()

    record = first_record(arguments.catalog)
    h_graph = Graph.from_graph6(record)
    if (
        h_graph.order != 20
        or h_graph.size != 100
        or next(h_graph.clique_masks(4), None) is not None
        or next(h_graph.complement().clique_masks(5), None) is not None
    ):
        raise ValueError("catalog record is not the unique R(4,5,20,100) graph")

    variables, bounds = degree_bound_clauses(45, 20, 24, 990)
    fixed_h = []
    for left, right in itertools.combinations(range(20), 2):
        variable = edge_variable(left + 1, right + 1)
        fixed_h.append((variable,) if h_graph.has_edge(left, right) else (-variable,))
    j_literals = tuple(
        -edge_variable(left, right)
        for left, right in itertools.combinations(range(21, 45), 2)
    )
    variables, dense_j = cardinality_range_encoding(
        j_literals, 126, len(j_literals), variables
    )
    clause_count = (
        2 * comb(45, 5)
        + 44
        + len(bounds)
        + len(fixed_h)
        + len(dense_j)
    )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for source in (
            ramsey55_clauses(45),
            fixed_star_clauses(45, 20),
            bounds,
            fixed_h,
            dense_j,
        ):
            for clause in source:
                output.write(" ".join(map(str, clause)) + " 0\n")

    document = {
        "schema": SCHEMA,
        "catalog": str(arguments.catalog),
        "catalog_sha256": file_sha256(arguments.catalog),
        "graph6": record,
        "degree": 20,
        "edges_h": 100,
        "minimum_edges_j": 126,
        "variables": variables,
        "clauses": clause_count,
        "path": arguments.output.name,
        "sha256": file_sha256(arguments.output),
    }
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
