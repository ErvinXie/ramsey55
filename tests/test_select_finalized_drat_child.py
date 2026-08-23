from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "select_finalized_drat_child.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SelectFinalizedDratChildTests(unittest.TestCase):
    def candidate(self, root: Path, name: str, payload: bytes = b"a\x02\x00") -> tuple[Path, Path]:
        proof = root / f"{name}.drat"
        evidence = root / f"{name}.json"
        standalone = root / f"{name}.standalone.drat"
        proof.write_bytes(payload)
        standalone.write_bytes(payload + b"a\x00")
        evidence.write_text(
            json.dumps(
                {
                    "schema": "ramsey55.cadical-dfs-checkpoint-finalization.v1",
                    "checker_verified": True,
                    "output_fragment": {
                        "path": str(proof),
                        "sha256": sha256(proof),
                        "size": proof.stat().st_size,
                        "contains_empty_addition": False,
                    },
                    "standalone_proof": {
                        "path": str(standalone),
                        "sha256": sha256(standalone),
                        "size": standalone.stat().st_size,
                        "appended_empty_clause": True,
                    },
                }
            )
            + "\n"
        )
        return proof, evidence

    def run_tool(
        self, output: Path, candidates: list[tuple[Path, Path]]
    ) -> subprocess.CompletedProcess[str]:
        command = [str(TOOL)]
        for proof, evidence in candidates:
            command.extend(("--candidate", str(proof), str(evidence)))
        command.extend(("--output", str(output)))
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def test_reports_not_ready_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "selection.json"
            completed = self.run_tool(output, [(root / "missing", root / "missing.json")])
            self.assertEqual(completed.returncode, 4)
            self.assertFalse(output.exists())

    def test_selects_first_ready_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = self.candidate(root, "first")
            second = self.candidate(root, "second")
            output = root / "selection.json"
            completed = self.run_tool(output, [first, second])
            self.assertEqual(completed.returncode, 0, completed.stderr)
            document = json.loads(output.read_text())
            self.assertEqual(document["selected_index"], 0)
            self.assertEqual(document["selected"]["proof"]["sha256"], sha256(first[0]))

    def test_can_select_later_candidate_while_first_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            second = self.candidate(root, "second")
            output = root / "selection.json"
            completed = self.run_tool(
                output, [(root / "missing", root / "missing.json"), second]
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(output.read_text())["selected_index"], 1)

    def test_rejects_manifest_proof_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            proof, evidence = self.candidate(root, "bad")
            proof.write_bytes(b"changed")
            output = root / "selection.json"
            completed = self.run_tool(output, [(proof, evidence)])
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("does not match", completed.stderr)
            self.assertFalse(output.exists())

    def test_existing_selection_is_reverified(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = self.candidate(root, "candidate")
            output = root / "selection.json"
            first = self.run_tool(output, [candidate])
            self.assertEqual(first.returncode, 0, first.stderr)
            candidate[0].write_bytes(b"changed")
            second = self.run_tool(output, [candidate])
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("does not match", second.stderr)


if __name__ == "__main__":
    unittest.main()
