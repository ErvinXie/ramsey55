from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_r45_gluing_branches.py"
COLLECTOR = ROOT / "tools/collect_r45_gluing_proofs.py"
AUDITOR = ROOT / "tools/audit_r45_gluing_proofs.py"
COMPACTOR = ROOT / "tools/compact_r45_gluing_proofs.py"


class R45GluingProofBundleTests(unittest.TestCase):
    def test_collect_and_independently_replay_one_formula(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            covers = root / "covers"
            covers.mkdir()
            (covers / "gen358").write_text(f"{3 ** 28} witness\n", encoding="ascii")
            (covers / "gen4416").write_text(
                f"{3 ** 120} witness\n", encoding="ascii"
            )
            branches = root / "branches"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--cover-dir",
                    str(covers),
                    "--degree",
                    "8",
                    "--pair-index",
                    "0",
                    "--output-dir",
                    str(branches),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            branch_manifest = branches / "manifest.json"
            branch_document = json.loads(branch_manifest.read_text())
            self.assertEqual(
                branch_document["schema"], "ramsey55.r45-gluing-branches.v2"
            )
            branch = branch_document["files"][0]
            stem = Path(branch["path"]).stem
            proofs = root / "proofs"
            proofs.mkdir()
            (proofs / f"{stem}.drat").write_bytes(b"synthetic proof\n")
            (proofs / f"{stem}.solver.log").write_text(
                "s UNSATISFIABLE\n", encoding="utf-8"
            )
            (proofs / f"{stem}.solver.time.log").write_text(
                "Exit status: 20\n", encoding="utf-8"
            )
            (proofs / f"{stem}.checker.log").write_text(
                "s VERIFIED\n", encoding="utf-8"
            )
            (proofs / f"{stem}.checker.time.log").write_text(
                "Exit status: 0\n", encoding="utf-8"
            )
            fake = root / "fake-checker"
            fake.write_text(
                "#!/bin/sh\n"
                "if [ \"${3-}\" = -l ]; then printf 'synthetic core\\n' > \"$4\"; fi\n"
                "echo 's VERIFIED'\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            proof_manifest = proofs / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(COLLECTOR),
                    str(branch_manifest),
                    str(proofs),
                    "--solver",
                    str(fake),
                    "--checker",
                    str(fake),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            audit_manifest = root / "audit.json"
            subprocess.run(
                [
                    sys.executable,
                    str(AUDITOR),
                    str(proof_manifest),
                    str(branch_manifest),
                    str(proofs),
                    "--checker",
                    str(fake),
                    "--audit-dir",
                    str(root / "audit-logs"),
                    "--output",
                    str(audit_manifest),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            audit = json.loads(audit_manifest.read_text())
            self.assertTrue(audit["summary"]["complete_unsat"])
            self.assertEqual(audit["summary"]["verified_unsat"], 1)

            cores = root / "cores"
            subprocess.run(
                [
                    sys.executable,
                    str(COMPACTOR),
                    str(proof_manifest),
                    str(branch_manifest),
                    str(proofs),
                    "--checker",
                    str(fake),
                    "--output-dir",
                    str(cores),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            compacted = json.loads((cores / "manifest.json").read_text())
            self.assertTrue(
                compacted["summary"]["complete_for_listed_formulas"]
            )
            self.assertEqual(compacted["summary"]["verified_unsat"], 1)
            self.assertEqual(compacted["results"][0]["core_proof"]["bytes"], 15)


if __name__ == "__main__":
    unittest.main()
