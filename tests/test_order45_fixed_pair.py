from __future__ import annotations

import itertools
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from tools.verify_order45_fixed_pair_cnf import (
    cardinality_range,
    contains_clique,
    decode_short_graph6,
    edge_count,
    find_automorphisms,
    lex_leader,
    verify,
)


ROOT = Path(__file__).resolve().parents[1]


def extend_assignment(
    clauses: list[tuple[int, ...]], primary: tuple[bool, ...], variables: int
) -> bool:
    auxiliary_count = variables - len(primary)
    for auxiliary in itertools.product((False, True), repeat=auxiliary_count):
        assignment = (False, *primary, *auxiliary)
        if all(
            any(
                assignment[abs(literal)] if literal > 0
                else not assignment[abs(literal)]
                for literal in clause
            )
            for clause in clauses
        ):
            return True
    return False


class FixedPairIndependentEncodingTests(unittest.TestCase):
    def test_reference_h100_record(self) -> None:
        record = (ROOT / "data/reference/r4520.100.g6").read_text().strip()
        adjacency = decode_short_graph6(record, 20)
        self.assertEqual(edge_count(adjacency), 100)
        self.assertFalse(contains_clique(adjacency, 4))
        self.assertEqual(len(find_automorphisms(adjacency)), 4)

    def test_automorphisms_of_four_cycle(self) -> None:
        adjacency = (0b1010, 0b0101, 0b1010, 0b0101)
        self.assertEqual(len(find_automorphisms(adjacency)), 8)

    def test_cardinality_range_semantics(self) -> None:
        variables, clauses = cardinality_range((1, 2, 3), 1, 2, 3)
        for primary in itertools.product((False, True), repeat=3):
            self.assertEqual(
                extend_assignment(clauses, primary, variables),
                1 <= sum(primary) <= 2,
            )

    def test_lex_leader_semantics(self) -> None:
        variables, clauses = lex_leader((1, 2, 3), (3, 2, 1), 3)
        for primary in itertools.product((False, True), repeat=3):
            right = (primary[2], primary[1], primary[0])
            self.assertEqual(
                extend_assignment(clauses, primary, variables), primary <= right
            )

    def test_cpp_generator_matches_independent_reconstruction(self) -> None:
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("a C++ compiler is not available")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = temporary / "generate_order45_fixed_pair_cnf"
            cnf = temporary / "pair.cnf"
            subprocess.run(
                [
                    compiler,
                    "-std=c++20",
                    "-O2",
                    "-DRAMSEY55_ORDER45_FIXED_PAIR",
                    str(ROOT / "tools/generate_degree18_pair_cnf.cpp"),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            subprocess.run(
                [
                    str(executable),
                    str(ROOT / "data/reference/r45_24.g6"),
                    "297775",
                    str(ROOT / "data/reference/r4520.100.g6"),
                    "0",
                    str(cnf),
                    "--no-symmetry",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = verify(
                SimpleNamespace(
                    h_catalog=ROOT / "data/reference/r4520.100.g6",
                    h_index=0,
                    j_catalog=ROOT / "data/reference/r45_24.g6",
                    j_index=297775,
                    cnf=cnf,
                    no_symmetry=True,
                )
            )
        self.assertEqual(report["variables"], 9746)
        self.assertEqual(report["clauses"], 114968)
        self.assertEqual(
            report["cnf_sha256"],
            "61a21ab44f1d10708f645ebdf70c1b6c4c3544c4548dfa36211a4f89271a4625",
        )


if __name__ == "__main__":
    unittest.main()
