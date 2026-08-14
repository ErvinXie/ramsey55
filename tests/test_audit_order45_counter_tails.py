from __future__ import annotations

import hashlib
import unittest

from tools.audit_order45_counter_tails import (
    clause_bytes,
    clause_stream_sha256,
    input_identifiers,
    integer_sequence_sha256,
)


class Order45CounterTailAuditTests(unittest.TestCase):
    def test_canonical_clause_stream(self) -> None:
        clauses = ((1, -2), (), (3,))
        encoded = b"1 -2 0\n0\n3 0\n"
        self.assertEqual(b"".join(map(clause_bytes, clauses)), encoded)
        self.assertEqual(
            clause_stream_sha256(clauses), hashlib.sha256(encoded).hexdigest()
        )

    def test_input_identifier_dimensions_and_endpoints(self) -> None:
        expected = {
            20: (190, 3, 210, 276, 253, 990),
            21: (210, 3, 231, 253, 276, 990),
            22: (231, 3, 253, 231, 300, 990),
        }
        for degree, values in expected.items():
            h_inputs, j_inputs = input_identifiers(degree)
            self.assertEqual(
                (
                    len(h_inputs),
                    h_inputs[0],
                    h_inputs[-1],
                    len(j_inputs),
                    j_inputs[0],
                    j_inputs[-1],
                ),
                values,
            )

    def test_integer_sequence_hash_is_unambiguous(self) -> None:
        self.assertNotEqual(
            integer_sequence_sha256((1, 23)),
            integer_sequence_sha256((12, 3)),
        )


if __name__ == "__main__":
    unittest.main()
