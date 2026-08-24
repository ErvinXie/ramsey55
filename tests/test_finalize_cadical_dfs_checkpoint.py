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
SELECTOR = ROOT / "tools/select_cadical_dfs_race.py"
REAL_CHECKER = ROOT / ".tools/src/drat-trim/drat-trim"


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
                    "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
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

    def forest_fixture(self, root: Path) -> list[str]:
        cnf = root / "root.cnf"
        source = root / "source.icnf"
        prefix_snapshot = root / "prefix.tsv"
        frontier = root / "frontier.icnf"
        replay = root / "replay.json"
        prefix = root / "prefix.drat"
        proof = root / "forest.drat"
        snapshot = root / "forest.tsv"
        producer_log = root / "forest.log"
        selection = root / "selection.json"
        checker = root / "checker.py"
        cnf.write_text("p cnf 2 1\n1 0\n", encoding="ascii")
        source.write_text("a 1 0\n", encoding="ascii")
        prefix_snapshot.write_text(
            "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
            "0\t0\t0\t100\t0\t0\t2\t0.125\n",
            encoding="ascii",
        )
        frontier.write_text("a 1 2 0\na 1 -2 0\n", encoding="ascii")
        prefix.write_bytes(b"a\x02\0")
        replay.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
                    "source_root": str(source),
                    "source_root_sha256": sha256(source),
                    "snapshot": str(prefix_snapshot),
                    "snapshot_sha256": sha256(prefix_snapshot),
                    "snapshot_rows": 1,
                    "processed_attempts": 1,
                    "processed_splits": 1,
                    "maximum_processed_depth": 0,
                    "source_root_count": 1,
                    "root_frontier_counts": [2],
                    "output": str(frontier),
                    "output_sha256": sha256(frontier),
                    "output_count": 2,
                    "proof_prefix": str(prefix),
                    "proof_prefix_sha256": sha256(prefix),
                }
            ),
            encoding="utf-8",
        )
        proof.write_bytes(b"a\x04\0")
        snapshot.write_text(
            "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
            "0\t0\t0\t100\t20\t1\t0\t0.250\n"
            "1\t1\t0\t100\t20\t1\t0\t0.375\n",
            encoding="ascii",
        )
        producer_log.write_text(
            "proof_fragment\t1\n"
            "root_index\tall\n"
            "status\t20\n"
            "cubes\t2\n"
            "attempts\t2\n"
            "splits\t0\n"
            "maximum_extra_depth\t0\n",
            encoding="ascii",
        )
        subprocess.run(
            [
                sys.executable,
                str(SELECTOR),
                str(frontier),
                "--race",
                str(proof),
                str(snapshot),
                str(producer_log),
                "--manifest",
                str(selection),
            ],
            check=True,
            stdout=subprocess.PIPE,
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
            "--forest-continuation",
            str(proof),
            str(selection),
            "--checker",
            str(checker),
            "--manifest",
            str(root / "manifest.json"),
        ]

    def finalized_child_manifest(
        self, root: Path, proof: Path, checker_verified: bool = True
    ) -> Path:
        placeholder = {
            "path": "recorded-elsewhere",
            "sha256": "0" * 64,
            "size": 0,
        }
        path = root / "child-finalization.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.cadical-dfs-checkpoint-finalization.v1",
                    "cnf": placeholder,
                    "replay_manifest": placeholder,
                    "prefix": placeholder,
                    "children": [{"index": 0}],
                    "output_fragment": {
                        "path": str(proof),
                        "sha256": sha256(proof),
                        "size": proof.stat().st_size,
                        "contains_empty_addition": False,
                    },
                    "standalone_proof": {
                        **placeholder,
                        "appended_empty_clause": True,
                    },
                    "checker": placeholder,
                    "checker_log": placeholder,
                    "checker_verified": checker_verified,
                }
            ),
            encoding="utf-8",
        )
        return path

    def promoted_child_manifest(self, root: Path, proof: Path) -> Path:
        placeholder = {
            "path": "recorded-elsewhere",
            "sha256": "0" * 64,
            "size": 0,
        }
        path = root / "child-promotion.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.checked-binary-drat-fragment-promotion.v1",
                    "source_composition_manifest": placeholder,
                    "source_composition_audit": placeholder,
                    "cnf": placeholder,
                    "output_fragment": {
                        "path": str(proof),
                        "sha256": sha256(proof),
                        "size": proof.stat().st_size,
                        "contains_empty_addition": False,
                    },
                    "standalone_proof": {
                        **placeholder,
                        "appended_empty_clause": True,
                    },
                    "checker": placeholder,
                    "checker_log": placeholder,
                    "checker_verified": True,
                }
            ),
            encoding="utf-8",
        )
        return path

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
            self.assertFalse(manifest["output_fragment"]["contains_empty_addition"])
            self.assertEqual(len(manifest["children"]), 1)

    def test_accepts_one_completed_stream_for_the_whole_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                self.forest_fixture(root), check=True, stdout=subprocess.PIPE
            )
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["composition"]["frontier_cover"], "forest")
            self.assertEqual(manifest["children"][0]["frontier_count"], 2)
            self.assertTrue(
                manifest["children"][0]["race_selection_manifest"]["chosen_completed"]
            )
            self.assertEqual((root / "fragment.drat").read_bytes(), b"a\x02\0a\x04\0")

    def test_rejects_incomplete_forest_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.forest_fixture(root)
            selection = root / "selection.json"
            document = json.loads(selection.read_text())
            document["chosen_completed"] = False
            selection.write_text(json.dumps(document), encoding="utf-8")
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forest continuation is not complete", completed.stderr)

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

    def test_accepts_checker_verified_finalized_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            proof = root / "child.drat"
            finalized = self.finalized_child_manifest(root, proof)
            command[command.index(str(root / "child.log"))] = str(finalized)
            subprocess.run(command, check=True, stdout=subprocess.PIPE)
            manifest = json.loads((root / "manifest.json").read_text())
            child = manifest["children"][0]
            self.assertNotIn("producer_log", child)
            self.assertTrue(child["finalization_manifest"]["checker_verified"])
            self.assertEqual(
                child["proof"]["sha256"],
                child["finalization_manifest"]["output_fragment_sha256"],
            )

    def test_accepts_checker_verified_promoted_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            proof = root / "child.drat"
            promoted = self.promoted_child_manifest(root, proof)
            command[command.index(str(root / "child.log"))] = str(promoted)
            subprocess.run(command, check=True, stdout=subprocess.PIPE)
            manifest = json.loads((root / "manifest.json").read_text())
            evidence = manifest["children"][0]["finalization_manifest"]
            self.assertEqual(
                evidence["schema"],
                "ramsey55.checked-binary-drat-fragment-promotion.v1",
            )
            self.assertEqual(evidence["output_fragment_sha256"], sha256(proof))

    def test_rejects_finalized_child_with_mismatched_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            proof = root / "child.drat"
            finalized = self.finalized_child_manifest(root, proof)
            proof.write_bytes(b"a\x06\0")
            command[command.index(str(root / "child.log"))] = str(finalized)
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("does not match finalization manifest", completed.stderr)

    def test_rejects_unverified_finalized_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            proof = root / "child.drat"
            finalized = self.finalized_child_manifest(
                root, proof, checker_verified=False
            )
            command[command.index(str(root / "child.log"))] = str(finalized)
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("is not checker-verified", completed.stderr)

    def test_records_checker_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            command.append("--checker-option=-p")
            subprocess.run(command, check=True, stdout=subprocess.PIPE)
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["checker_options"], ["-p"])

    def test_can_emit_addition_only_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = self.fixture(root)
            (root / "prefix.drat").write_bytes(b"d\x02\0a\x02\0")
            (root / "child.drat").write_bytes(b"d\x04\0a\x04\0")
            replay = json.loads((root / "replay.json").read_text())
            replay["proof_prefix_sha256"] = sha256(root / "prefix.drat")
            (root / "replay.json").write_text(json.dumps(replay), encoding="utf-8")
            command.append("--drop-deletions")
            subprocess.run(command, check=True, stdout=subprocess.PIPE)
            fragment = root / "fragment.drat"
            standalone = root / "standalone.drat"
            self.assertEqual(fragment.read_bytes(), b"a\x02\0a\x04\0")
            self.assertEqual(standalone.read_bytes(), fragment.read_bytes() + b"a\0")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertTrue(manifest["composition"]["drop_deletions"])
            self.assertEqual(manifest["output_fragment"]["binary_drat"]["deletions"], 0)
            self.assertEqual(
                manifest["standalone_proof"]["binary_drat"]["empty_additions"],
                1,
            )

    @unittest.skipUnless(REAL_CHECKER.is_file(), "drat-trim is not built")
    def test_real_checker_accepts_deletion_free_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "root.cnf"
            replay = root / "replay.json"
            prefix = root / "prefix.drat"
            child = root / "child.drat"
            child_log = root / "child.log"
            cnf.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="ascii")
            # Deleting input clause (1) would make the final empty addition
            # invalid.  The normalized composition must physically omit it.
            prefix.write_bytes(b"d\x02\0")
            child.write_bytes(b"")
            child_log.write_text(
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
            subprocess.run(
                [
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
                    str(child_log),
                    "--checker",
                    str(REAL_CHECKER),
                    "--drop-deletions",
                    "--manifest",
                    str(root / "manifest.json"),
                ],
                check=True,
                stdout=subprocess.PIPE,
            )
            self.assertEqual((root / "fragment.drat").read_bytes(), b"")
            self.assertEqual((root / "standalone.drat").read_bytes(), b"a\0")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertTrue(manifest["checker_verified"])
            self.assertTrue(manifest["composition"]["drop_deletions"])
            self.assertEqual(manifest["checker_options"], [])

    @unittest.skipUnless(REAL_CHECKER.is_file(), "drat-trim is not built")
    def test_real_checker_accepts_recursive_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "root.cnf"
            cnf.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="ascii")

            lower_prefix = root / "lower-prefix.drat"
            lower_child = root / "lower-child.drat"
            lower_log = root / "lower-child.log"
            lower_replay = root / "lower-replay.json"
            lower_prefix.write_bytes(b"")
            lower_child.write_bytes(b"")
            lower_log.write_text(
                "proof_fragment\t1\n"
                "root_index\tall\n"
                "status\t20\n"
                "cubes\t1\n"
                "attempts\t1\n"
                "splits\t0\n"
                "maximum_extra_depth\t0\n",
                encoding="ascii",
            )
            lower_replay.write_text(
                json.dumps(
                    {
                        "schema": "ramsey55.cadical-dfs-prefix-replay.v1",
                        "proof_prefix_sha256": sha256(lower_prefix),
                        "output_count": 1,
                    }
                ),
                encoding="utf-8",
            )
            lower_fragment = root / "lower-fragment.drat"
            lower_manifest = root / "lower-finalization.json"
            subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(lower_replay),
                    str(lower_prefix),
                    str(lower_fragment),
                    str(root / "lower-standalone.drat"),
                    str(root / "lower-checker.log"),
                    "--child",
                    str(lower_child),
                    str(lower_log),
                    "--checker",
                    str(REAL_CHECKER),
                    "--manifest",
                    str(lower_manifest),
                ],
                check=True,
                stdout=subprocess.PIPE,
            )

            upper_prefix = root / "upper-prefix.drat"
            upper_replay = root / "upper-replay.json"
            upper_prefix.write_bytes(b"")
            upper_replay.write_text(
                json.dumps(
                    {
                        "schema": "ramsey55.cadical-dfs-prefix-replay.v1",
                        "proof_prefix_sha256": sha256(upper_prefix),
                        "output_count": 1,
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(upper_replay),
                    str(upper_prefix),
                    str(root / "upper-fragment.drat"),
                    str(root / "upper-standalone.drat"),
                    str(root / "upper-checker.log"),
                    "--child",
                    str(lower_fragment),
                    str(lower_manifest),
                    "--checker",
                    str(REAL_CHECKER),
                    "--manifest",
                    str(root / "upper-finalization.json"),
                ],
                check=True,
                stdout=subprocess.PIPE,
            )
            self.assertIn("s VERIFIED", (root / "lower-checker.log").read_text())
            self.assertIn("s VERIFIED", (root / "upper-checker.log").read_text())


if __name__ == "__main__":
    unittest.main()
