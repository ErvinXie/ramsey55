from __future__ import annotations

import importlib.util
import json
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
RUNNER = load("run_arm_cold_archive")


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


class RunArmColdArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tar = gnu_tar()
        zstd = shutil.which("zstd")
        self.zstd = Path(zstd).resolve() if zstd else None

    def require_tools(self) -> tuple[Path, Path]:
        if self.tar is None or self.zstd is None:
            self.skipTest("GNU tar and zstd are required")
        return self.tar, self.zstd

    @staticmethod
    def make_plan(root: Path) -> tuple[Path, Path, Path]:
        source = root / "source"
        archive_root = root / "archive"
        source.mkdir()
        archive_root.mkdir()
        for child in ("large", "small"):
            directory = source / child
            directory.mkdir()
            (directory / "proof").write_bytes((child.encode() + b"\0") * 100)
        (source / "root-manifest.json").write_text("{}\n", encoding="utf-8")
        snapshot = archive_root / "snapshot.json"
        snapshot.write_text('{"schema":"fixture"}\n', encoding="utf-8")
        plan = archive_root / "plan.json"
        plan.write_text(
            json.dumps(
                {
                    "schema": RUNNER.PLAN_SCHEMA,
                    "archive_root": str(archive_root),
                    "snapshot": AUDITOR.file_record(snapshot),
                    "phases": [
                        {
                            "name": "children",
                            "kind": "children",
                            "parent": str(source),
                            "children": ["large", "small"],
                        },
                        {
                            "name": "container",
                            "kind": "directory",
                            "source": str(source),
                        },
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return source, archive_root, plan

    def test_runs_nested_plan_and_is_resumable(self) -> None:
        tar, zstd = self.require_tools()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            source, archive_root, plan = self.make_plan(root)
            plan_sha256 = AUDITOR.file_sha256(plan)
            checked = RUNNER.run(
                plan, plan_sha256, archive_root, zstd, tar, 1, 2, True
            )
            self.assertTrue(checked["verified"])
            self.assertEqual(checked["shards"], 3)
            completed = RUNNER.run(
                plan, plan_sha256, archive_root, zstd, tar, 1, 2
            )
            self.assertTrue(completed["verified"])
            self.assertEqual(completed["shards"], 3)
            self.assertFalse(source.exists())
            receipts = list((archive_root / "shards").glob("*/*/removal.json"))
            self.assertEqual(len(receipts), 3)
            resumed = RUNNER.run(
                plan, plan_sha256, archive_root, zstd, tar, 1, 2
            )
            self.assertEqual(resumed, completed)

    def test_rejects_plan_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _, archive_root, plan = self.make_plan(Path(raw).resolve())
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                RUNNER.load_plan(plan, "0" * 64)
            self.assertTrue(archive_root.is_dir())


if __name__ == "__main__":
    unittest.main()
