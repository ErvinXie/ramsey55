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
AUDITOR = ROOT / "tools/audit_binary_drat_protect_cnf.py"


def encode_literal(literal: int) -> bytes:
    value = 2 * abs(literal) + (literal < 0)
    output = bytearray()
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def binary_clause(marker: str, *literals: int) -> bytes:
    return marker.encode("ascii") + b"".join(map(encode_literal, literals)) + b"\0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditProtectedCnfCompositionTests(unittest.TestCase):
    def compose(self, root: Path) -> tuple[Path, Path, Path]:
        cnf = root / "input.cnf"
        fragment = root / "fragment.drat"
        output = root / "output.drat"
        manifest = root / "manifest.json"
        cnf.write_text("p cnf 130 3\n1 -130 0\n2 0\n1 -130 0\n", encoding="ascii")
        fragment.write_bytes(
            binary_clause("d", -130, 1)
            + binary_clause("a", 131)
            + binary_clause("d", 131)
        )
        subprocess.run(
            [
                sys.executable,
                str(COMPOSER),
                str(cnf),
                str(output),
                str(fragment),
                "--append-empty",
                "--manifest",
                str(manifest),
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        checker_log = root / "checker.log"
        checker_log.write_text("c test\ns VERIFIED\n", encoding="utf-8")
        return manifest, output, checker_log

    def run_auditor(
        self, manifest: Path, checker_log: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(AUDITOR),
                str(manifest),
                "--checker-log",
                str(checker_log),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_audits_exact_composition_and_checker_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _, checker_log = self.compose(Path(directory))
            completed = self.run_auditor(manifest, checker_log)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["verified"])
            self.assertTrue(report["checker_verified"])
            self.assertEqual(report["cnf_exact_unique_clauses"], 2)
            self.assertEqual(
                report["composition_counts"]["dropped_protected_deletions"], 1
            )

    def test_auditor_runs_without_production_composer_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _, checker_log = self.compose(root)
            isolated = root / "isolated-auditor.py"
            shutil.copyfile(AUDITOR, isolated)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(isolated),
                    str(manifest),
                    "--checker-log",
                    str(checker_log),
                ],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["verified"])

    def test_rejects_rehashed_noncomponent_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, output, checker_log = self.compose(Path(directory))
            document = json.loads(manifest.read_text())
            output.write_bytes(binary_clause("a", 4) + binary_clause("a"))
            document["output"]["size"] = output.stat().st_size
            document["output"]["sha256"] = sha256(output)
            manifest.write_text(json.dumps(document), encoding="utf-8")
            completed = self.run_auditor(manifest, checker_log)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("not the exact protected-CNF composition", completed.stderr)

    def test_rejects_nonexact_checker_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, _, checker_log = self.compose(Path(directory))
            checker_log.write_text("c s VERIFIED eventually\n", encoding="utf-8")
            completed = self.run_auditor(manifest, checker_log)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("exact s VERIFIED", completed.stderr)


if __name__ == "__main__":
    unittest.main()
