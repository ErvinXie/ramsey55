from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_r45_gluing_branches.py"
VERIFIER = ROOT / "tools/verify_r45_gluing_branches.py"


class R45GluingBranchTests(unittest.TestCase):
    def generate(self, root: Path) -> tuple[Path, Path]:
        covers = root / "covers"
        covers.mkdir()
        # A leading one followed by all-zero ternary digits encodes an all-hole graph.
        (covers / "gen358").write_text(f"{3 ** 28} witness\n", encoding="ascii")
        (covers / "gen4416").write_text(f"{3 ** 120} witness\n", encoding="ascii")
        output = root / "branches"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--cover-dir",
                str(covers),
                "--degree",
                "8",
                "--pair-count",
                "1",
                "--output-dir",
                str(output),
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        return output / "manifest.json", covers

    def test_independent_reconstruction_accepts_generated_branch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, covers = self.generate(Path(raw))
            subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    str(manifest),
                    "--cover-dir",
                    str(covers),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            document = json.loads(manifest.read_text())
            self.assertEqual(document["total_pairs"], 1)
            self.assertEqual(document["files"][0]["variables"], 276)
            self.assertEqual(document["files"][0]["clauses"], 53130)

    def test_independent_reconstruction_rejects_clause_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, covers = self.generate(Path(raw))
            document = json.loads(manifest.read_text())
            cnf = manifest.parent / document["files"][0]["path"]
            lines = cnf.read_text(encoding="ascii").splitlines()
            lines[1] = "1 0"
            cnf.write_text("\n".join(lines) + "\n", encoding="ascii")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(VERIFIER),
                    str(manifest),
                    "--cover-dir",
                    str(covers),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("clause 1 differs", completed.stderr)


if __name__ == "__main__":
    unittest.main()
