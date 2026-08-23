from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_r45_gluing_selector_formula.py"
VERIFIER = ROOT / "tools/verify_r45_gluing_selector_formula.py"


class R45GluingSelectorFormulaTests(unittest.TestCase):
    def generate(self, root: Path) -> tuple[Path, Path]:
        covers = root / "covers"
        covers.mkdir()
        (covers / "gen358").write_text(
            f"{3 ** 28} witness\n{3 ** 28} duplicate\n", encoding="ascii"
        )
        (covers / "gen4416").write_text(
            f"{3 ** 120} witness\n{3 ** 120} duplicate\n", encoding="ascii"
        )
        output = root / "selector"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--cover-dir",
                str(covers),
                "--degree",
                "8",
                "--output-dir",
                str(output),
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        return output / "manifest.json", covers

    def test_independent_reconstruction_accepts_formula(self) -> None:
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
            self.assertEqual(document["variables"], 280)
            self.assertEqual(document["clauses"], 53132)
            self.assertEqual(document["pair_count"], 4)

    def test_independent_reconstruction_rejects_clause_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, covers = self.generate(Path(raw))
            document = json.loads(manifest.read_text())
            cnf = manifest.parent / document["cnf"]["path"]
            lines = cnf.read_text(encoding="ascii").splitlines()
            lines[-1] = "277 0"
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
            self.assertIn("clause", completed.stderr)


if __name__ == "__main__":
    unittest.main()
