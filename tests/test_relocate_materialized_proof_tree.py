from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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

    def test_updates_repo_relative_hash_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            project = temporary / "project"
            old = "/dev/shm/example-proof-tree"
            new = project / "build" / "stable"
            halted = new / "chain" / "halted.json"
            write_json(halted, {"current_manifest": old + "/candidate.json"})
            state = new / "chain" / "state.json"
            write_json(
                state,
                {
                    "adopted_growth": {
                        "halt_path": str(halted.relative_to(project)),
                        "halt_sha256": sha256(halted),
                    }
                },
            )

            previous = Path.cwd()
            os.chdir(project)
            try:
                RELOCATE.relocate_tree(old, new)
            finally:
                os.chdir(previous)

            document = json.loads(state.read_text())
            self.assertEqual(
                document["adopted_growth"]["halt_sha256"], sha256(halted)
            )

    def test_preserves_previous_relocation_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            old = "/dev/shm/example-proof-tree"
            new = temporary / "stable"
            previous = new / "relocation-v1.json"
            write_json(
                previous,
                {
                    "schema": RELOCATE.SCHEMA,
                    "old_root": old,
                    "new_root": str(new),
                },
            )
            manifest = new / "manifest.json"
            write_json(manifest, {"path": old + "/artifact"})
            record = previous.read_bytes()

            result = RELOCATE.relocate_tree(old, new)

            self.assertEqual(previous.read_bytes(), record)
            self.assertEqual(result["json_documents"], 1)
            self.assertEqual(
                json.loads(manifest.read_text())["path"],
                str((new / "artifact").resolve()),
            )


if __name__ == "__main__":
    unittest.main()
