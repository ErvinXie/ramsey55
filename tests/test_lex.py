from __future__ import annotations

from itertools import product
import unittest

from ramsey55.lex import lex_leq_encoding
from ramsey55.sat import clause_is_satisfied


class LexEncodingTests(unittest.TestCase):
    def test_all_assignments_through_width_four(self) -> None:
        for width in range(1, 5):
            left = tuple(range(1, width + 1))
            right = tuple(range(width + 1, 2 * width + 1))
            maximum, clauses = lex_leq_encoding(left, right, 2 * width)
            for primary in product((False, True), repeat=2 * width):
                extendible = False
                for auxiliary in product(
                    (False, True), repeat=maximum - 2 * width
                ):
                    values = primary + auxiliary
                    assignment = {
                        variable: values[variable - 1]
                        for variable in range(1, maximum + 1)
                    }
                    if all(
                        clause_is_satisfied(clause, assignment)
                        for clause in clauses
                    ):
                        extendible = True
                        break
                left_value = primary[:width]
                right_value = primary[width:]
                self.assertEqual(
                    extendible, left_value <= right_value,
                    (width, left_value, right_value),
                )


if __name__ == "__main__":
    unittest.main()
