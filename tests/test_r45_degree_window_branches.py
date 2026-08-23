from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_r45_degree_window_branches.py"
VERIFIER = ROOT / "tools/verify_r45_degree_window_branches.py"


class R45DegreeWindowBranchTests(unittest.TestCase):
    def generate(self, root: Path) -> Path:
        output = root / "branches"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--output-dir",
                str(output),
                "--degree",
                "8",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        return output / "manifest.json"

    def test_independent_reconstruction_accepts_generated_branch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest = self.generate(Path(raw))
            subprocess.run(
                [sys.executable, str(VERIFIER), str(manifest)],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            document = json.loads(manifest.read_text())
            self.assertEqual(document["fixed_star_degrees"], [8])
            self.assertEqual(document["files"][0]["variables"], 6180)
            self.assertEqual(document["files"][0]["clauses"], 88460)

    def test_independent_reconstruction_rejects_clause_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest = self.generate(Path(raw))
            document = json.loads(manifest.read_text())
            cnf = manifest.parent / document["files"][0]["path"]
            lines = cnf.read_text(encoding="ascii").splitlines()
            lines[1] = "1 0"
            cnf.write_text("\n".join(lines) + "\n", encoding="ascii")
            completed = subprocess.run(
                [sys.executable, str(VERIFIER), str(manifest)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("clause 1 differs", completed.stderr)


if __name__ == "__main__":
    unittest.main()
