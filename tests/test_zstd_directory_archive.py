from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def load(name: str):
    path = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDITOR = load("audit_zstd_directory_archive")
ARCHIVER = load("archive_zstd_directory")
REMOVER = load("remove_verified_directory_archive_source")


def gnu_tar() -> Path | None:
    for name in ("gtar", "tar"):
        candidate = shutil.which(name)
        if candidate is None:
            continue
        version = subprocess.run(
            [candidate, "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ).stdout
        if "GNU tar" in version:
            return Path(candidate).resolve()
    return None


class ZstdDirectoryArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tar = gnu_tar()
        zstd = shutil.which("zstd")
        self.zstd = Path(zstd).resolve() if zstd else None

    def require_tools(self) -> tuple[Path, Path]:
        if self.tar is None or self.zstd is None:
            self.skipTest("GNU tar and zstd are required")
        return self.tar, self.zstd

    @staticmethod
    def populate(root: Path) -> tuple[Path, Path, Path]:
        source_parent = root / "source-parent"
        source = source_parent / "shard"
        archive_root = root / "archive"
        source.mkdir(parents=True)
        archive_root.mkdir()
        (source / "nested").mkdir()
        (source / "proof.drat").write_bytes(b"proof bytes\0" * 1000)
        (source / "nested" / "manifest.json").write_text(
            '{"verified":true}\n', encoding="utf-8"
        )
        os.link(source / "proof.drat", source / "proof-hardlink.drat")
        (source / "proof-link.drat").symlink_to("proof.drat")
        with (source / "sparse.bin").open("wb") as stream:
            stream.seek((1 << 20) - 1)
            stream.write(b"\0")
        provenance = archive_root / "snapshot.json"
        provenance.write_text('{"frozen":true}\n', encoding="utf-8")
        return source, archive_root, provenance

    def create(self, root: Path) -> tuple[Path, Path, Path, Path, Path]:
        tar, zstd = self.require_tools()
        source, archive_root, provenance = self.populate(root)
        archive = archive_root / "shard.tar.zst"
        manifest = archive_root / "shard.archive.json"
        audit_path = archive_root / "shard.audit.json"
        ARCHIVER.create_archive(
            source,
            provenance,
            archive,
            manifest,
            audit_path,
            zstd,
            tar,
        )
        return source, archive, manifest, audit_path, provenance

    def test_create_audit_remove_restore_and_reaudit(self) -> None:
        tar, zstd = self.require_tools()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            source, archive, manifest, audit_path, _ = self.create(root)
            initial = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertTrue(initial["verified"])
            self.assertTrue(initial["source_compared"])

            receipt = archive.parent / "shard.removal.json"
            removed = REMOVER.remove_source(
                manifest,
                audit_path,
                source.parent,
                receipt,
                zstd,
                tar,
            )
            self.assertTrue(removed["recoverable"])
            self.assertFalse(source.exists())
            archived_only = AUDITOR.audit(manifest, zstd, tar)
            self.assertTrue(archived_only["verified"])
            self.assertFalse(archived_only["source_compared"])

            decompressor = subprocess.Popen(
                [str(zstd), "-q", "-d", "-c", str(archive)],
                stdout=subprocess.PIPE,
            )
            assert decompressor.stdout is not None
            extraction = subprocess.run(
                [str(tar), "--extract", "--file=-", "--directory", str(source.parent)],
                stdin=decompressor.stdout,
                check=False,
            )
            decompressor.stdout.close()
            self.assertEqual(extraction.returncode, 0)
            self.assertEqual(decompressor.wait(), 0)
            restored = AUDITOR.audit(manifest, zstd, tar, require_source=True)
            self.assertTrue(restored["source_compared"])
            self.assertTrue((source / "proof-link.drat").is_symlink())
            self.assertEqual(
                os.stat(source / "proof.drat").st_ino,
                os.stat(source / "proof-hardlink.drat").st_ino,
            )

    def test_audit_rejects_changed_source(self) -> None:
        tar, zstd = self.require_tools()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            source, _, manifest, _, _ = self.create(root)
            (source / "proof.drat").write_bytes(b"changed")
            with self.assertRaisesRegex(
                ValueError, "source directory statistics mismatch|archive differs"
            ):
                AUDITOR.audit(manifest, zstd, tar, require_source=True)

    def test_removal_rejects_wrong_allowed_parent(self) -> None:
        tar, zstd = self.require_tools()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            source, _, manifest, audit_path, _ = self.create(root)
            wrong = root / "wrong"
            wrong.mkdir()
            with self.assertRaisesRegex(ValueError, "immediate child"):
                REMOVER.remove_source(
                    manifest,
                    audit_path,
                    wrong,
                    root / "archive" / "bad.receipt.json",
                    zstd,
                    tar,
                )
            self.assertTrue(source.is_dir())


if __name__ == "__main__":
    unittest.main()
