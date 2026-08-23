import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_upstream_hol_minisat.py"
SPEC = importlib.util.spec_from_file_location("audit_upstream_hol_minisat", SCRIPT)
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


class UpstreamHolMinisatAuditTests(unittest.TestCase):
    def prepare(
        self, root: Path, *, fallback: bool = False
    ) -> tuple[Path, Path, Path, str]:
        upstream = root / "upstream"
        hol_root = upstream / "HOL"
        hol_root.mkdir(parents=True)
        git(hol_root, "init", "-q")
        (hol_root / "README").write_text("fixture\n", encoding="utf-8")
        git(hol_root, "add", ".")
        git(
            hol_root,
            "-c",
            "user.name=Ramsey55 Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        commit = git(hol_root, "rev-parse", "HEAD")

        build = root / "build"
        build.mkdir()
        solver = build / "minisat"
        solver.write_text(
            """#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
pathlib.Path(args[args.index('-r') + 1]).write_bytes(b'UNSAT\\n')
pathlib.Path(args[args.index('-p') + 1]).write_bytes(b'proof-trace')
if '-c' in args:
    print('Final clause: <empty>')
print('UNSATISFIABLE')
raise SystemExit(20)
""",
            encoding="utf-8",
        )
        solver.chmod(0o755)
        manifest = {
            "schema": MODULE.BUILD_SCHEMA,
            "hol_commit": commit,
            "compiler": {"coptimize": "-O3 -fsigned-char"},
            "artifacts": {
                "solver": {
                    "path": "minisat",
                    "bytes": solver.stat().st_size,
                    "sha256": MODULE.file_sha256(solver),
                }
            },
        }
        (build / "build-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        fake_hol = root / "hol"
        warning = MODULE.FALLBACK_TEXT if fallback else ""
        fake_hol.write_text(
            f"""#!/usr/bin/env python3
import pathlib
import re
import sys
script = sys.stdin.read()
match = re.search(r'set_infile "([^"]+)"', script)
if match is None:
    raise SystemExit(2)
base = pathlib.Path(match.group(1) + '.minisatp')
base.write_bytes(b'UNSAT\\n')
pathlib.Path(str(base) + '.proof').write_bytes(b'proof-trace')
pathlib.Path(str(base) + '.stats').write_bytes(b'UNSATISFIABLE\\n')
print('val replayed = |- regression: thm')
print({warning!r})
print('{MODULE.SUCCESS_MARKER}')
""",
            encoding="utf-8",
        )
        fake_hol.chmod(0o755)
        fixture = root / "regression.cnf"
        fixture.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="utf-8")
        return upstream, build, fixture, commit

    def test_accepts_exact_internal_and_kernel_replay(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            upstream, build, fixture, commit = self.prepare(root)
            document = MODULE.audit(
                upstream,
                build,
                fixture,
                expected_hol_commit=commit,
                expected_fixture_sha256=MODULE.file_sha256(fixture),
                hol_executable=root / "hol",
            )
            self.assertTrue(document["verified"])
            self.assertFalse(document["checks"]["hol_internal_dpll_fallback"])
            self.assertEqual(
                document["evidence"]["audit-direct.proof"]["sha256"],
                document["evidence"]["audit-kernel.proof"]["sha256"],
            )
            self.assertTrue((build / "audit.json").is_file())

    def test_rejects_hol_internal_prover_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            upstream, build, fixture, commit = self.prepare(root, fallback=True)
            with self.assertRaisesRegex(ValueError, "fell back"):
                MODULE.audit(
                    upstream,
                    build,
                    fixture,
                    expected_hol_commit=commit,
                    expected_fixture_sha256=MODULE.file_sha256(fixture),
                    hol_executable=root / "hol",
                )

    def test_refuses_solver_different_from_build_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            upstream, build, fixture, commit = self.prepare(root)
            with (build / "minisat").open("a", encoding="utf-8") as stream:
                stream.write("# changed\n")
            os.chmod(build / "minisat", 0o755)
            with self.assertRaisesRegex(ValueError, "does not match"):
                MODULE.audit(
                    upstream,
                    build,
                    fixture,
                    expected_hol_commit=commit,
                    expected_fixture_sha256=MODULE.file_sha256(fixture),
                    hol_executable=root / "hol",
                )


if __name__ == "__main__":
    unittest.main()
