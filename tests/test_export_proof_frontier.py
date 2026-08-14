from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.export_proof_frontier import (
    Row,
    read_cubes,
    read_rows,
    reconstruct_frontier,
)


class ProofFrontierExportTests(unittest.TestCase):
    def test_committed_pilot_is_hash_bound_unknown_telemetry(self) -> None:
        root = Path(__file__).parents[1]
        manifest = json.loads(
            (root / "data/order45-proof-frontier-pilot.json").read_text()
        )
        self.assertEqual(manifest["schema"], "ramsey55.proof-frontier-pilot.v1")
        self.assertIn("not an UNSAT certificate", manifest["claim"])
        self.assertEqual(
            manifest["exporter_sha256"],
            hashlib.sha256(
                (root / "tools/export_proof_frontier.py").read_bytes()
            ).hexdigest(),
        )
        for case in manifest["cases"]:
            counts = case["result_status_counts"]
            self.assertEqual(sum(counts.values()), case["frontier_cubes"])
            self.assertNotIn("10", counts)
            self.assertIn("0", counts)

    def test_reconstructs_depth_first_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "cubes.icnf"
            cubes.write_text("a 1 0\n", encoding="ascii")
            results = root / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t10\t0\t0\t-2\t0.1\n"
                "0\t1\t1\t10\t20\t1\t0\t0.2\n"
                "0\t2\t1\t10\t0\t0\t3\t0.3\n",
                encoding="ascii",
            )
            parsed_cubes = read_cubes(cubes)
            rows = read_rows(results, 0)
        self.assertEqual(
            reconstruct_frontier(parsed_cubes[0], rows),
            ((1, 2, 3), (1, 2, -3)),
        )

    def test_ignores_only_a_trailing_partial_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "4\t0\t0\t10\t0\t0\t2\t0.1\n"
                "4\t1\t1\t10",
                encoding="ascii",
            )
            rows = read_rows(results, 4)
        self.assertEqual(len(rows), 1)
        self.assertEqual(reconstruct_frontier((1,), rows), ((1, 2), (1, -2)))

    def test_rejects_non_dfs_depth(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected depth"):
            reconstruct_frontier(
                (1,),
                (
                    # A root split must be followed at depth one.
                    Row(0, 0, 2, 0, 3),
                ),
            )

    def test_rejects_incomplete_nonfinal_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "4\t0\t0\t10\n"
                "4\t1\t1\t10\t20\t1\t0\t0.2\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "incomplete nonfinal"):
                read_rows(results, 4)

    def test_selects_root_from_multi_root_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t10\t20\t1\t0\t0.1\n"
                "1\t1\t0\t10\t0\t0\t-3\t0.2\n"
                "1\t2\t1\t10\t20\t1\t0\t0.3\n",
                encoding="ascii",
            )
            rows = read_rows(results, 1)
        self.assertEqual(tuple(row.attempt for row in rows), (1, 2))
        self.assertEqual(reconstruct_frontier((2,), rows), ((2, 3),))

    def test_cli_appends_only_untouched_later_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "cubes.icnf"
            cubes.write_text("a 1 0\na 2 0\na 3 0\n", encoding="ascii")
            results = root / "results.tsv"
            results.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t10\t0\t0\t4\t0.1\n"
                "0\t1\t1\t10\t20\t1\t0\t0.2\n",
                encoding="ascii",
            )
            output = root / "frontier.icnf"
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "tools/export_proof_frontier.py"),
                    str(cubes),
                    "0",
                    str(results),
                    str(output),
                    "--include-later-roots",
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                read_cubes(output), ((1, -4), (2,), (3,))
            )


if __name__ == "__main__":
    unittest.main()
