from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "tools/finalize_cadical_dfs_checkpoint.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FinalizeCadicalDfsCheckpointTests(unittest.TestCase):
    def fixture(self, root: Path, embedded_empty: bool = False) -> list[str]:
        cnf = root / "root.cnf"
        replay = root / "replay.json"
        prefix = root / "prefix.drat"
        child = root / "child.drat"
        producer_log = root / "child.log"
        checker = root / "checker.py"
        cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
        prefix.write_bytes(b"a\0" if embedded_empty else b"a\x02\0")
        child.write_bytes(b"a\x04\0")
        producer_log.write_text(
            "proof_fragment\t1\n"
            "root_index\tall\n"
            "status\t20\n"
            "cubes\t1\n"
            "attempts\t1\n"
            "splits\t0\n"
            "maximum_extra_depth\t0\n",
            encoding="ascii",
        )
        replay.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.cadical-dfs-prefix-replay.v1",
                    "proof_prefix_sha256": sha256(prefix),
                    "output_count": 1,
                }
            ),
            encoding="utf-8",
        )
        checker.write_text(
            "#!/usr/bin/env python3\nprint('s VERIFIED')\n", encoding="utf-8"
        )
        checker.chmod(0o755)
        return [
            sys.executable,
            str(TOOL),
            str(cnf),
            str(replay),
            str(prefix),
            str(root / "fragment.drat"),
            str(root / "standalone.drat"),
            str(root / "checker.log"),
            "--child",
            str(child),
            str(producer_log),
            "--checker",
            str(checker),
            "--manifest",
            str(root / "manifest.json"),
        ]

    def test_composes_checks_and_hash_binds_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(self.fixture(root), check=True, stdout=subprocess.PIPE)
            fragment = root / "fragment.drat"
            standalone = root / "standalone.drat"
            self.assertEqual(fragment.read_bytes(), b"a\x02\0a\x04\0")
            self.assertEqual(standalone.read_bytes(), fragment.read_bytes() + b"a\0")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertTrue(manifest["checker_verified"])
            self.assertFalse(
                manifest["output_fragment"]["contains_empty_addition"]
            )
            self.assertEqual(len(manifest["children"]), 1)

    def test_rejects_embedded_empty_clause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = subprocess.run(
                self.fixture(root, embedded_empty=True),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("embedded empty clause", completed.stderr)
            self.assertFalse((root / "fragment.drat").exists())

    def test_rejects_incomplete_producer_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            (root / "child.log").write_text(
                "proof_fragment\t1\nstatus\t0\n", encoding="ascii"
            )
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("lacks root_index=all", completed.stderr)


if __name__ == "__main__":
    unittest.main()
