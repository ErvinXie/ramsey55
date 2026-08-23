from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "tools/frame_binary_drat_prefix.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrameBinaryDratPrefixTests(unittest.TestCase):
    def fixture(self, root: Path) -> list[str]:
        source = root / "raw.drat"
        replay = root / "replay.json"
        source.write_bytes(b"a\x02\0d\x04\0a\x06")
        replay.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
                    "proof_prefix": str(source),
                    "proof_prefix_sha256": sha256(source),
                    "output_count": 3,
                }
            ),
            encoding="utf-8",
        )
        return [
            sys.executable,
            str(TOOL),
            str(source),
            str(replay),
            str(root / "framed.drat"),
            str(root / "framed-replay.json"),
            "--manifest",
            str(root / "framing.json"),
        ]

    def test_frames_prefix_and_hash_binds_derived_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(self.fixture(root), check=True, stdout=subprocess.PIPE)
            framed = root / "framed.drat"
            self.assertEqual(framed.read_bytes(), b"a\x02\0d\x04\0")
            replay = json.loads((root / "framed-replay.json").read_text())
            self.assertEqual(replay["proof_prefix_sha256"], sha256(framed))
            self.assertEqual(replay["proof_prefix_truncated_bytes"], 2)
            manifest = json.loads((root / "framing.json").read_text())
            self.assertEqual(manifest["truncated_tail"]["size"], 2)
            self.assertTrue(manifest["framed_prefix"]["ends_at_clause_boundary"])

    def test_rejects_replay_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            replay = root / "replay.json"
            document = json.loads(replay.read_text())
            document["proof_prefix_sha256"] = "0" * 64
            replay.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("does not match replay manifest", completed.stderr)
            self.assertFalse((root / "framed.drat").exists())


if __name__ == "__main__":
    unittest.main()
