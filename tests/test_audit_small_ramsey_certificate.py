from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
AUDITOR = ROOT / "tools/audit_small_ramsey_certificate.py"
MANIFEST = ROOT / "data/certificates/r34-n9/manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditSmallRamseyCertificateTests(unittest.TestCase):
    def audit(self, manifest: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(AUDITOR),
                str(manifest),
                "--root",
                str(ROOT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_audits_retained_r34_certificate(self) -> None:
        completed = self.audit(MANIFEST)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["verified"])
        self.assertEqual(
            report["proof_sha256"],
            "6410b4135b83c8040024d32688b453954447f71ef7fb704d5f235041394ae2c6",
        )

    def test_rejects_proof_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = json.loads(MANIFEST.read_text())
            proof = root / "proof.drat"
            proof.write_bytes((ROOT / document["proof"]["path"]).read_bytes() + b"a\0")
            document["proof"]["path"] = str(proof)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(document), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("proof size mismatch", completed.stderr)

    def test_rejects_rehashed_checker_log_without_verified_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = json.loads(MANIFEST.read_text())
            checker_log = root / "checker.log"
            checker_log.write_text("s NOT VERIFIED\n", encoding="utf-8")
            document["checker"]["log"].update(
                {
                    "path": str(checker_log),
                    "sha256": sha256(checker_log),
                    "size": checker_log.stat().st_size,
                }
            )
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(document), encoding="utf-8")
            completed = self.audit(manifest)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("lacks an exact s VERIFIED", completed.stderr)


if __name__ == "__main__":
    unittest.main()
