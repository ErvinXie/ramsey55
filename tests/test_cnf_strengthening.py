from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.verify_cnf_strengthening import strengthening_manifest


class CnfStrengtheningTest(unittest.TestCase):
    def test_accepts_exact_clause_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.cnf"
            stronger = root / "stronger.cnf"
            base.write_text("c base\np cnf 2 2\n1 0\n-1 2 0\n", encoding="ascii")
            stronger.write_text(
                "c stronger\np cnf 3 3\n1 0\n-1 2 0\n3 0\n", encoding="ascii"
            )
            manifest = strengthening_manifest(base, stronger)
        self.assertEqual(manifest["relation"], "exact-clause-prefix")
        self.assertEqual(manifest["added_variables"], 1)
        self.assertEqual(manifest["added_clauses"], 1)

    def test_rejects_a_changed_base_clause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.cnf"
            stronger = root / "stronger.cnf"
            base.write_text("p cnf 2 2\n1 0\n-1 2 0\n", encoding="ascii")
            stronger.write_text("p cnf 3 3\n1 0\n1 2 0\n3 0\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "exact prefix"):
                strengthening_manifest(base, stronger)


if __name__ == "__main__":
    unittest.main()
