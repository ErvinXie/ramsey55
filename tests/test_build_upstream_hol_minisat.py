import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_upstream_hol_minisat.py"
SPEC = importlib.util.spec_from_file_location("build_upstream_hol_minisat", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git(directory: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return process.stdout.strip()


class UpstreamHolMinisatBuildTests(unittest.TestCase):
    def test_build_uses_committed_source_and_signed_char_flags(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            hol = root / "upstream" / "HOL"
            source = hol / MODULE.SOURCE_PREFIX
            source.mkdir(parents=True)
            git(hol, "init", "-q")
            (source / "Main.C").write_text("main\n", encoding="utf-8")
            (source / "Solver.C").write_text("solver\n", encoding="utf-8")
            (source / "Solver.h").write_text("header\n", encoding="utf-8")
            fake_solver = source / "fake-solver"
            fake_solver.write_text("#!/bin/sh\necho committed\n", encoding="utf-8")
            fake_solver.chmod(0o755)
            (source / "Makefile").write_text(
                "r:\n\tcp fake-solver minisat\n", encoding="utf-8"
            )
            git(hol, "add", ".")
            git(
                hol,
                "-c",
                "user.name=Ramsey55 Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            )
            commit = git(hol, "rev-parse", "HEAD")

            # A dirty worktree must not affect a build extracted from the commit.
            fake_solver.write_text("#!/bin/sh\necho dirty\n", encoding="utf-8")
            output = root / "signed-build"
            document = MODULE.build(root / "upstream", output, commit)

            self.assertEqual(document["hol_commit"], commit)
            self.assertEqual(document["compiler"]["coptimize"], "-O3 -fsigned-char")
            self.assertTrue(document["host"]["signed_char_probe_passed"])
            self.assertTrue(os.access(output / "minisat", os.X_OK))
            self.assertEqual(
                subprocess.check_output([output / "minisat"], text=True), "committed\n"
            )
            on_disk = json.loads(
                (output / "build-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                on_disk["artifacts"]["solver"]["sha256"],
                MODULE.file_sha256(output / "minisat"),
            )

    def test_refuses_wrong_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            hol = root / "upstream" / "HOL"
            hol.mkdir(parents=True)
            git(hol, "init", "-q")
            (hol / "README").write_text("test\n", encoding="utf-8")
            git(hol, "add", ".")
            git(
                hol,
                "-c",
                "user.name=Ramsey55 Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            )
            with self.assertRaisesRegex(ValueError, "commit mismatch"):
                MODULE.build(root / "upstream", root / "output", "0" * 40)


if __name__ == "__main__":
    unittest.main()
