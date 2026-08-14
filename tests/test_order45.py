from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ramsey55 import Graph, normalize_order45_degree_branch
from ramsey55.sat import write_dimacs
from tools.verify_order45_benchmarks import verify_exact_cnf
from tools.analyze_order45_excess_coverage import (
    analyze_split,
    doubled_local_constant,
    minimum_edge_sum,
    short_graph6_order_and_size,
)


def circulant(order: int, half_degree: int) -> Graph:
    return Graph.from_edges(
        order,
        {
            tuple(sorted((vertex, (vertex + step) % order)))
            for vertex in range(order)
            for step in range(1, half_degree + 1)
        },
    )


class Order45ReductionTests(unittest.TestCase):
    def test_normalizes_degree_20_branch(self) -> None:
        graph = circulant(45, 10)
        result = normalize_order45_degree_branch(graph)
        self.assertEqual(result.degree, 20)
        self.assertFalse(result.complemented)
        self.assertEqual(result.graph.degrees[0], 20)
        self.assertTrue(all(result.graph.has_edge(0, v) for v in range(1, 21)))
        self.assertTrue(all(not result.graph.has_edge(0, v) for v in range(21, 45)))

    def test_normalizes_degree_22_branch(self) -> None:
        result = normalize_order45_degree_branch(circulant(45, 11))
        self.assertEqual(result.degree, 22)
        self.assertFalse(result.complemented)
        self.assertEqual(result.graph.degrees[0], 22)

    def test_complements_degree_24_to_degree_20(self) -> None:
        graph = circulant(45, 12)
        result = normalize_order45_degree_branch(graph)
        self.assertEqual(result.degree, 20)
        self.assertTrue(result.complemented)
        self.assertEqual(result.graph.size, graph.complement().size)

    def test_rejects_graph_outside_degree_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "degree window"):
            normalize_order45_degree_branch(Graph.from_edges(45, ()))


class Order45CnfVerificationTests(unittest.TestCase):
    def test_independent_verifier_accepts_exact_small_instance(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "small.cnf"
            expected = write_dimacs(path, 7, fixed_star_degree=2)
            self.assertEqual(verify_exact_cnf(path, 7, 2), expected)

    def test_independent_verifier_rejects_changed_clause(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "small.cnf"
            write_dimacs(path, 6, fixed_star_degree=2)
            lines = path.read_text(encoding="ascii").splitlines()
            lines[1] = lines[1].replace("-1", "1", 1)
            path.write_text("\n".join(lines) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "differs"):
                verify_exact_cnf(path, 6, 2)


class Order45ExcessCoverageTests(unittest.TestCase):
    def test_local_constants_and_thresholds(self) -> None:
        self.assertEqual(
            [doubled_local_constant(degree) for degree in range(20, 25)],
            [452, 443, 440, 443, 452],
        )
        self.assertEqual(
            [minimum_edge_sum(degree) for degree in (20, 21, 22)],
            [226, 222, 220],
        )

    def test_edge_pair_coverage_is_not_confused_with_gluing(self) -> None:
        histograms = {
            20: {98: 2, 99: 3, 100: 5},
            24: {edges: 1 for edges in range(116, 133)},
        }
        report = analyze_split(20, histograms)
        self.assertEqual(len(report.possible_pairs), 28)
        self.assertEqual(len(report.available_pairs), 18)
        self.assertEqual(report.raw_available_record_pairs, 2 * 5 + 3 * 6 + 5 * 7)

    def test_degree22_colour_swap_quotient(self) -> None:
        report = analyze_split(22, {22: {113: 2, 114: 3}})
        self.assertEqual(len(report.possible_pairs), 45)
        self.assertEqual(len(report.available_pairs), 4)
        self.assertEqual(report.raw_available_record_pairs, 25)
        self.assertEqual(report.symmetry_reduced_record_pairs, 15)

    def test_graph6_size_decoder(self) -> None:
        graph = circulant(24, 3)
        self.assertEqual(
            short_graph6_order_and_size(graph.to_graph6()),
            (24, graph.size),
        )


if __name__ == "__main__":
    unittest.main()
