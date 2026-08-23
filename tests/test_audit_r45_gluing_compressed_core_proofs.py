from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_r45_gluing_compressed_core_proofs.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_r45_gluing_compressed_core_proofs", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict[str, object]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}


class AuditR45GluingCompressedCoreProofsTests(unittest.TestCase):
    def populate(self, root: Path) -> tuple[Path, Path, Path]:
        checker = root / "checker"
        checker.write_bytes(b"checker")
        zstd = root / "zstd"
        zstd.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake zstd 1.0')\n"
            "else:\n"
            "    sys.stdout.buffer.write(pathlib.Path(sys.argv[-1]).read_bytes())\n",
            encoding="utf-8",
        )
        zstd.chmod(0o755)

        branch_files = []
        proof_results = []
        core_results = []
        compressed_results = []
        source_total = core_total = compressed_total = 0
        core_dir = root / "core"
        compressed_dir = root / "compressed"
        core_dir.mkdir()
        compressed_dir.mkdir()
        for pair_index, payload in ((7, b"core one\n"), (11, b"core two\n")):
            name = f"pair-{pair_index}"
            source = payload + b"source"
            cnf_sha = hashlib.sha256(f"cnf-{pair_index}".encode()).hexdigest()
            core_path = core_dir / f"{name}.core.drat"
            compressed_path = compressed_dir / f"{name}.core.drat.zst"
            source_log = core_dir / f"{name}.source-checker.log"
            core_log = core_dir / f"{name}.core-checker.log"
            core_path.write_bytes(payload)
            compressed_path.write_bytes(payload)
            source_log.write_text("c details\ns VERIFIED\n", encoding="utf-8")
            core_log.write_text("s VERIFIED\nc details\n", encoding="utf-8")
            source_record = {
                "path": f"{name}.drat",
                "bytes": len(source),
                "sha256": hashlib.sha256(source).hexdigest(),
            }
            branch_files.append({"pair_index": pair_index, "sha256": cnf_sha})
            proof_results.append(
                {
                    "pair_index": pair_index,
                    "status": "VERIFIED_UNSAT",
                    "cnf": {"sha256": cnf_sha},
                    "proof": source_record,
                }
            )
            core_results.append(
                {
                    "pair_index": pair_index,
                    "status": "VERIFIED_UNSAT",
                    "cnf_sha256": cnf_sha,
                    "source_proof": source_record,
                    "core_proof": record(core_path),
                    "source_checker_log": record(source_log),
                    "core_checker_log": record(core_log),
                    "source_checker_seconds": 1.0,
                    "core_checker_seconds": 2.0,
                }
            )
            compressed_results.append(
                {
                    "pair_index": pair_index,
                    **record(compressed_path),
                    "core_bytes": len(payload),
                    "core_sha256": sha256(core_path),
                }
            )
            source_total += len(source)
            core_total += len(payload)
            compressed_total += len(payload)

        branch = root / "branches.json"
        branch.write_text(
            json.dumps(
                {"schema": "ramsey55.r45-gluing-branches.v2", "files": branch_files}
            ),
            encoding="utf-8",
        )
        proofs = root / "proofs.json"
        proofs.write_text(
            json.dumps(
                {
                    "schema": MODULE.PROOF_SCHEMA,
                    "branch_manifest": {
                        "sha256": sha256(branch),
                        "schema": "ramsey55.r45-gluing-branches.v2",
                    },
                    "results": proof_results,
                    "summary": {
                        "complete_unsat": True,
                        "formulas": 2,
                        "verified_unsat": 2,
                        "proof_bytes": source_total,
                    },
                }
            ),
            encoding="utf-8",
        )
        core_manifest = core_dir / "manifest.json"
        core_document = {
            "schema": MODULE.CORE_SCHEMA,
            "proof_manifest": {"path": str(proofs), "sha256": sha256(proofs)},
            "branch_manifest": {"path": str(branch), "sha256": sha256(branch)},
            "checker": {"path": str(checker), "sha256": sha256(checker)},
            "results": core_results,
            "summary": {
                "complete_for_listed_formulas": True,
                "formulas": 2,
                "verified_unsat": 2,
                "source_proof_bytes": source_total,
                "core_proof_bytes": core_total,
                "core_to_source_ratio": round(core_total / source_total, 9),
            },
        }
        core_manifest.write_text(json.dumps(core_document), encoding="utf-8")
        compressed_manifest = compressed_dir / "manifest.json"
        compressed_manifest.write_text(
            json.dumps(
                {
                    "schema": MODULE.COMPRESSED_SCHEMA,
                    "core_manifest": {
                        "path": str(core_manifest),
                        "sha256": sha256(core_manifest),
                        "schema": MODULE.CORE_SCHEMA,
                    },
                    "compression": {
                        "format": "zstd",
                        "executable_sha256": sha256(zstd),
                        "version": "fake zstd 1.0",
                    },
                    "results": compressed_results,
                    "summary": {
                        "complete_for_listed_formulas": True,
                        "formulas": 2,
                        "source_proof_bytes": source_total,
                        "core_bytes": core_total,
                        "compressed_bytes": compressed_total,
                        "compressed_to_core_ratio": round(
                            compressed_total / core_total, 9
                        ),
                        "compressed_to_source_ratio": round(
                            compressed_total / source_total, 9
                        ),
                    },
                }
            ),
            encoding="utf-8",
        )
        return core_manifest, compressed_manifest, zstd

    def test_rehashes_logs_cores_and_decompressed_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            core, compressed, zstd = self.populate(root)
            audit = MODULE.audit(core, compressed, zstd, root, jobs=2)
            self.assertTrue(audit["verified"])
            self.assertEqual(audit["summary"]["formulas"], 2)
            self.assertEqual(audit["summary"]["decompressed_identities"], 2)
            self.assertTrue(all(row["decompressed_identity"] for row in audit["results"]))

    def test_rejects_compressed_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            core, compressed, zstd = self.populate(root)
            (compressed.parent / "pair-7.core.drat.zst").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "compressed proof artifact mismatch"):
                MODULE.audit(core, compressed, zstd, root, jobs=1)

    def test_rejects_checker_log_without_exact_verified_line(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            core, compressed, zstd = self.populate(root)
            log = core.parent / "pair-7.core-checker.log"
            log.write_text("s VERIFIED extra\n", encoding="utf-8")
            document = json.loads(core.read_text(encoding="utf-8"))
            document["results"][0]["core_checker_log"] = record(log)
            core.write_text(json.dumps(document), encoding="utf-8")
            compressed_document = json.loads(compressed.read_text(encoding="utf-8"))
            compressed_document["core_manifest"]["sha256"] = sha256(core)
            compressed.write_text(json.dumps(compressed_document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lacks one exact s VERIFIED"):
                MODULE.audit(core, compressed, zstd, root, jobs=1)

    def test_rejects_pair_order_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            core, compressed, zstd = self.populate(root)
            document = json.loads(compressed.read_text(encoding="utf-8"))
            document["results"].reverse()
            compressed.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pair-index order"):
                MODULE.audit(core, compressed, zstd, root, jobs=1)


if __name__ == "__main__":
    unittest.main()
