from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_screened_split_budget",
    ROOT / "tools" / "analyze_screened_split_budget.py",
)
assert SPEC is not None and SPEC.loader is not None
ANALYSIS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYSIS
SPEC.loader.exec_module(ANALYSIS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScreenedSplitBudgetTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> Path:
        variables = root / "variables.txt"
        variables.write_text("10,20\n", encoding="ascii")
        rows = [
            "cube\tstatus\tseconds\tmodel",
            "0\t20\t0.080000\t",
            "1\t0\t1.000000\t",
            "2\t20\t0.150000\t",
            "3\t0\t1.000000\t",
        ]
        sources = []
        for index, first_seconds in enumerate(("0.080000", "0.090000")):
            results = root / f"solver-{index}.tsv"
            source_rows = rows.copy()
            source_rows[1] = f"0\t20\t{first_seconds}\t"
            results.write_text("\n".join(source_rows) + "\n", encoding="ascii")
            sources.append(
                {
                    "path": str(root / f"solver-{index}"),
                    "sha256": str(index) * 64,
                    "arguments": [],
                    "results": str(results),
                    "results_sha256": sha256(results),
                    "log": str(root / f"solver-{index}.log"),
                    "log_sha256": "f" * 64,
                }
            )
        selection = root / "selection.json"
        selection.write_text(
            json.dumps(
                {
                    "schema": ANALYSIS.SCHEMA,
                    "parents": {"count": 1},
                    "variables": {
                        "path": str(variables),
                        "sha256": sha256(variables),
                        "count": 2,
                    },
                    "screen_seconds": 1.0,
                    "screen_solvers": sources,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return selection

    def test_replays_smaller_time_and_variable_budget(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            selection = self.make_fixture(Path(raw))
            replay = ANALYSIS.analyze_selection(selection, 0.1, {10, 20})
            self.assertTrue(replay["feasible"])
            self.assertEqual(replay["candidate_counts"], [1])
            self.assertEqual(replay["candidates"][0][0]["variable"], 10)
            self.assertFalse(
                ANALYSIS.analyze_selection(selection, 0.07, {10, 20})["feasible"]
            )
            self.assertFalse(
                ANALYSIS.analyze_selection(selection, 0.1, {20})["feasible"]
            )

    def test_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            selection = self.make_fixture(Path(raw))
            document = json.loads(selection.read_text(encoding="utf-8"))
            document["variables"]["sha256"] = "0" * 64
            selection.write_text(json.dumps(document) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                ANALYSIS.analyze_selection(selection, 0.1, None)


if __name__ == "__main__":
    unittest.main()
