from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "tools" / "enumerate_minimal_flip_models.py"
SPEC = importlib.util.spec_from_file_location("enumerate_minimal_flip_models", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FlipEnumerationCheckpointTests(unittest.TestCase):
    def test_deterministic_checkpoint_round_trip(self) -> None:
        models = [(1, 2, 7, 860), (3, 4, 5, 6)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rep012.json.gz"
            MODULE.write_checkpoint(path, 12, 4, "Zgraph6", models)
            first = path.read_bytes()
            self.assertEqual(
                MODULE.read_checkpoint(path, 12, 4, "Zgraph6"), models
            )
            MODULE.write_checkpoint(path, 12, 4, "Zgraph6", models)
            self.assertEqual(path.read_bytes(), first)

    def test_rejects_stale_and_duplicate_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rep000.json.gz"
            MODULE.write_checkpoint(path, 0, 4, "Zgraph6", [(1, 2, 3, 4)])
            with self.assertRaisesRegex(ValueError, "graph6"):
                MODULE.read_checkpoint(path, 0, 4, "different")

            payload = {
                "version": MODULE.CHECKPOINT_VERSION,
                "representative": 0,
                "flips": 4,
                "graph6": "Zgraph6",
                "model_count": 2,
                "models": [[1, 2, 3, 4], [1, 2, 3, 4]],
            }
            with gzip.open(path, "wt", encoding="ascii") as output:
                json.dump(payload, output)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                MODULE.read_checkpoint(path, 0, 4, "Zgraph6")


if __name__ == "__main__":
    unittest.main()
