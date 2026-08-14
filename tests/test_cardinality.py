from __future__ import annotations

from itertools import product
import unittest

from ramsey55.cardinality import at_least_counter_encoding, cardinality_range_encoding
from ramsey55.sat import clause_is_satisfied


class CardinalityEncodingTests(unittest.TestCase):
    def test_observable_counter_outputs_exact_count(self) -> None:
        maximum, clauses, outputs = at_least_counter_encoding((1, -2, 3), 3, 3)
        for primary in product((False, True), repeat=3):
            satisfying = []
            for auxiliary in product((False, True), repeat=maximum - 3):
                values = primary + auxiliary
                assignment = {v: values[v - 1] for v in range(1, maximum + 1)}
                if all(clause_is_satisfied(c, assignment) for c in clauses):
                    satisfying.append(assignment)
            self.assertEqual(len(satisfying), 1)
            count = int(primary[0]) + int(not primary[1]) + int(primary[2])
            self.assertEqual(
                tuple(satisfying[0][v] for v in outputs),
                tuple(j <= count for j in range(1, 4)),
            )
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

    def test_signed_literals_count_their_satisfied_values(self) -> None:
        inputs = (1, -2, 3)
        for lower in range(4):
            for upper in range(lower, 4):
                maximum, clauses = cardinality_range_encoding(
                    inputs, lower, upper, 3
                )
                for primary in product((False, True), repeat=3):
                    extendible = False
                    for auxiliary in product((False, True), repeat=maximum - 3):
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
                    count = int(primary[0]) + int(not primary[1]) + int(primary[2])
                    self.assertEqual(extendible, lower <= count <= upper)


if __name__ == "__main__":
    unittest.main()
