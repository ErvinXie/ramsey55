import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "compress_r45_gluing_core_proofs.py"
SPEC = importlib.util.spec_from_file_location(
    "compress_r45_gluing_core_proofs", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompressR45GluingCoreProofsTests(unittest.TestCase):
    def populate(self, root: Path) -> tuple[Path, Path]:
        zstd = root / "zstd"
        zstd.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake zstd 1.0')\n"
            "elif '-d' in sys.argv:\n"
            "    sys.stdout.buffer.write(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "else:\n"
            "    out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "    out.write_bytes(pathlib.Path(sys.argv[-1]).read_bytes())\n",
            encoding="utf-8",
        )
        zstd.chmod(0o755)
        results = []
        source_bytes = 0
        for pair_index, payload in ((7, b"proof one\n"), (11, b"proof two\n")):
            core = root / f"pair-{pair_index}.core.drat"
            core.write_bytes(payload)
            source_bytes += len(payload) * 2
            results.append(
                {
                    "pair_index": pair_index,
                    "status": "VERIFIED_UNSAT",
                    "core_proof": {
                        "path": core.name,
                        "bytes": len(payload),
                        "sha256": sha256(core),
                    },
                }
            )
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": MODULE.CORE_SCHEMA,
                    "results": results,
                    "summary": {
                        "formulas": 2,
                        "verified_unsat": 2,
                        "complete_for_listed_formulas": True,
                        "source_proof_bytes": source_bytes,
                        "core_proof_bytes": sum(
                            result["core_proof"]["bytes"] for result in results
                        ),
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest, zstd

    def test_compresses_and_rehashes_every_core(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd = self.populate(root)
            output = root / "compressed"
            document = MODULE.compress(manifest, output, zstd, level=1, jobs=2)
            self.assertTrue(document["summary"]["complete_for_listed_formulas"])
            self.assertEqual(document["summary"]["formulas"], 2)
            self.assertEqual(document["compression"]["version"], "fake zstd 1.0")
            self.assertTrue((output / "manifest.json").is_file())
            for result in document["results"]:
                compressed = output / result["path"]
                core = root / compressed.name.removesuffix(".zst")
                self.assertEqual(compressed.read_bytes(), core.read_bytes())
                self.assertEqual(result["core_sha256"], sha256(core))

    def test_rejects_core_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd = self.populate(root)
            (root / "pair-7.core.drat").write_bytes(b"changed\n")
            with self.assertRaisesRegex(ValueError, "core artifact mismatch"):
                MODULE.compress(manifest, root / "compressed", zstd, 1, 1)

    def test_rejects_incomplete_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd = self.populate(root)
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["summary"]["complete_for_listed_formulas"] = False
            manifest.write_text(json.dumps(document) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest is incomplete"):
                MODULE.compress(manifest, root / "compressed", zstd, 1, 1)

    def test_rejects_decompression_mismatch_and_cleans_temporary_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd = self.populate(root)
            zstd.write_text(
                zstd.read_text(encoding="utf-8").replace(
                    "sys.stdout.buffer.write(pathlib.Path(sys.argv[-1]).read_bytes())",
                    "sys.stdout.buffer.write(b'wrong')",
                ),
                encoding="utf-8",
            )
            output = root / "compressed"
            with self.assertRaisesRegex(RuntimeError, "does not match core"):
                MODULE.compress(manifest, output, zstd, 1, 2)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".compressed.*")), [])

    def test_refuses_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd = self.populate(root)
            output = root / "compressed"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                MODULE.compress(manifest, output, zstd, 1, 1)


if __name__ == "__main__":
    unittest.main()
