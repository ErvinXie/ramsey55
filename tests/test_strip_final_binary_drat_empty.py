from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "tools/strip_final_binary_drat_empty.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StripFinalBinaryDratEmptyTests(unittest.TestCase):
    def command(self, root: Path) -> list[str]:
        return [
            sys.executable,
            str(TOOL),
            str(root / "standalone.drat"),
            str(root / "fragment.drat"),
            "--manifest",
            str(root / "strip.json"),
        ]

    def test_strips_only_final_empty_and_hash_binds_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "standalone.drat"
            source.write_bytes(b"a\x02\0d\x04\0a\0")
            subprocess.run(self.command(root), check=True, stdout=subprocess.PIPE)

            fragment = root / "fragment.drat"
            self.assertEqual(fragment.read_bytes(), b"a\x02\0d\x04\0")
            manifest = json.loads((root / "strip.json").read_text())
            self.assertEqual(
                manifest["schema"], "ramsey55.binary-drat-final-empty-strip.v1"
            )
            self.assertEqual(manifest["output_fragment"]["sha256"], sha256(fragment))
            self.assertEqual(manifest["standalone_proof"]["binary_drat"], {
                "additions": 2,
                "deletions": 1,
                "empty_additions": 1,
                "empty_deletions": 0,
            })
            self.assertFalse(manifest["proof_credit"])

    def test_rejects_embedded_empty_addition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "standalone.drat").write_bytes(b"a\0a\x02\0a\0")
            completed = subprocess.run(
                self.command(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("exactly one empty addition", completed.stderr)
            self.assertFalse((root / "fragment.drat").exists())

    def test_rejects_empty_addition_before_final_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "standalone.drat").write_bytes(b"a\0d\x02\0")
            completed = subprocess.run(
                self.command(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("not the final record", completed.stderr)

    def test_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "standalone.drat").write_bytes(b"a\x02\0a\0")
            (root / "fragment.drat").write_bytes(b"keep")
            completed = subprocess.run(
                self.command(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((root / "fragment.drat").read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
