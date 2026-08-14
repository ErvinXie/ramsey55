from __future__ import annotations

from itertools import product
import unittest

from ramsey55.cardinality import cardinality_range_encoding
from ramsey55.sat import clause_is_satisfied


class CardinalityEncodingTests(unittest.TestCase):
    def test_all_primary_and_auxiliary_assignments_through_size_four(self) -> None:
        for size in range(1, 5):
            inputs = tuple(range(1, size + 1))
            for lower in range(size + 1):
                for upper in range(lower, size + 1):
                    maximum, clauses = cardinality_range_encoding(
                        inputs, lower, upper, size
                    )
                    for primary in product((False, True), repeat=size):
                        extendible = False
                        for auxiliary in product(
                            (False, True), repeat=maximum - size
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
                        self.assertEqual(
                            extendible,
                            lower <= sum(primary) <= upper,
                            (size, lower, upper, primary),
                        )

    def test_rejects_invalid_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "range"):
            cardinality_range_encoding((1, 2), 2, 1, 2)
        with self.assertRaisesRegex(ValueError, "distinct"):
            cardinality_range_encoding((1, 1), 0, 1, 1)


if __name__ == "__main__":
    unittest.main()
