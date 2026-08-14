from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.audit_icnf_partition import audit_partition


class IcnfPartitionAuditTests(unittest.TestCase):
    def test_accepts_exact_ordered_partition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            whole = root / "whole.icnf"
            first = root / "first.icnf"
            second = root / "second.icnf"
            whole.write_text("a 1 0\na -2 3 0\na 4 0\n", encoding="ascii")
            first.write_text("a 1 0\n", encoding="ascii")
            second.write_text("a -2 3 0\na 4 0\n", encoding="ascii")
            manifest = audit_partition(whole, [first, second])
        self.assertEqual(manifest["whole"]["cubes"], 3)
        self.assertEqual(
            [(part["start"], part["stop"]) for part in manifest["parts"]],
            [(0, 1), (1, 3)],
        )

    def test_rejects_reordered_parts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            whole = root / "whole.icnf"
            first = root / "first.icnf"
            second = root / "second.icnf"
            whole.write_text("a 1 0\na 2 0\n", encoding="ascii")
            first.write_text("a 1 0\n", encoding="ascii")
            second.write_text("a 2 0\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "do not exactly equal"):
                audit_partition(whole, [second, first])


if __name__ == "__main__":
    unittest.main()
