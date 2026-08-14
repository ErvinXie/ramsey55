#!/usr/bin/env python3
"""Verify the public R(5,5) reference graphs without third-party packages."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from ramsey55 import Graph


def load_graph6(path: Path) -> list[Graph]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return [Graph.from_graph6(line) for line in lines]


def load_matrix(path: Path) -> Graph:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return Graph.from_adjacency_matrix(rows)


def verify_r55_42(path: Path) -> None:
    graphs = load_graph6(path)
    if len(graphs) != 328:
        raise AssertionError(f"expected 328 graph6 records, found {len(graphs)}")
    if any(graph.order != 42 for graph in graphs):
        raise AssertionError("not every reference graph has order 42")
    if len({graph.upper_triangle_bits() for graph in graphs}) != 328:
        raise AssertionError("duplicate labelled graph in the 328 representatives")

    edge_histogram = Counter(graph.size for graph in graphs)
    expected = {
        423: 1,
        424: 7,
        425: 29,
        426: 66,
        427: 89,
        428: 77,
        429: 43,
        430: 16,
    }
    if edge_histogram != expected:
        raise AssertionError(
            f"edge histogram differs from published values: {edge_histogram}"
        )

    family = graphs + [graph.complement() for graph in graphs]
    if len({graph.upper_triangle_bits() for graph in family}) != 656:
        raise AssertionError("the representatives and complements are not distinct")

    invalid = [
        index for index, graph in enumerate(family) if not graph.is_ramsey_55_graph()
    ]
    if invalid:
        raise AssertionError(f"graphs failing the Ramsey(5,5) predicate: {invalid}")

    degree_values = sorted({degree for graph in family for degree in graph.degrees})
    if degree_values != [19, 20, 21, 22]:
        raise AssertionError(f"unexpected degree support: {degree_values}")

    print("R(5,5,42) reference family")
    print(f"  representatives: {len(graphs)}")
    print(f"  with complements: {len(family)}")
    print(f"  edge histogram: {dict(sorted(edge_histogram.items()))}")
    print(f"  degree support: {degree_values}")
    print("  monochromatic K5: 0 in every graph")


def verify_k43_near_miss(path: Path) -> None:
    graph = load_matrix(path)
    graph_cliques = graph.cliques(5)
    complement_cliques = graph.complement().cliques(5)
    total = len(graph_cliques) + len(complement_cliques)
    if graph.order != 43:
        raise AssertionError(f"expected order 43, found {graph.order}")
    if total != 2:
        raise AssertionError(f"expected exactly 2 monochromatic K5s, found {total}")

    print("K43 near miss")
    print(f"  edges/nonedges: {graph.size}/{43 * 42 // 2 - graph.size}")
    print(f"  K5 in encoded graph: {graph_cliques}")
    print(f"  K5 in complement: {complement_cliques}")
    print(f"  total monochromatic K5: {total}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--r55-42",
        type=Path,
        default=Path("data/reference/r55_42some.g6"),
    )
    parser.add_argument(
        "--k43-near-miss",
        type=Path,
        default=Path("data/reference/k43_near_miss_1.matrix"),
    )
    args = parser.parse_args()

    verify_r55_42(args.r55_42)
    verify_k43_near_miss(args.k43_near_miss)


if __name__ == "__main__":
    main()
