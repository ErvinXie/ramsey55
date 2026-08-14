from __future__ import annotations

from itertools import combinations
import unittest

from ramsey55 import Graph
from ramsey55.excess import doubled_local_excess, verify_global_excess_identity
from ramsey55.order45 import (
    doubled_order45_local_excess_constant,
    order45_excess_minimum_edge_sum,
)


class ExcessIdentityTests(unittest.TestCase):
    def test_identity_on_every_graph_through_order_five(self) -> None:
        for order in range(1, 6):
            pairs = tuple(combinations(range(order), 2))
            for bits in range(1 << len(pairs)):
                graph = Graph.from_edges(
                    order,
                    (pair for index, pair in enumerate(pairs) if bits & (1 << index)),
                )
                self.assertTrue(verify_global_excess_identity(graph))

    def test_order45_constants_and_thresholds(self) -> None:
        self.assertEqual(
            [doubled_order45_local_excess_constant(d) for d in range(20, 25)],
            [452, 443, 440, 443, 452],
        )
        self.assertEqual(
            [order45_excess_minimum_edge_sum(d) for d in (20, 21, 22)],
            [226, 222, 220],
        )

    def test_complete_and_empty_graph_contributions_cancel(self) -> None:
        complete = Graph.from_edges(8, combinations(range(8), 2))
        empty = Graph.from_edges(8, ())
        self.assertTrue(all(doubled_local_excess(complete, v) == 0 for v in range(8)))
        self.assertTrue(all(doubled_local_excess(empty, v) == 0 for v in range(8)))
