from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "tools/compose_binary_drat_protect_cnf.py"
CHECKER = ROOT / ".tools/src/drat-trim/drat-trim"


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


class ProtectedCnfCompositionTests(unittest.TestCase):
    def test_drops_reordered_cnf_deletion_and_retains_learned_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "input.cnf"
            first = root / "first.drat"
            second = root / "second.drat"
            output = root / "output.drat"
            manifest = root / "manifest.json"
            cnf.write_text("p cnf 130 2\n1 -130 0\n2 0\n", encoding="ascii")
            first.write_bytes(
                binary_clause("d", -130, 1)
                + binary_clause("a", 3)
                + binary_clause("d", 3)
            )
            second.write_bytes(binary_clause("a", -4))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(output),
                    str(first),
                    str(second),
                    "--append-empty",
                    "--manifest",
                    str(manifest),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                output.read_bytes(),
                binary_clause("a", 3)
                + binary_clause("d", 3)
                + binary_clause("a", -4)
                + binary_clause("a"),
            )
            document = json.loads(manifest.read_text())
            self.assertEqual(
                document["composition_counts"]["dropped_protected_deletions"], 1
            )
            self.assertEqual(
                document["composition_counts"]["retained_deletions"], 1
            )
            self.assertEqual(document["composition_counts"]["empty_additions"], 1)

    @unittest.skipUnless(CHECKER.is_file(), "drat-trim is not built")
    def test_protected_original_unit_is_accepted_by_real_checker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "input.cnf"
            fragment = root / "fragment.drat"
            output = root / "output.drat"
            cnf.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="ascii")
            fragment.write_bytes(binary_clause("d", 1))
            subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(output),
                    str(fragment),
                    "--append-empty",
                    "--manifest",
                    str(root / "manifest.json"),
                ],
                check=True,
                stdout=subprocess.PIPE,
            )
            checked = subprocess.run(
                [str(CHECKER), str(cnf), str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertIn("s VERIFIED", checked.stdout)

    def test_accepts_fresh_proof_variable_outside_cnf_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "input.cnf"
            fragment = root / "fragment.drat"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            fragment.write_bytes(binary_clause("a", 2))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(root / "output.drat"),
                    str(fragment),
                    "--manifest",
                    str(root / "manifest.json"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                (root / "output.drat").read_bytes(), binary_clause("a", 2)
            )

    def test_rejects_binary_literal_outside_signed_int32_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "input.cnf"
            fragment = root / "fragment.drat"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            fragment.write_bytes(binary_clause("a", 2_147_483_648))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(root / "output.drat"),
                    str(fragment),
                    "--manifest",
                    str(root / "manifest.json"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("outside signed int32 range", completed.stderr)

    def test_rejects_embedded_empty_addition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cnf = root / "input.cnf"
            fragment = root / "fragment.drat"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            fragment.write_bytes(binary_clause("a"))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(cnf),
                    str(root / "output.drat"),
                    str(fragment),
                    "--manifest",
                    str(root / "manifest.json"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("empty addition", completed.stderr)


if __name__ == "__main__":
    unittest.main()
