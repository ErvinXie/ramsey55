from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_order45_fixed_pair_proofs import (
    audit_results,
    audit_selective_runner_log,
    cube_count,
    cube_variables,
    dimacs_shape,
)


class FixedPairProofAuditTests(unittest.TestCase):
    def test_selective_freeze_pilot_is_explicit_unknown_telemetry(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pilot = json.loads(
            (root / "data/order45-selective-freeze-pilot.json").read_text()
        )
        self.assertIn("not an UNSAT certificate", pilot["claim"])
        self.assertEqual(len(pilot["results"]), 8)
        for result in pilot["results"]:
            self.assertEqual(
                result["open"],
                result["splits"] - result["closed"] + result["roots_seen"],
            )
            self.assertGreater(result["open"], 0)

    def test_dimacs_shape_and_cube_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            cnf = temporary / "tiny.cnf"
            cnf.write_text("c tiny\np cnf 2 2\n1 0\n-1 2 0\n", encoding="ascii")
            cubes = temporary / "tiny.icnf"
            cubes.write_text("a 1 0\na -1 0\n", encoding="ascii")
            self.assertEqual(dimacs_shape(cnf), (2, 2))
            self.assertEqual(cube_count(cubes), 2)
            self.assertEqual(cube_variables(cubes), {1})

    def test_selective_runner_log_binds_freeze_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "runner.log"
            log.write_text(
                "conflicts\t10000\n"
                "maximum_conflicts\t128000\n"
                "maximum_lookahead_seconds\t1\n"
                "maximum_primary_split_variable\t480\n"
                "maximum_solve_seconds\t5\n"
                "freeze_policy\tselective\n"
                "root_index\tall\n"
                "initial_frozen_variables\t494\n",
                encoding="utf-8",
            )
            audit_selective_runner_log(log, 10000, 128000, 1.0, 480, 5.0, 494)

    def test_balanced_result_forest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t1\t0\t0\t2\t0.1\n"
                "0\t1\t1\t1\t20\t1\t0\t0.2\n"
                "0\t2\t1\t1\t20\t1\t0\t0.3\n"
                "1\t3\t0\t1\t20\t1\t0\t0.4\n",
                encoding="ascii",
            )
            report = audit_results(results, 2)
        self.assertEqual(report["attempts"], 4)
        self.assertEqual(report["covered_roots"], 2)
        self.assertEqual(report["global_unsat_cores"], 0)
        self.assertEqual(report["splits"], 1)
        self.assertEqual(report["unsat_leaves"], 3)
        self.assertEqual(report["maximum_extra_depth"], 1)
        self.assertEqual(report["minimum_conflict_limit"], 1)
        self.assertEqual(report["maximum_conflict_limit"], 1)
        self.assertEqual(report["reported_solve_seconds"], 1.0)

    def test_unbalanced_result_forest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t1\t0\t0\t2\t0.1\n"
                "0\t1\t1\t1\t20\t1\t0\t0.2\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "unbalanced"):
                audit_results(results, 1)

    def test_global_unsat_core_allows_early_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t10\t20\t0\t0\t0.1\n",
                encoding="ascii",
            )
            report = audit_results(results, 2)
        self.assertEqual(report["covered_roots"], 1)
        self.assertEqual(report["global_unsat_cores"], 1)


if __name__ == "__main__":
    unittest.main()
