from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/summarize_r45_gluing_sample.py"
SPEC = importlib.util.spec_from_file_location("summarize_r45_gluing_sample", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class R45GluingSampleSummaryTests(unittest.TestCase):
    def test_elapsed_seconds_accepts_both_gnu_time_forms(self) -> None:
        self.assertEqual(MODULE.elapsed_seconds("2:03.50"), 123.5)
        self.assertEqual(MODULE.elapsed_seconds("1:02:03"), 3723.0)

    def test_distribution_uses_nearest_rank(self) -> None:
        summary = MODULE.distribution(list(range(1, 101)))
        self.assertEqual(summary["p50_nearest_rank"], 50)
        self.assertEqual(summary["p95_nearest_rank"], 95)
        self.assertEqual(summary["p99_nearest_rank"], 99)

    def test_summarizes_hash_bound_checked_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            proof_dir = root / "proofs"
            proof_dir.mkdir()

            def artifact(name: str, contents: bytes) -> dict[str, object]:
                path = proof_dir / name
                path.write_bytes(contents)
                return {
                    "path": name,
                    "bytes": len(contents),
                    "sha256": MODULE.file_sha256(path),
                }

            time_template = (
                "User time (seconds): {user}\n"
                "Elapsed (wall clock) time (h:mm:ss or m:ss): {wall}\n"
                "Maximum resident set size (kbytes): {rss}\n"
                "Exit status: {status}\n"
            )
            proof = artifact("sample.drat", b"proof\n")
            solver_time = artifact(
                "sample.solver.time.log",
                time_template.format(user="2.5", wall="0:03.00", rss=12, status=20).encode(),
            )
            checker_time = artifact(
                "sample.checker.time.log",
                time_template.format(user="4.5", wall="0:05.00", rss=34, status=0).encode(),
            )
            branches = {
                "schema": "ramsey55.r45-gluing-branches.v2",
                "fixed_star_degree": 10,
                "total_pairs": 100,
                "files": [{"pair_index": 7}],
            }
            branch_manifest = root / "branches.json"
            branch_manifest.write_text(json.dumps(branches), encoding="utf-8")
            proofs = {
                "schema": "ramsey55.r45-gluing-proofs.v1",
                "branch_manifest": {
                    "schema": branches["schema"],
                    "sha256": MODULE.file_sha256(branch_manifest),
                },
                "summary": {"complete_unsat": True},
                "results": [
                    {
                        "pair_index": 7,
                        "proof": proof,
                        "solver_time": solver_time,
                        "checker_time": checker_time,
                    }
                ],
            }
            proof_manifest = root / "proofs.json"
            proof_manifest.write_text(json.dumps(proofs), encoding="utf-8")

            summary = MODULE.summarize(
                proof_manifest, branch_manifest, proof_dir
            )
            self.assertEqual(summary["sample_formulas"], 1)
            self.assertEqual(summary["total_pairs"], 100)
            self.assertEqual(summary["distribution"]["proof_bytes"]["sum"], 6)
            self.assertEqual(
                summary["distribution"]["solver_user_seconds"]["sum"], 2.5
            )
            self.assertEqual(
                summary["distribution"]["checker_max_rss_kbytes"]["max"], 34
            )


if __name__ == "__main__":
    unittest.main()
