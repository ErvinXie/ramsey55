import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "prepare_cadical_dfs_checkpoint_recovery.py"
SPEC = importlib.util.spec_from_file_location(
    "prepare_cadical_dfs_checkpoint_recovery", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareCadicalDfsCheckpointRecoveryTests(unittest.TestCase):
    def populate(self, root: Path) -> dict[str, Path]:
        source = root / "source.icnf"
        snapshot = root / "snapshot.tsv"
        proof = root / "prefix.drat"
        log = root / "producer.log"
        time_log = root / "producer.time"
        source.write_text("a 1 0\n", encoding="ascii")
        snapshot.write_text(
            MODULE.HEADER + "\n0\t0\t0\t10\t0\t0\t2\t0.1\n",
            encoding="ascii",
        )
        proof.write_bytes(b"a\0")
        rows = {
            "conflicts": "10",
            "maximum_conflicts": "20",
            "maximum_lookahead_seconds": "1",
            "maximum_primary_split_variable": "0",
            "maximum_solve_seconds": "2",
            "maximum_wall_seconds": "3",
            "freeze_policy": "selective",
            "cadical_seed": "7",
            "cadical_phase": "1",
            "proof_fragment": "1",
            "root_index": "all",
            "initial_frozen_variables": "1",
            "checkpoint": "1",
            "status": "0",
            "attempts": "1",
            "splits": "1",
            "maximum_extra_depth": "0",
        }
        log.write_text(
            "".join(f"{key}\t{value}\n" for key, value in rows.items()),
            encoding="ascii",
        )
        time_log.write_text("Exit status: 0\n", encoding="utf-8")
        return {
            "source_root": source,
            "snapshot": snapshot,
            "proof_prefix": proof,
            "producer_log": log,
            "producer_time_log": time_log,
            "output_prefix": root / "recovery",
        }

    def test_prepares_exact_replayed_split(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            document = MODULE.prepare(**paths)
            self.assertTrue(document["verified"])
            self.assertEqual(document["summary"]["frontier_roots"], 2)
            prefix = paths["output_prefix"]
            self.assertEqual(
                prefix.with_suffix(".frontier.icnf").read_text(encoding="ascii"),
                "a 1 2 0\na 1 -2 0\n",
            )
            self.assertTrue(
                prefix.with_name("recovery-root000.icnf").is_file()
            )
            self.assertTrue(
                prefix.with_name("recovery-root001.icnf").is_file()
            )

    def test_refuses_to_overwrite_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            MODULE.prepare(**paths)
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                MODULE.prepare(**paths)

    def test_rejects_completed_producer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            log = paths["producer_log"]
            log.write_text(
                log.read_text(encoding="ascii").replace("status\t0", "status\t20"),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "clean incomplete checkpoint"):
                MODULE.prepare(**paths)

    def test_rejects_unframed_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["proof_prefix"].write_bytes(b"partial")
            with self.assertRaisesRegex(ValueError, "DRAT boundary"):
                MODULE.prepare(**paths)

    def test_rejects_wrong_replay_count(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            log = paths["producer_log"]
            log.write_text(
                log.read_text(encoding="ascii").replace("attempts\t1", "attempts\t2"),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "attempt count mismatch"):
                MODULE.prepare(**paths)


if __name__ == "__main__":
    unittest.main()
