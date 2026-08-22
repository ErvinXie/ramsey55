from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "replay_cadical_dfs_prefix", ROOT / "tools" / "replay_cadical_dfs_prefix.py"
)
assert SPEC is not None and SPEC.loader is not None
REPLAY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPLAY
SPEC.loader.exec_module(REPLAY)


class ReplayCadicalDfsPrefixTests(unittest.TestCase):
    def test_replays_lifo_frontier_and_binds_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "root.icnf"
            snapshot = root / "snapshot.tsv"
            proof = root / "prefix.drat"
            output = root / "open.icnf"
            manifest = root / "replay.json"
            source.write_text("a 1 -2 0\n", encoding="ascii")
            snapshot.write_text(
                REPLAY.HEADER
                + "\n"
                + "0\t0\t0\t500000\t0\t0\t3\t1.0\n"
                + "0\t1\t1\t500000\t20\t2\t0\t0.5\n"
                + "0\t2\t1\t500000\t0\t0\t4\t2.0\n",
                encoding="ascii",
            )
            proof.write_bytes(b"a\x02\0")
            old_argv = sys.argv
            try:
                sys.argv = [
                    "replay_cadical_dfs_prefix.py",
                    str(source),
                    str(snapshot),
                    str(output),
                    "--manifest",
                    str(manifest),
                    "--proof-prefix",
                    str(proof),
                ]
                REPLAY.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(output.read_text(), "a 1 -2 -3 4 0\na 1 -2 -3 -4 0\n")
            document = json.loads(manifest.read_text())
            self.assertEqual(document["schema"], REPLAY.SCHEMA)
            self.assertEqual(document["snapshot_rows"], 3)
            self.assertEqual(document["maximum_processed_depth"], 1)
            self.assertEqual(document["output_count"], 2)
            self.assertEqual(document["proof_prefix_sha256"], REPLAY.file_sha256(proof))

    def test_detects_unframed_binary_drat_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            proof = Path(raw) / "prefix.drat"
            proof.write_bytes(b"a\x02\0a\x04")
            self.assertFalse(REPLAY.binary_drat_is_framed(proof))
            proof.write_bytes(b"a\x02\0a\x04\0")
            self.assertTrue(REPLAY.binary_drat_is_framed(proof))

    def test_rejects_depth_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            snapshot = Path(raw) / "snapshot.tsv"
            snapshot.write_text(
                REPLAY.HEADER + "\n0\t0\t1\t500000\t20\t1\t0\t0.1\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "depth mismatch"):
                REPLAY.replay_prefix((1,), snapshot)

    def test_rejects_sat_row(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            snapshot = Path(raw) / "snapshot.tsv"
            snapshot.write_text(
                REPLAY.HEADER + "\n0\t0\t0\t500000\t10\t0\t0\t0.1\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "SAT row"):
                REPLAY.replay_prefix((1,), snapshot)


if __name__ == "__main__":
    unittest.main()
