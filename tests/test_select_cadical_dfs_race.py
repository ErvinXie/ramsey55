from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/select_cadical_dfs_race.py"
HEADER = "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"


def producer_log(
    status: int, attempts: int, splits: int, depth: int, cubes: int = 1
) -> str:
    extra = "checkpoint\t1\n" if status == 0 else f"cubes\t{cubes}\n"
    return (
        "proof_fragment\t1\n"
        "root_index\tall\n"
        + extra
        + f"status\t{status}\n"
        + f"attempts\t{attempts}\n"
        + f"splits\t{splits}\n"
        + f"maximum_extra_depth\t{depth}\n"
    )


class CadicalDfsRaceSelectionTests(unittest.TestCase):
    def run_tool(
        self,
        directory: Path,
        races: list[tuple[bytes, str, str]],
        expect_success: bool = True,
        roots: str = "a 1 0\n",
    ) -> subprocess.CompletedProcess[str]:
        root = directory / "root.icnf"
        root.write_text(roots, encoding="ascii")
        command = [sys.executable, str(TOOL), str(root)]
        for index, (proof, snapshot, log) in enumerate(races):
            proof_path = directory / f"race-{index}.drat"
            snapshot_path = directory / f"race-{index}.tsv"
            log_path = directory / f"race-{index}.log"
            proof_path.write_bytes(proof)
            snapshot_path.write_text(snapshot, encoding="ascii")
            log_path.write_text(log, encoding="utf-8")
            command.extend(
                ["--race", str(proof_path), str(snapshot_path), str(log_path)]
            )
        command.extend(["--manifest", str(directory / "selection.json")])
        completed = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if expect_success:
            self.assertEqual(completed.returncode, 0, completed.stderr)
        else:
            self.assertNotEqual(completed.returncode, 0)
        return completed

    def test_prefers_smaller_completed_proof(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t20\t1\t0\t0.1\n"
        log = producer_log(20, 1, 0, 0)
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [(b"a\x02\0more\0", snapshot, log), (b"a\x02\0", snapshot, log)],
            )
            document = json.loads((directory / "selection.json").read_text())
            self.assertEqual(document["chosen_index"], 1)
            self.assertTrue(document["chosen_completed"])
            self.assertEqual(document["races"][1]["frontier_count"], 0)

    def test_checkpoint_prefers_smaller_frontier(self) -> None:
        two_open = HEADER + "0\t0\t0\t10\t0\t0\t2\t0.1\n"
        one_open = two_open + "0\t1\t1\t10\t20\t1\t0\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [
                    (b"a\x02\0", two_open, producer_log(0, 1, 1, 0)),
                    (b"a\x04\0", one_open, producer_log(0, 2, 1, 1)),
                ],
            )
            document = json.loads((directory / "selection.json").read_text())
            self.assertEqual(document["chosen_index"], 1)
            self.assertFalse(document["chosen_completed"])
            self.assertEqual(document["races"][0]["frontier_count"], 2)
            self.assertEqual(document["races"][1]["frontier_count"], 1)

    def test_checkpoint_accepts_unlogged_popped_frontier_depth(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t0\t0\t2\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [(b"a\x02\0", snapshot, producer_log(0, 1, 1, 1))],
            )
            race = json.loads((directory / "selection.json").read_text())[
                "races"
            ][0]
            self.assertEqual(race["producer_maximum_depth"], 1)
            self.assertEqual(race["maximum_processed_depth"], 0)
            self.assertEqual(race["maximum_frontier_depth"], 1)

    def test_checkpoint_rejects_impossible_producer_depth(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t0\t0\t2\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            self.run_tool(
                Path(raw),
                [(b"a\x02\0", snapshot, producer_log(0, 1, 1, 2))],
                expect_success=False,
            )

    def test_checkpoint_cannot_forget_a_deeper_processed_node(self) -> None:
        snapshot = (
            HEADER
            + "0\t0\t0\t10\t0\t0\t2\t0.1\n"
            + "0\t1\t1\t10\t0\t0\t3\t0.1\n"
            + "0\t2\t2\t10\t20\t1\t0\t0.1\n"
            + "0\t3\t2\t10\t20\t1\t0\t0.1\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            self.run_tool(
                Path(raw),
                [(b"a\x02\0", snapshot, producer_log(0, 4, 2, 1))],
                expect_success=False,
            )

    def test_rejects_unframed_proof(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t20\t1\t0\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            self.run_tool(
                Path(raw),
                [(b"not-framed", snapshot, producer_log(20, 1, 0, 0))],
                expect_success=False,
            )

    def test_rejects_status_frontier_disagreement(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t0\t0\t2\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            self.run_tool(
                Path(raw),
                [(b"a\x02\0", snapshot, producer_log(20, 1, 1, 0))],
                expect_success=False,
            )

    def test_replays_complete_two_root_forest(self) -> None:
        snapshot = (
            HEADER
            + "0\t0\t0\t10\t20\t1\t0\t0.1\n"
            + "1\t1\t0\t10\t20\t1\t0\t0.1\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [(b"a\x02\0", snapshot, producer_log(20, 2, 0, 0, 2))],
                roots="a 1 0\na -1 0\n",
            )
            document = json.loads((directory / "selection.json").read_text())
            self.assertEqual(document["root_count"], 2)
            self.assertEqual(
                document["races"][0]["root_frontier_counts"], [0, 0]
            )
            self.assertTrue(document["races"][0]["completed"])

    def test_replays_two_root_checkpoint(self) -> None:
        snapshot = (
            HEADER
            + "0\t0\t0\t10\t20\t1\t0\t0.1\n"
            + "1\t1\t0\t10\t0\t0\t2\t0.1\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [(b"a\x02\0", snapshot, producer_log(0, 2, 1, 0))],
                roots="a 1 0\na -1 0\n",
            )
            race = json.loads((directory / "selection.json").read_text())["races"][0]
            self.assertEqual(race["root_frontier_counts"], [0, 2])
            self.assertEqual(race["frontier_count"], 2)
            self.assertFalse(race["completed"])

    def test_accepts_global_unsat_core_before_later_root(self) -> None:
        snapshot = HEADER + "0\t0\t0\t10\t20\t0\t0\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            self.run_tool(
                directory,
                [(b"a\x02\0", snapshot, producer_log(20, 1, 0, 0, 2))],
                roots="a 1 0\na -1 0\n",
            )
            race = json.loads((directory / "selection.json").read_text())["races"][0]
            self.assertTrue(race["global_unsat"])
            self.assertEqual(race["frontier_count"], 0)
            self.assertTrue(race["completed"])

    def test_rejects_root_transition_before_prior_closure(self) -> None:
        snapshot = HEADER + "1\t0\t0\t10\t20\t1\t0\t0.1\n"
        with tempfile.TemporaryDirectory() as raw:
            self.run_tool(
                Path(raw),
                [(b"a\x02\0", snapshot, producer_log(0, 1, 0, 0))],
                expect_success=False,
                roots="a 1 0\na -1 0\n",
            )


if __name__ == "__main__":
    unittest.main()
