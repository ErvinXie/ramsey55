from __future__ import annotations

import itertools
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools/verify_generalized_graph_cover.py"


def encode(colors: tuple[int, ...]) -> int:
    value = 1
    for color in colors:
        value = value * 3 + color
    return value


class GeneralizedGraphCoverTests(unittest.TestCase):
    def cover_line(self, omit_blue_one_class: bool = False) -> str:
        completions = list(itertools.product((1, 2), repeat=3))[1:-1]
        if omit_blue_one_class:
            completions = [colors for colors in completions if colors.count(1) != 1]
        witnesses = [f"{encode(colors)}_0_1_2" for colors in completions]
        return " ".join([str(3**3), *witnesses]) + "\n"

    def run_verifier(self, cover: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                str(cover),
                "--order",
                "3",
                "--blue-clique",
                "3",
                "--red-clique",
                "3",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_accepts_exact_local_completion_set(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cover = root / "cover"
            cover.write_text(self.cover_line(), encoding="ascii")
            completed = self.run_verifier(cover, root / "audit.json")
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_rejects_missing_valid_completion(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cover = root / "cover"
            cover.write_text(self.cover_line(omit_blue_one_class=True), encoding="ascii")
            completed = self.run_verifier(cover, root / "audit.json")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("covered up to isomorphism", completed.stderr)


if __name__ == "__main__":
    unittest.main()
