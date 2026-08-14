from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "tools" / "verify_minimal_flip_models.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("verify_minimal_flip_models", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FlipVerificationTests(unittest.TestCase):
    def test_adds_model_blocks_and_updates_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.cnf"
            destination = Path(directory) / "blocked.cnf"
            source.write_text("c example\np cnf 9 2\n1 0\n-2 3 0\n", encoding="ascii")
            MODULE.add_blocking_clauses(
                source, destination, [(0, 2, 4, 8), (1, 3, 5, 7)]
            )
            self.assertEqual(
                destination.read_text(encoding="ascii"),
                "c example\np cnf 9 4\n1 0\n-2 3 0\n"
                "-1 -3 -5 -9 0\n-2 -4 -6 -8 0\n",
            )

    def test_rejects_missing_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.cnf"
            destination = Path(directory) / "blocked.cnf"
            source.write_text("1 0\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "missing DIMACS header"):
                MODULE.add_blocking_clauses(source, destination, [])


if __name__ == "__main__":
    unittest.main()
