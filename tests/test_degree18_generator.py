from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Degree18GeneratorTest(unittest.TestCase):
    def test_cardinality_encoding_exhaustively_on_small_instances(self) -> None:
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("a C++ compiler is not available")
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "generate_degree18_fixed_cnf"
            subprocess.run(
                [
                    compiler,
                    "-std=c++20",
                    "-O2",
                    str(ROOT / "tools/generate_degree18_fixed_cnf.cpp"),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            completed = subprocess.run(
                [str(executable), "--self-test-cardinality"],
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(
            completed.stdout.strip(), "cardinality encoding self-test passed"
        )

    def test_pair_symmetry_encoding_and_automorphisms(self) -> None:
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("a C++ compiler is not available")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = temporary / "generate_degree18_pair_cnf"
            subprocess.run(
                [
                    compiler,
                    "-std=c++20",
                    "-O2",
                    str(ROOT / "tools/generate_degree18_pair_cnf.cpp"),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            self_test = subprocess.run(
                [str(executable), "--self-test-symmetry"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                self_test.stdout.strip(), "symmetry encoding self-test passed"
            )

            no_symmetry = temporary / "pair-no-symmetry.cnf"
            subprocess.run(
                [
                    str(executable),
                    str(ROOT / "data/reference/r45_24.g6"),
                    "35",
                    str(ROOT / "data/reference/r4518.85.g6"),
                    "0",
                    str(no_symmetry),
                    "--no-symmetry",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                hashlib.sha256(no_symmetry.read_bytes()).hexdigest(),
                "f12d41fbb2550e2e494bd9fea161a1f7d283d5232d5e316e585dc5763bf87681",
            )

            symmetric = temporary / "pair-symmetric.cnf"
            generated = subprocess.run(
                [
                    str(executable),
                    str(ROOT / "data/reference/r45_24.g6"),
                    "35",
                    str(ROOT / "data/reference/r4518.85.g6"),
                    "0",
                    str(symmetric),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            statistics = dict(
                line.split("\t", 1) for line in generated.stdout.splitlines()
            )
            self.assertEqual(statistics["variables"], "10162")
            self.assertEqual(statistics["A_automorphisms"], "8")
            self.assertEqual(statistics["H_automorphisms"], "1")
            self.assertEqual(statistics["symmetry_clauses"], "9174")


if __name__ == "__main__":
    unittest.main()
