from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_order45_strata_leaf_proofs import (
    audit_root_results,
    read_bound_cubes,
)


class Order45StrataLeafProofAuditTests(unittest.TestCase):
    def test_committed_pilot_is_explicit_unknown_telemetry(self) -> None:
        root = Path(__file__).resolve().parents[1]
        document = json.loads(
            (root / "data/order45-strata-leaf-pilot.json").read_text()
        )
        self.assertEqual(document["schema"], "ramsey55.order45-strata-leaf-pilot.v1")
        self.assertIn("not an UNSAT certificate", document["claim"])
        self.assertEqual(document["timeout_seconds"], 120)
        self.assertEqual(len(document["cases"]), 3)
        self.assertEqual(len(document["configurations"]), 3)
        for configuration in document["configurations"]:
            self.assertEqual(len(configuration["results"]), 3)
            for result in configuration["results"]:
                self.assertEqual(
                    result["open"], 1 + result["splits"] - result["closed"]
                )
                self.assertGreater(result["open"], 0)

    def test_reads_hash_bound_cubes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cubes.txt"
            path.write_text(
                "c manifest_sha256 abc\n"
                "c cnf_sha256 def\n"
                "c degree 20\n"
                "0 1 -2 0\n"
                "1 -1 2 0\n",
                encoding="ascii",
            )
            metadata, cubes = read_bound_cubes(path)
        self.assertEqual(
            metadata,
            {"manifest_sha256": "abc", "cnf_sha256": "def", "degree": "20"},
        )
        self.assertEqual(cubes, ((1, -2), (-1, 2)))

    def test_audits_complete_single_root_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.tsv"
            path.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "7\t0\t0\t10\t0\t0\t3\t0.1\n"
                "7\t1\t1\t10\t20\t2\t0\t0.2\n"
                "7\t2\t1\t10\t20\t1\t0\t0.3\n",
                encoding="ascii",
            )
            report = audit_root_results(path, 7)
        self.assertEqual(report["attempts"], 3)
        self.assertEqual(report["splits"], 1)
        self.assertEqual(report["unsat_leaves"], 2)
        self.assertEqual(report["maximum_extra_depth"], 1)

    def test_rejects_unbalanced_root_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.tsv"
            path.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t10\t0\t0\t3\t0.1\n"
                "0\t1\t1\t10\t20\t2\t0\t0.2\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "unbalanced"):
                audit_root_results(path, 0)


if __name__ == "__main__":
    unittest.main()
