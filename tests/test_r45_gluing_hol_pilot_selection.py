from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/audit_r45_gluing_hol_pilot_selection.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_r45_gluing_hol_pilot_selection", TOOL
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class R45GluingHolPilotSelectionTests(unittest.TestCase):
    def populate(self, root: Path, sizes: tuple[int, int] = (2, 5)) -> dict[str, Path]:
        proof_directory = root / "proofs"
        proof_directory.mkdir()
        proof_records = []
        for pair_index, size in zip((1, 3), sizes, strict=True):
            path = proof_directory / f"p{pair_index}.drat"
            path.write_bytes(bytes([pair_index]) * size)
            proof_records.append(
                {
                    "pair_index": pair_index,
                    "status": "VERIFIED_UNSAT",
                    "proof": {
                        "path": path.name,
                        "bytes": size,
                        "sha256": MODULE.file_sha256(path),
                    },
                }
            )
        branch_document = {
            "schema": "ramsey55.r45-gluing-branches.v2",
            "fixed_star_degree": 12,
            "total_pairs": 4,
            "pair_indices": [1, 3],
            "files": [
                {"pair_index": 1, "left_code": 11, "right_code": 17},
                {"pair_index": 3, "left_code": 13, "right_code": 19},
            ],
        }
        branch_manifest = root / "branches.json"
        branch_manifest.write_text(json.dumps(branch_document), encoding="utf-8")
        proof_document = {
            "schema": "ramsey55.r45-gluing-proofs.v1",
            "branch_manifest": {
                "schema": branch_document["schema"],
                "sha256": MODULE.file_sha256(branch_manifest),
            },
            "results": proof_records,
            "summary": {
                "formulas": 2,
                "verified_unsat": 2,
                "complete_unsat": True,
                "proof_bytes": sum(sizes),
            },
        }
        proof_manifest = root / "proofs.json"
        proof_manifest.write_text(json.dumps(proof_document), encoding="utf-8")
        full_problem_list = root / "full.pbl"
        full_problem_list.write_text(
            "7 23\n11 17\n29 31\n13 19\n", encoding="ascii"
        )
        pilot_problem_list = root / "pilot.pbl"
        selected = "13 19\n" if sizes[1] > sizes[0] else "11 17\n"
        pilot_problem_list.write_text(selected, encoding="ascii")
        return {
            "proof_manifest_path": proof_manifest,
            "branch_manifest_path": branch_manifest,
            "proof_directory": proof_directory,
            "full_problem_list_path": full_problem_list,
            "pilot_problem_list_path": pilot_problem_list,
        }

    def test_accepts_rehashed_maximum_and_exact_problem_row(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            document = MODULE.audit(**self.populate(Path(raw)))
            self.assertTrue(document["verified"])
            self.assertEqual(document["sample"]["raw_proof_artifacts_rehashed"], 2)
            self.assertEqual(document["selection"]["pair_index_zero_based"], 3)
            self.assertEqual(document["selection"]["full_problem_list_line_one_based"], 4)
            self.assertEqual(document["selection"]["runner_up"]["proof_bytes"], 2)

    def test_tie_is_broken_by_lower_global_pair_index(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            document = MODULE.audit(**self.populate(Path(raw), sizes=(5, 5)))
            self.assertEqual(document["selection"]["pair_index_zero_based"], 1)

    def test_rejects_pilot_for_nonmaximum_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["pilot_problem_list_path"].write_text("11 17\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "pilot problem list"):
                MODULE.audit(**paths)

    def test_rejects_unbound_branch_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["branch_manifest_path"].write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema"):
                MODULE.audit(**paths)

    def test_rejects_incomplete_proof_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            manifest = json.loads(paths["proof_manifest_path"].read_text())
            manifest["results"][0]["status"] = "UNKNOWN"
            paths["proof_manifest_path"].write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "non-verified"):
                MODULE.audit(**paths)

    def test_rejects_mutated_proof_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            (paths["proof_directory"] / "p3.drat").write_bytes(b"mutated")
            with self.assertRaisesRegex(ValueError, "proof artifact mismatch"):
                MODULE.audit(**paths)


if __name__ == "__main__":
    unittest.main()
