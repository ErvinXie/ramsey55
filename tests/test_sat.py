from __future__ import annotations

import unittest
from pathlib import Path

from ramsey55 import Graph
from ramsey55.sat import (
    assignment_from_graph,
    edge_variable,
    ramsey55_clauses,
    variable_count,
    violated_clauses,
)


ROOT = Path(__file__).resolve().parents[1]


class SatEncodingTest(unittest.TestCase):
    def test_variable_bijection(self) -> None:
        for order in range(2, 15):
            variables = {
                edge_variable(u, v)
                for v in range(1, order)
                for u in range(v)
            }
            self.assertEqual(variables, set(range(1, variable_count(order) + 1)))

    def test_five_vertex_extremes(self) -> None:
        complete = Graph.from_edges(5, ((u, v) for v in range(5) for u in range(v)))
        empty = complete.complement()
        clauses = tuple(ramsey55_clauses(5))
        self.assertEqual(len(clauses), 2)
        self.assertEqual(
            len(
                tuple(
                    violated_clauses(clauses, assignment_from_graph(complete))
                )
            ),
            1,
        )
        self.assertEqual(
            len(tuple(violated_clauses(clauses, assignment_from_graph(empty)))),
            1,
        )

    def test_reference_42_graph_satisfies_cnf(self) -> None:
        line = (
            ROOT / "data/reference/r55_42some.g6"
        ).read_text(encoding="ascii").splitlines()[0]
        graph = Graph.from_graph6(line)
        violations = tuple(
            violated_clauses(ramsey55_clauses(42), assignment_from_graph(graph))
        )
        self.assertEqual(violations, ())

    def test_k43_near_miss_violates_exactly_two_clauses(self) -> None:
        rows = [
            line.strip()
            for line in (
                ROOT / "data/reference/k43_near_miss_1.matrix"
            ).read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        graph = Graph.from_adjacency_matrix(rows)
        violations = tuple(
            violated_clauses(ramsey55_clauses(43), assignment_from_graph(graph))
        )
        self.assertEqual(len(violations), 2)

        def clause_vertices(clause: tuple[int, ...]) -> tuple[int, ...]:
            variables = {abs(literal) for literal in clause}
            vertices: set[int] = set()
            for v in range(1, 43):
                for u in range(v):
                    if edge_variable(u, v) in variables:
                        vertices.update((u, v))
            return tuple(sorted(vertices))

        self.assertEqual(
            {clause_vertices(clause) for clause in violations},
            {
                (0, 2, 28, 29, 38),
                (0, 11, 28, 29, 38),
            },
        )


if __name__ == "__main__":
    unittest.main()
