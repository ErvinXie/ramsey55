from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "split_icnf_roots", ROOT / "tools" / "split_icnf_roots.py"
)
assert SPEC is not None and SPEC.loader is not None
SPLIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SPLIT
SPEC.loader.exec_module(SPLIT)


class SplitIcnfRootsTests(unittest.TestCase):
    def run_tool(self, frontier: Path, prefix: Path, manifest: Path) -> None:
        old_argv = sys.argv
        try:
            sys.argv = [
                "split_icnf_roots.py",
                str(frontier),
                str(prefix),
                "--manifest",
                str(manifest),
            ]
            SPLIT.main()
        finally:
            sys.argv = old_argv

    def test_splits_and_hash_binds_normalized_roots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            frontier = directory / "frontier.icnf"
            prefix = directory / "leaf"
            manifest = directory / "split.json"
            frontier.write_text("c roots\na 1 -2 0\n1 3 -4 0\n", encoding="ascii")

            self.run_tool(frontier, prefix, manifest)

            first = directory / "leaf-root000.icnf"
            second = directory / "leaf-root001.icnf"
            self.assertEqual(first.read_text(), "a 1 -2 0\n")
            self.assertEqual(second.read_text(), "a 3 -4 0\n")
            document = json.loads(manifest.read_text())
            self.assertEqual(document["schema"], SPLIT.SCHEMA)
            self.assertEqual(document["source_frontier"]["count"], 2)
            self.assertEqual(document["outputs"][0]["sha256"], SPLIT.file_sha256(first))
            self.assertEqual(document["outputs"][1]["sha256"], SPLIT.file_sha256(second))

    def test_refuses_to_overwrite_any_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            frontier = directory / "frontier.icnf"
            prefix = directory / "leaf"
            manifest = directory / "split.json"
            frontier.write_text("a 1 0\n", encoding="ascii")
            (directory / "leaf-root000.icnf").write_text("sentinel\n")

            with self.assertRaises(SystemExit):
                self.run_tool(frontier, prefix, manifest)

            self.assertFalse(manifest.exists())
            self.assertEqual(
                (directory / "leaf-root000.icnf").read_text(), "sentinel\n"
            )


if __name__ == "__main__":
    unittest.main()
