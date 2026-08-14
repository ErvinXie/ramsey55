from __future__ import annotations

from itertools import combinations
from pathlib import Path
import unittest

from ramsey55 import Graph
from tools.generate_catalog_flip_certificate import (
    flip_is_ramsey_free,
    toggled_graph,
)


class GraphTest(unittest.TestCase):
    def test_complete_and_empty_graphs(self) -> None:
        complete = Graph.from_edges(6, ((u, v) for v in range(6) for u in range(v)))
        self.assertEqual(complete.size, 15)
        self.assertEqual(len(complete.cliques(5)), 6)
        self.assertEqual(len(complete.complement().cliques(5)), 0)

        empty = Graph.from_edges(6, ())
        self.assertEqual(empty.size, 0)
        self.assertEqual(len(empty.cliques(5)), 0)
        self.assertEqual(len(empty.complement().cliques(5)), 6)

    def test_cycle_five_graph6(self) -> None:
        # NetworkX/nauty graph6 encoding of C5.
        cycle = Graph.from_graph6("Dhc")
        self.assertEqual(cycle.order, 5)
        self.assertEqual(cycle.size, 5)
        self.assertEqual(sorted(cycle.degrees), [2, 2, 2, 2, 2])
        self.assertEqual(cycle.complement().size, 5)
        self.assertEqual(Graph.from_graph6(cycle.to_graph6()), cycle)

    def test_matrix_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "symmetric"):
            Graph.from_adjacency_matrix(["01", "00"])
        with self.assertRaisesRegex(ValueError, "loop"):
            Graph.from_adjacency_matrix(["10", "00"])

    def test_clique_enumerator_against_all_graphs_on_five_vertices(self) -> None:
        pairs = tuple(combinations(range(5), 2))
        for encoded_edges in range(1 << len(pairs)):
            edges = {
                pair
                for index, pair in enumerate(pairs)
                if encoded_edges & (1 << index)
            }
            graph = Graph.from_edges(5, edges)
            self.assertEqual(Graph.from_graph6(graph.to_graph6()), graph)
            for size in range(1, 6):
                expected = {
                    vertices
                    for vertices in combinations(range(5), size)
                    if all(
                        (min(u, v), max(u, v)) in edges
                        for u, v in combinations(vertices, 2)
                    )
                }
                self.assertEqual(set(graph.cliques(size)), expected)

    def test_local_single_flip_criterion_against_full_check(self) -> None:
        path = Path("data/reference/r55_42some.g6")
        record = next(
            line.strip()
            for line in path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        )
        graph = Graph.from_graph6(record)
        for v in range(1, graph.order):
            for u in range(v):
                edge = (u, v)
                self.assertEqual(
                    flip_is_ramsey_free(graph, edge),
                    toggled_graph(graph, edge).is_ramsey_55_graph(),
                )


if __name__ == "__main__":
    unittest.main()
