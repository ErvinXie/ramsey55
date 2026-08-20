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
    "relocate_materialized_proof_tree",
    ROOT / "tools" / "relocate_materialized_proof_tree.py",
)
assert SPEC is not None and SPEC.loader is not None
RELOCATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RELOCATE
SPEC.loader.exec_module(RELOCATE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class RelocateMaterializedProofTreeTests(unittest.TestCase):
    def test_rewrites_paths_and_propagates_nested_manifest_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            old = "/dev/shm/example-proof-tree"
            new = temporary / "stable"
            cubes = new / "cubes.icnf"
            cubes.parent.mkdir()
            cubes.write_text("a 1 0\n")
            child = new / "child" / "manifest.json"
            write_json(
                child,
                {
                    "cubes": {
                        "path": old + "/cubes.icnf",
                        "sha256": sha256(cubes),
                    }
                },
            )
            parent = new / "parent" / "manifest.json"
            write_json(
                parent,
                {
                    "composition": {
                        "primary_manifest": {
                            "path": old + "/child/manifest.json",
                            "sha256": sha256(child),
                        }
                    }
                },
            )
            frontier = new / "frontier.json"
            write_json(
                frontier,
                {
                    "source_manifest": old + "/parent/manifest.json",
                    "source_manifest_sha256": sha256(parent),
                },
            )

            result = RELOCATE.relocate_tree(old, new)

            child_document = json.loads(child.read_text())
            parent_document = json.loads(parent.read_text())
            frontier_document = json.loads(frontier.read_text())
            self.assertEqual(child_document["cubes"]["path"], str(cubes.resolve()))
            self.assertEqual(
                parent_document["composition"]["primary_manifest"]["sha256"],
                sha256(child),
            )
            self.assertEqual(frontier_document["source_manifest_sha256"], sha256(parent))
            self.assertGreaterEqual(result["convergence_passes"], 2)
            self.assertNotIn(old, "".join(path.read_text() for path in new.rglob("*.json")))

    def test_missing_hash_bound_file_does_not_partially_relocate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            old = "/dev/shm/example-proof-tree"
            new = temporary / "stable"
            manifest = new / "manifest.json"
            write_json(
                manifest,
                {
                    "cubes": {
                        "path": old + "/missing.icnf",
                        "sha256": "0" * 64,
                    }
                },
            )
            original = manifest.read_bytes()

            with self.assertRaisesRegex(ValueError, "does not exist"):
                RELOCATE.relocate_tree(old, new)

            self.assertEqual(manifest.read_bytes(), original)
            self.assertIn(old, manifest.read_text())


if __name__ == "__main__":
    unittest.main()
