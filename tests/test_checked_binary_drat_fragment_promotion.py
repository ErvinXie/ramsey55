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
COMPOSER = ROOT / "tools/compose_binary_drat_protect_cnf.py"
SOURCE_AUDITOR = ROOT / "tools/audit_binary_drat_protect_cnf.py"
PROMOTER = ROOT / "tools/promote_checked_binary_drat_fragment.py"
AUDITOR = ROOT / "tools/audit_checked_binary_drat_fragment_promotion.py"
FINALIZER = ROOT / "tools/finalize_cadical_dfs_checkpoint.py"
CHECKPOINT_AUDITOR = ROOT / "tools/audit_cadical_dfs_checkpoint_finalization.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CheckedBinaryDratFragmentPromotionTests(unittest.TestCase):
    def source_evidence(self, root: Path) -> tuple[Path, Path, Path]:
        cnf = root / "input.cnf"
        source = root / "source.drat"
        standalone = root / "standalone.drat"
        composition = root / "composition.json"
        checker = root / "checker.py"
        checker_log = root / "checker.log"
        audit = root / "composition-audit.json"
        cnf.write_text("p cnf 2 2\n1 0\n-1 0\n", encoding="ascii")
        # The original-clause deletion is omitted; the learned addition remains.
        source.write_bytes(b"d\x02\0a\x04\0")
        subprocess.run(
            [
                sys.executable,
                str(COMPOSER),
                str(cnf),
                str(standalone),
                str(source),
                "--append-empty",
                "--manifest",
                str(composition),
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        checker.write_text(
            "#!/usr/bin/env python3\nprint('s VERIFIED')\n", encoding="utf-8"
        )
        checker.chmod(0o755)
        checker_log.write_text("s VERIFIED\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SOURCE_AUDITOR),
                str(composition),
                "--root",
                str(root),
                "--checker-log",
                str(checker_log),
                "--checker",
                str(checker),
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        audit.write_text(completed.stdout, encoding="utf-8")
        return composition, audit, standalone

    def promote(self, root: Path) -> Path:
        composition, audit, _ = self.source_evidence(root)
        manifest = root / "promotion.json"
        subprocess.run(
            [
                sys.executable,
                str(PROMOTER),
                str(composition),
                str(audit),
                str(root / "fragment.drat"),
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        return manifest

    def audit(self, manifest: Path, *options: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(AUDITOR),
                str(manifest),
                "--root",
                str(manifest.parent),
                *options,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_promotes_exact_prefix_and_independently_audits_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.promote(root)
            document = json.loads(manifest.read_text())
            fragment = Path(document["output_fragment"]["path"])
            standalone = Path(document["standalone_proof"]["path"])
            self.assertEqual(fragment.read_bytes() + b"a\0", standalone.read_bytes())
            self.assertFalse(document["output_fragment"]["contains_empty_addition"])
            completed = self.audit(
                manifest,
                "--rerun-source-audit",
                "--source-auditor",
                str(SOURCE_AUDITOR),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["verified"])
            self.assertTrue(report["source_audit_rerun"]["verified"])

    def test_auditor_runs_without_the_promotion_producer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.promote(root)
            isolated = root / "isolated-auditor.py"
            shutil.copyfile(AUDITOR, isolated)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(isolated),
                    str(manifest),
                    "--root",
                    str(root),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["verified"])

    def test_rejects_rehashed_fragment_that_is_not_standalone_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.promote(root)
            document = json.loads(manifest.read_text())
            fragment = Path(document["output_fragment"]["path"])
            fragment.write_bytes(b"a\x06\0")
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
            manifest.write_text(json.dumps(document), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("not fragment plus one empty addition", completed.stderr)

    def test_rejects_unverified_source_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composition, audit, _ = self.source_evidence(root)
            report = json.loads(audit.read_text())
            report["checker_verified"] = False
            audit.write_text(json.dumps(report), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROMOTER),
                    str(composition),
                    str(audit),
                    str(root / "fragment.drat"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(root / "promotion.json"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("checker_verified=true", completed.stderr)

    def test_checkpoint_finalization_recursively_audits_promoted_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            promotion = self.promote(root)
            promoted = json.loads(promotion.read_text())
            prefix = root / "upper-prefix.drat"
            replay = root / "upper-replay.json"
            prefix.write_bytes(b"")
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
            upper = root / "upper-finalization.json"
            subprocess.run(
                [
                    sys.executable,
                    str(FINALIZER),
                    promoted["cnf"]["path"],
                    str(replay),
                    str(prefix),
                    str(root / "upper-fragment.drat"),
                    str(root / "upper-standalone.drat"),
                    str(root / "upper-checker.log"),
                    "--child",
                    promoted["output_fragment"]["path"],
                    str(promotion),
                    "--checker",
                    promoted["checker"]["path"],
                    "--manifest",
                    str(upper),
                ],
                check=True,
                stdout=subprocess.PIPE,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CHECKPOINT_AUDITOR),
                    str(upper),
                    "--root",
                    str(root),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(completed.stdout)["recursively_audited_children"], 1
            )


if __name__ == "__main__":
    unittest.main()
