from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RefineAssumptionFrontierTests(unittest.TestCase):
    def test_splits_only_unknown_parents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "cubes.txt"
            cubes.write_text("a 4 -2 0\na -3 0\n", encoding="ascii")
            results = root / "results.tsv"
            results.write_text(
                "cube\tstatus\tseconds\n0\t20\t0.1\n1\t0\t0.2\n",
                encoding="ascii",
            )
            output = root / "children.txt"
            manifest = root / "children.json"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/refine_assumption_frontier.py"),
                    str(cubes),
                    str(results),
                    "--primary-variables",
                    "4",
                    "--output",
                    str(output),
                    "--manifest",
                    str(manifest),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(output.read_text(), "0 -3 1 0\n1 -3 -1 0\n")
            document = json.loads(manifest.read_text())
            self.assertEqual(document["unsat_parents"], 1)
            self.assertEqual(document["unknown_parents"], 1)
            self.assertEqual(document["child_cubes"], 2)

    def test_can_filter_without_splitting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "cubes.txt"
            cubes.write_text("a 4 -2 0\na -3 0\n", encoding="ascii")
            results = root / "results.tsv"
            results.write_text(
                "cube\tstatus\tseconds\n0\t20\t0.1\n1\t0\t0.2\n",
                encoding="ascii",
            )
            output = root / "unknown.txt"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/refine_assumption_frontier.py"),
                    str(cubes),
                    str(results),
                    "--primary-variables",
                    "4",
                    "--output",
                    str(output),
                    "--keep-unknown",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(output.read_text(), "0 -3 0\n")


if __name__ == "__main__":
    unittest.main()
