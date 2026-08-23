from __future__ import annotations

import unittest

from tools.generate_asymmetric_ramsey_cnf import asymmetric_ramsey_clauses
from tools.generate_r45_upper_bound_cnf import (
    CLAUSES,
    VARIABLES,
    r45_upper_bound_clauses,
)
from tools.generate_r45_fixed_star_branches import fixed_star_clauses
from tools.verify_asymmetric_ramsey_cnf import expected_clauses as asymmetric_expected
from tools.verify_r45_upper_bound_cnf import expected_clauses


class R45UpperBoundCnfTests(unittest.TestCase):
    def test_dimensions_and_independent_reconstruction(self) -> None:
        generated = tuple(r45_upper_bound_clauses())
        self.assertEqual(VARIABLES, 300)
        self.assertEqual(CLAUSES, 65_780)
        self.assertEqual(generated, tuple(expected_clauses(25)))
        self.assertEqual(generated[0], (-1, -2, -4, -3, -5, -6))
        self.assertEqual(
            generated[-1],
            (231, 252, 274, 297, 253, 275, 298, 276, 299, 300),
        )

    def test_fixed_star_endpoints(self) -> None:
        self.assertEqual(tuple(fixed_star_clauses(0))[:3], ((-1,), (-2,), (-4,)))
        self.assertEqual(tuple(fixed_star_clauses(24))[-3:], ((232,), (254,), (277,)))

    def test_smaller_asymmetric_inputs(self) -> None:
        r35 = tuple(asymmetric_ramsey_clauses(14, 3, 5))
        self.assertEqual(len(r35), 2_366)
        self.assertEqual(r35[0], (-1, -2, -3))
        self.assertEqual(r35[-1], (55, 65, 76, 88, 66, 77, 89, 78, 90, 91))
        r44 = tuple(asymmetric_ramsey_clauses(18, 4, 4))
        self.assertEqual(len(r44), 6_120)
        self.assertEqual(r44[0], (-1, -2, -4, -3, -5, -6))
        self.assertEqual(r44[-1], (120, 135, 151, 136, 152, 153))
        self.assertEqual(r35, tuple(asymmetric_expected(14, 3, 5)))
        self.assertEqual(r44, tuple(asymmetric_expected(18, 4, 4)))


if __name__ == "__main__":
    unittest.main()
