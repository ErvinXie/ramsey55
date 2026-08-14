from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "tools/compose_binary_drat.py"


class ComposeBinaryDratTests(unittest.TestCase):
    def test_concatenates_fragments_and_appends_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.drat"
            second = root / "second.drat"
            output = root / "combined.drat"
            first.write_bytes(b"first\0")
            second.write_bytes(b"second\0")
            subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--append-empty",
                    str(output),
                    str(first),
                    str(second),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(output.read_bytes(), b"first\0second\0a\0")

    def test_rejects_overwriting_a_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fragment = Path(directory) / "fragment.drat"
            fragment.write_bytes(b"proof")
            completed = subprocess.run(
                [sys.executable, str(TOOL), str(fragment), str(fragment)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(fragment.read_bytes(), b"proof")


if __name__ == "__main__":
    unittest.main()
