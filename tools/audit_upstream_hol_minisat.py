#!/usr/bin/env python3
"""Audit ARM MiniSat regression behavior and HOL4 kernel proof replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BUILD_SCHEMA = "ramsey55.upstream-hol-minisat-build.v1"
SCHEMA = "ramsey55.upstream-hol-minisat-kernel-replay.v1"
EXPECTED_HOL_COMMIT = "cf03ce2dc756feb6c0bc4b042f879595d21f2e68"
EXPECTED_FIXTURE_SHA256 = (
    "b76c8a6e998afe4fad0ecb29257683b388b6bc3d90bc2bb2e9f14673ffcd7ad7"
)
FALLBACK_TEXT = "Proof replay failed. Using internal prover."
SUCCESS_MARKER = "RAMSEY55_KERNEL_REPLAY_OK"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_artifact(name: str, data: bytes) -> dict[str, object]:
    return {
        "path": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def sml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def kernel_script(solver: Path, cnf: Path) -> str:
    return f'''load "HolSatLib";
open SatSolvers satConfig minisatProve;
Globals.interactive := true;
val fixed = case minisatp of SatSolver r => SatSolver {{
  name = #name r, URL = #URL r, executable = {sml_string(str(solver))},
  post_exe = #post_exe r, notime_run = #notime_run r,
  time_run = #time_run r, post_run = #post_run r,
  only_true = #only_true r, failure_string = #failure_string r,
  start_string = #start_string r, end_string = #end_string r}};
val cfg = set_infile {sml_string(str(cnf))} (set_solver fixed base_config);
val replayed = GEN_SAT cfg;
print "{SUCCESS_MARKER}\\n";
print_thm replayed;
'''


def require_file(path: Path) -> bytes:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return path.read_bytes()


def git_head(hol_root: Path) -> str:
    process = subprocess.run(
        ["git", "-C", str(hol_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        raise ValueError(f"cannot read HOL4 commit: {process.stderr.strip()}")
    return process.stdout.strip()


def audit(
    upstream_root: Path,
    build_directory: Path,
    fixture: Path,
    *,
    expected_hol_commit: str = EXPECTED_HOL_COMMIT,
    expected_fixture_sha256: str = EXPECTED_FIXTURE_SHA256,
    hol_executable: Path | None = None,
    timeout_seconds: float = 300.0,
) -> dict[str, object]:
    upstream_root = upstream_root.resolve()
    build_directory = build_directory.resolve()
    fixture = fixture.resolve()
    hol_root = upstream_root / "HOL"
    solver = build_directory / "minisat"
    manifest_path = build_directory / "build-manifest.json"
    if not os.access(solver, os.X_OK):
        raise ValueError(f"solver is not executable: {solver}")
    if not fixture.is_file():
        raise ValueError(f"missing regression fixture: {fixture}")
    observed_fixture_sha256 = file_sha256(fixture)
    if observed_fixture_sha256 != expected_fixture_sha256:
        raise ValueError(
            "regression fixture hash mismatch: "
            f"expected {expected_fixture_sha256}, found {observed_fixture_sha256}"
        )
    try:
        build_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read build manifest: {error}") from error
    if build_manifest.get("schema") != BUILD_SCHEMA:
        raise ValueError("unexpected build manifest schema")
    if build_manifest.get("hol_commit") != expected_hol_commit:
        raise ValueError("build manifest HOL4 commit mismatch")
    if build_manifest.get("compiler", {}).get("coptimize") != "-O3 -fsigned-char":
        raise ValueError("build manifest does not record exact signed-char flags")
    solver_record = build_manifest.get("artifacts", {}).get("solver", {})
    if (
        solver_record.get("bytes") != solver.stat().st_size
        or solver_record.get("sha256") != file_sha256(solver)
    ):
        raise ValueError("solver does not match its build manifest")
    observed_commit = git_head(hol_root)
    if observed_commit != expected_hol_commit:
        raise ValueError(
            "HOL4 checkout mismatch: "
            f"expected {expected_hol_commit}, found {observed_commit}"
        )

    hol = (hol_executable or hol_root / "bin" / "hol").resolve()
    if not os.access(hol, os.X_OK):
        raise ValueError(f"HOL executable is not executable: {hol}")

    evidence_names = [
        "audit-direct.result",
        "audit-direct.proof",
        "audit-solver.stdout.log",
        "audit-solver.stderr.log",
        "audit-kernel.result",
        "audit-kernel.proof",
        "audit-kernel.stats",
        "audit-hol.stdout.log",
        "audit-hol.stderr.log",
        "audit.json",
    ]
    existing = [name for name in evidence_names if (build_directory / name).exists()]
    if existing:
        raise ValueError(f"refusing to overwrite audit artifacts: {existing}")

    with tempfile.TemporaryDirectory(prefix="ramsey55-hol-minisat-audit-") as raw:
        temporary = Path(raw)
        direct_cnf = temporary / "direct.cnf"
        kernel_cnf = temporary / "kernel.cnf"
        shutil.copyfile(fixture, direct_cnf)
        shutil.copyfile(fixture, kernel_cnf)
        direct_result = temporary / "direct.result"
        direct_proof = temporary / "direct.proof"
        direct = subprocess.run(
            [
                str(solver),
                str(direct_cnf),
                "-r",
                str(direct_result),
                "-p",
                str(direct_proof),
                "-x",
                "-c",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        if direct.returncode != 20:
            raise ValueError(
                f"direct MiniSat exit was {direct.returncode}, expected 20"
            )
        direct_result_data = require_file(direct_result)
        direct_proof_data = require_file(direct_proof)
        if direct_result_data != b"UNSAT\n":
            raise ValueError("direct MiniSat result is not exact UNSAT")
        if b"Final clause: <empty>" not in direct.stdout:
            raise ValueError(
                "MiniSat internal proof traversal did not reach empty clause"
            )
        if b"PROOF ERROR!" in direct.stdout or b"PROOF ERROR!" in direct.stderr:
            raise ValueError("MiniSat internal proof traversal reported an error")

        replay = subprocess.run(
            [str(hol), "--q"],
            input=kernel_script(solver, kernel_cnf).encode("utf-8"),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        replay_text = (replay.stdout + replay.stderr).decode(
            "utf-8", errors="replace"
        )
        if replay.returncode != 0:
            raise ValueError(f"HOL4 replay exit was {replay.returncode}, expected 0")
        if SUCCESS_MARKER not in replay_text:
            raise ValueError("HOL4 replay did not reach its post-theorem marker")
        if FALLBACK_TEXT in replay_text:
            raise ValueError("HOL4 replay fell back to the internal DPLL prover")

        kernel_result = Path(str(kernel_cnf) + ".minisatp")
        kernel_proof = Path(str(kernel_result) + ".proof")
        kernel_stats = Path(str(kernel_result) + ".stats")
        kernel_result_data = require_file(kernel_result)
        kernel_proof_data = require_file(kernel_proof)
        kernel_stats_data = require_file(kernel_stats)
        if kernel_result_data != b"UNSAT\n":
            raise ValueError("HOL-invoked MiniSat result is not exact UNSAT")
        if b"UNSATISFIABLE" not in kernel_stats_data:
            raise ValueError("HOL-invoked MiniSat stats lack UNSATISFIABLE")
        if kernel_proof_data != direct_proof_data:
            raise ValueError("direct and HOL-invoked proof traces differ")

        evidence = {
            "audit-direct.result": direct_result_data,
            "audit-direct.proof": direct_proof_data,
            "audit-solver.stdout.log": direct.stdout,
            "audit-solver.stderr.log": direct.stderr,
            "audit-kernel.result": kernel_result_data,
            "audit-kernel.proof": kernel_proof_data,
            "audit-kernel.stats": kernel_stats_data,
            "audit-hol.stdout.log": replay.stdout,
            "audit-hol.stderr.log": replay.stderr,
        }
        document = {
            "schema": SCHEMA,
            "claim": (
                "the signed-char MiniSat regression proof was checked by its "
                "internal resolution traversal and replayed by the pinned HOL4 kernel"
            ),
            "verified": True,
            "upstream_root": str(upstream_root),
            "hol_commit": observed_commit,
            "auditor": {
                "path": str(Path(__file__).resolve()),
                "bytes": Path(__file__).stat().st_size,
                "sha256": file_sha256(Path(__file__).resolve()),
            },
            "hol_executable": {
                "path": str(hol),
                "bytes": hol.stat().st_size,
                "sha256": file_sha256(hol),
            },
            "build_manifest": {
                "path": str(manifest_path),
                "bytes": manifest_path.stat().st_size,
                "sha256": file_sha256(manifest_path),
            },
            "solver": {
                "path": str(solver),
                "bytes": solver.stat().st_size,
                "sha256": file_sha256(solver),
            },
            "fixture": {
                "path": str(fixture),
                "bytes": fixture.stat().st_size,
                "sha256": observed_fixture_sha256,
            },
            "checks": {
                "direct_exit": direct.returncode,
                "direct_result_exact_unsat": True,
                "internal_resolution_final_empty": True,
                "hol_exit": replay.returncode,
                "hol_post_theorem_marker": True,
                "hol_internal_dpll_fallback": False,
                "direct_and_hol_proofs_identical": True,
            },
            "evidence": {
                name: bytes_artifact(name, data) for name, data in evidence.items()
            },
        }
        for name, data in evidence.items():
            (build_directory / name).write_bytes(data)
        (build_directory / "audit.json").write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    parser.add_argument("build_directory", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--expected-hol-commit", default=EXPECTED_HOL_COMMIT)
    parser.add_argument(
        "--expected-fixture-sha256", default=EXPECTED_FIXTURE_SHA256
    )
    parser.add_argument("--hol-executable", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    arguments = parser.parse_args()
    try:
        audit(
            arguments.upstream_root,
            arguments.build_directory,
            arguments.fixture,
            expected_hol_commit=arguments.expected_hol_commit,
            expected_fixture_sha256=arguments.expected_fixture_sha256,
            hol_executable=arguments.hol_executable,
            timeout_seconds=arguments.timeout_seconds,
        )
    except (ValueError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))
    print(
        "verified signed-char MiniSat internal traversal and HOL4 kernel replay; "
        f"wrote {arguments.build_directory / 'audit.json'}"
    )


if __name__ == "__main__":
    main()
