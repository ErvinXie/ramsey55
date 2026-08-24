import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_zstd_file_archive.py"
SPEC = importlib.util.spec_from_file_location("audit_zstd_file_archive", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict[str, object]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


class AuditZstdFileArchiveTests(unittest.TestCase):
    def populate(self, root: Path) -> tuple[Path, Path, Path, Path]:
        zstd = root / "zstd"
        zstd.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake zstd 1.0')\n"
            "elif '-t' in sys.argv:\n"
            "    data = pathlib.Path(sys.argv[-1]).read_bytes()\n"
            "    raise SystemExit(1 if data.startswith(b'corrupt') else 0)\n"
            "elif '-d' in sys.argv and '-c' in sys.argv:\n"
            "    data = pathlib.Path(sys.argv[-1]).read_bytes()\n"
            "    if data.startswith(b'corrupt'):\n"
            "        raise SystemExit(1)\n"
            "    sys.stdout.buffer.write(data)\n"
            "else:\n"
            "    raise SystemExit(2)\n",
            encoding="utf-8",
        )
        zstd.chmod(0o755)
        source = root / "prefix.drat"
        source.write_bytes(b"proof bytes\0")
        compressed = root / "prefix.drat.zst"
        compressed.write_bytes(source.read_bytes())
        provenance = root / "recovery.json"
        provenance.write_text('{"verified":true}\n', encoding="utf-8")
        source_record = record(source)
        manifest = root / "archive.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": MODULE.ARCHIVE_SCHEMA,
                    "source": source_record,
                    "compressed": record(compressed),
                    "recovery_manifest": record(provenance),
                    "compression": {
                        "format": "zstd",
                        "level": 1,
                        "executable": {
                            "path": str(zstd),
                            "sha256": sha256(zstd),
                            "version": "fake zstd 1.0",
                        },
                    },
                    "verification": {
                        "zstd_test": True,
                        "decompressed_bytes": source_record["bytes"],
                        "decompressed_sha256": source_record["sha256"],
                        "verified": True,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest, zstd, source, compressed

    def test_audits_archive_with_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, zstd, source, _ = self.populate(Path(raw))
            source.unlink()
            result = MODULE.audit(manifest, zstd)
            self.assertTrue(result["verified"])
            self.assertFalse(result["source_present_before"])
            self.assertFalse(result["restored"])

    def test_atomically_restores_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, zstd, source, _ = self.populate(Path(raw))
            expected = json.loads(manifest.read_text(encoding="utf-8"))["source"]
            source.unlink()
            result = MODULE.audit(manifest, zstd, restore=True)
            self.assertTrue(result["restored"])
            self.assertEqual(source.stat().st_size, expected["bytes"])
            self.assertEqual(sha256(source), expected["sha256"])
            self.assertFalse(source.with_name(source.name + ".restore.tmp").exists())

    def test_audits_compressed_symbolic_link(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd, source, compressed = self.populate(root)
            target = root / "relocated.zst"
            compressed.replace(target)
            compressed.symlink_to(target)
            source.unlink()
            result = MODULE.audit(manifest, zstd)
            self.assertTrue(result["verified"])
            self.assertEqual(result["compressed"]["sha256"], sha256(target))

    def test_rejects_corrupted_compressed_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, zstd, source, compressed = self.populate(Path(raw))
            source.unlink()
            compressed.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "compressed artifact mismatch"):
                MODULE.audit(manifest, zstd)

    def test_refuses_to_overwrite_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest, zstd, _, _ = self.populate(Path(raw))
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                MODULE.audit(manifest, zstd, restore=True)

    def test_rejects_provenance_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, zstd, source, _ = self.populate(root)
            source.unlink()
            (root / "recovery.json").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "recovery manifest artifact mismatch"):
                MODULE.audit(manifest, zstd)


if __name__ == "__main__":
    unittest.main()
