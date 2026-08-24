from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
SCRIPT = TOOLS / "archive_zstd_file.py"
SPEC = importlib.util.spec_from_file_location("archive_zstd_file", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArchiveZstdFileTests(unittest.TestCase):
    def populate(self, root: Path) -> tuple[Path, Path, Path]:
        zstd = root / "zstd"
        zstd.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake zstd 1.0')\n"
            "elif '-t' in sys.argv:\n"
            "    raise SystemExit(0)\n"
            "elif '-d' in sys.argv and '-c' in sys.argv:\n"
            "    sys.stdout.buffer.write(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "elif '-c' in sys.argv:\n"
            "    sys.stdout.buffer.write(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "else:\n"
            "    raise SystemExit(2)\n",
            encoding="utf-8",
        )
        zstd.chmod(0o755)
        source = root / "proof.drat"
        source.write_bytes(b"proof archive bytes\0")
        provenance = root / "proof.manifest.json"
        provenance.write_text('{"verified":true}\n', encoding="utf-8")
        return zstd, source, provenance

    def test_creates_auditable_and_restorable_archive(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            zstd, source, provenance = self.populate(root)
            compressed = root / "archive" / "proof.drat.zst"
            compressed.parent.mkdir()
            manifest = compressed.with_name(compressed.name + ".archive.json")
            document = MODULE.create_archive(
                source, provenance, compressed, manifest, zstd
            )
            self.assertEqual(document["provenance"]["path"], str(provenance))
            audited = MODULE.audit(manifest, zstd)
            self.assertTrue(audited["verified"])
            source.unlink()
            restored = MODULE.audit(manifest, zstd, restore=True)
            self.assertTrue(restored["restored"])
            self.assertEqual(source.read_bytes(), b"proof archive bytes\0")

    def test_refuses_existing_archive_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            zstd, source, provenance = self.populate(root)
            compressed = root / "proof.drat.zst"
            compressed.write_bytes(b"existing")
            manifest = root / "proof.drat.zst.archive.json"
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                MODULE.create_archive(
                    source, provenance, compressed, manifest, zstd
                )


if __name__ == "__main__":
    unittest.main()
