from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
FINALIZER = ROOT / "tools/finalize_cadical_dfs_checkpoint.py"
AUDITOR = ROOT / "tools/audit_cadical_dfs_checkpoint_finalization.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditCadicalDfsCheckpointFinalizationTests(unittest.TestCase):
    def finalize(
        self,
        root: Path,
        stem: str,
        *,
        child_proof: Path | None = None,
        child_evidence: Path | None = None,
        drop_deletions: bool = True,
        replay_v2: bool = False,
    ) -> Path:
        cnf = root / f"{stem}.cnf"
        replay = root / f"{stem}-replay.json"
        prefix = root / f"{stem}-prefix.drat"
        child = child_proof or root / f"{stem}-child.drat"
        evidence = child_evidence or root / f"{stem}-child.log"
        checker = root / "checker.py"
        cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
        prefix.write_bytes(b"d\x02\0a\x02\0")
        if child_proof is None:
            child.write_bytes(b"d\x04\0a\x04\0")
        if child_evidence is None:
            evidence.write_text(
                "proof_fragment\t1\n"
                "root_index\tall\n"
                "status\t20\n"
                "cubes\t1\n"
                "attempts\t1\n"
                "splits\t0\n"
                "maximum_extra_depth\t0\n",
                encoding="ascii",
            )
        replay_document: dict[str, object]
        if replay_v2:
            source_root = root / f"{stem}-root.icnf"
            snapshot = root / f"{stem}-snapshot.tsv"
            output = root / f"{stem}-frontier.icnf"
            source_root.write_text("a 1 0\n", encoding="ascii")
            snapshot.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t100\t0\t0\t2\t0.125\n"
                "0\t1\t1\t100\t20\t1\t0\t0.250\n",
                encoding="ascii",
            )
            output.write_text("a 1 -2 0\n", encoding="ascii")
            replay_document = {
                "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
                "source_root": str(source_root),
                "source_root_sha256": sha256(source_root),
                "snapshot": str(snapshot),
                "snapshot_sha256": sha256(snapshot),
                "snapshot_rows": 2,
                "processed_attempts": 2,
                "processed_splits": 1,
                "maximum_processed_depth": 1,
                "source_root_count": 1,
                "root_frontier_counts": [1],
                "output": str(output),
                "output_sha256": sha256(output),
                "output_count": 1,
                "proof_prefix": str(prefix),
                "proof_prefix_sha256": sha256(prefix),
            }
        else:
            replay_document = {
                "schema": "ramsey55.cadical-dfs-prefix-replay.v1",
                "proof_prefix_sha256": sha256(prefix),
                "output_count": 1,
            }
        replay.write_text(json.dumps(replay_document), encoding="utf-8")
        checker.write_text(
            "#!/usr/bin/env python3\nprint('s VERIFIED')\n", encoding="utf-8"
        )
        checker.chmod(0o755)
        manifest = root / f"{stem}-finalization.json"
        command = [
            sys.executable,
            str(FINALIZER),
            str(cnf),
            str(replay),
            str(prefix),
            str(root / f"{stem}-fragment.drat"),
            str(root / f"{stem}-standalone.drat"),
            str(root / f"{stem}-checker.log"),
            "--child",
            str(child),
            str(evidence),
            "--checker",
            str(checker),
        ]
        if drop_deletions:
            command.append("--drop-deletions")
        command.extend(["--manifest", str(manifest)])
        subprocess.run(command, check=True, stdout=subprocess.PIPE)
        return manifest

    def audit(self, manifest: Path, *options: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(AUDITOR), str(manifest), *options],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_audits_exact_addition_only_composition_and_reruns_checker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf")
            completed = self.audit(manifest, "--rerun-checker")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["verified"])
            self.assertTrue(report["drop_deletions"])
            self.assertTrue(report["checker_rerun"]["verified"])

    def test_auditor_runs_without_the_production_finalizer_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf")
            isolated = root / "isolated-auditor.py"
            shutil.copyfile(AUDITOR, isolated)
            completed = subprocess.run(
                [sys.executable, "-I", str(isolated), str(manifest)],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["verified"])

    def test_independently_replays_v2_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf", replay_v2=True)
            completed = self.audit(manifest)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["replay_independently_verified"])

    def test_rejects_rehashed_false_v2_replay_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf", replay_v2=True)
            finalization = json.loads(manifest.read_text(encoding="utf-8"))
            replay = Path(finalization["replay_manifest"]["path"])
            replay_document = json.loads(replay.read_text(encoding="utf-8"))
            replay_document["processed_splits"] = 2
            replay.write_text(json.dumps(replay_document), encoding="utf-8")
            finalization["replay_manifest"]["sha256"] = sha256(replay)
            finalization["replay_manifest"]["size"] = replay.stat().st_size
            manifest.write_text(json.dumps(finalization), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("replay processed_splits mismatch", completed.stderr)

    def test_rejects_rehashed_false_v2_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf", replay_v2=True)
            finalization = json.loads(manifest.read_text(encoding="utf-8"))
            replay = Path(finalization["replay_manifest"]["path"])
            replay_document = json.loads(replay.read_text(encoding="utf-8"))
            output = Path(replay_document["output"])
            output.write_text("a 1 2 0\n", encoding="ascii")
            replay_document["output_sha256"] = sha256(output)
            replay.write_text(json.dumps(replay_document), encoding="utf-8")
            finalization["replay_manifest"]["sha256"] = sha256(replay)
            finalization["replay_manifest"]["size"] = replay.stat().st_size
            manifest.write_text(json.dumps(finalization), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "replay output is not the independently reconstructed frontier",
                completed.stderr,
            )

    def test_rejects_hash_bound_output_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf")
            document = json.loads(manifest.read_text())
            fragment = Path(document["output_fragment"]["path"])
            fragment.write_bytes(fragment.read_bytes() + b"a\x06\0")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("size mismatch", completed.stderr)

    def test_rejects_rehashed_noncomponent_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.finalize(root, "leaf")
            document = json.loads(manifest.read_text())
            fragment = Path(document["output_fragment"]["path"])
            standalone = Path(document["standalone_proof"]["path"])
            fragment.write_bytes(b"a\x06\0")
            standalone.write_bytes(fragment.read_bytes() + b"a\0")
            document["output_fragment"].update(
                {
                    "sha256": sha256(fragment),
                    "size": fragment.stat().st_size,
                    "binary_drat": {
                        "additions": 1,
                        "deletions": 0,
                        "empty_additions": 0,
                        "empty_deletions": 0,
                    },
                }
            )
            document["standalone_proof"].update(
                {
                    "sha256": sha256(standalone),
                    "size": standalone.stat().st_size,
                    "binary_drat": {
                        "additions": 2,
                        "deletions": 0,
                        "empty_additions": 1,
                        "empty_deletions": 0,
                    },
                }
            )
            manifest.write_text(json.dumps(document), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("clause counts do not match components", completed.stderr)

    def test_recursively_audits_finalized_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lower = self.finalize(root, "lower")
            lower_document = json.loads(lower.read_text())
            upper = self.finalize(
                root,
                "upper",
                child_proof=Path(lower_document["output_fragment"]["path"]),
                child_evidence=lower,
            )
            completed = self.audit(upper)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["recursively_audited_children"], 1)


if __name__ == "__main__":
    unittest.main()
