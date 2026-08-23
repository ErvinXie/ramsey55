#!/usr/bin/env python3
"""Build pinned HOL4 MiniSat from committed sources with signed-char semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "ramsey55.upstream-hol-minisat-build.v1"
EXPECTED_HOL_COMMIT = "cf03ce2dc756feb6c0bc4b042f879595d21f2e68"
SOURCE_PREFIX = "src/HolSat/sat_solvers/minisat"
COPTIMIZE = "-O3 -fsigned-char"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(hol_root: Path, *arguments: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(hol_root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(arguments)} failed: {detail}")
    return process.stdout


def compiler_macros(compiler: str, *flags: str) -> str:
    process = subprocess.run(
        [compiler, *flags, "-dM", "-E", "-x", "c++", "-"],
        input=b"",
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"compiler macro probe failed: {detail}")
    return process.stdout.decode("utf-8", errors="strict")


def artifact(path: Path, *, relative_to: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.relative_to(relative_to)),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def external_artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def build(
    upstream_root: Path,
    output_directory: Path,
    expected_hol_commit: str = EXPECTED_HOL_COMMIT,
    compiler: str = "c++",
) -> dict[str, object]:
    upstream_root = upstream_root.resolve()
    hol_root = upstream_root / "HOL"
    output_directory = output_directory.resolve()
    if output_directory.exists():
        raise ValueError(f"refusing to overwrite {output_directory}")
    if not output_directory.parent.is_dir():
        raise ValueError(f"missing output parent: {output_directory.parent}")
    if not (hol_root / ".git").exists():
        raise ValueError(f"missing HOL4 git checkout: {hol_root}")

    commit = run_git(hol_root, "rev-parse", "HEAD").decode().strip()
    if commit != expected_hol_commit:
        raise ValueError(
            f"HOL4 commit mismatch: expected {expected_hol_commit}, found {commit}"
        )

    names = run_git(
        hol_root,
        "ls-tree",
        "-r",
        "--name-only",
        commit,
        "--",
        SOURCE_PREFIX,
    ).decode("utf-8", errors="strict").splitlines()
    required = {"Main.C", "Solver.C", "Solver.h", "Makefile"}
    basenames = {Path(name).name for name in names}
    if not names or not required.issubset(basenames):
        raise ValueError("committed MiniSat source family is incomplete")

    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise ValueError(f"compiler not found: {compiler}")
    version_process = subprocess.run(
        [compiler_path, "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if version_process.returncode != 0:
        raise ValueError("compiler version probe failed")
    default_macros = compiler_macros(compiler_path)
    signed_macros = compiler_macros(compiler_path, "-fsigned-char")
    if "__CHAR_UNSIGNED__" in signed_macros:
        raise ValueError("-fsigned-char did not clear __CHAR_UNSIGNED__")

    with tempfile.TemporaryDirectory(prefix="ramsey55-hol-minisat-build-") as raw:
        build_root = Path(raw) / "minisat"
        build_root.mkdir()
        sources = []
        for name in names:
            relative = Path(name).relative_to(SOURCE_PREFIX)
            if len(relative.parts) != 1:
                raise ValueError(f"unexpected nested MiniSat source: {name}")
            data = run_git(hol_root, "show", f"{commit}:{name}")
            destination = build_root / relative
            destination.write_bytes(data)
            blob = run_git(hol_root, "rev-parse", f"{commit}:{name}").decode().strip()
            sources.append(
                {
                    "path": name,
                    "git_blob": blob,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )

        command = [
            "make",
            "-C",
            str(build_root),
            "r",
            f"COPTIMIZE={COPTIMIZE}",
            f"MINISAT_CXX={compiler_path}",
        ]
        process = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if process.returncode != 0:
            detail = process.stdout.decode("utf-8", errors="replace")[-8000:]
            raise ValueError(f"MiniSat build failed:\n{detail}")
        built_solver = build_root / "minisat"
        if not built_solver.is_file() or built_solver.stat().st_size == 0:
            raise ValueError("MiniSat build did not create a nonempty executable")

        publication = Path(
            tempfile.mkdtemp(
                prefix=f".{output_directory.name}.", dir=output_directory.parent
            )
        )
        try:
            solver = publication / "minisat"
            shutil.copy2(built_solver, solver)
            solver.chmod(0o755)
            build_log = publication / "build.log"
            build_log.write_bytes(process.stdout)
            document = {
                "schema": SCHEMA,
                "claim": (
                    "binary built from the exact committed HOL4 MiniSat source "
                    "with signed-char semantics; proof acceptance is separate"
                ),
                "upstream_root": str(upstream_root),
                "hol_commit": commit,
                "builder": external_artifact(Path(__file__).resolve()),
                "source_prefix": SOURCE_PREFIX,
                "sources": sources,
                "host": {
                    "machine": platform.machine(),
                    "default_char_unsigned": "__CHAR_UNSIGNED__" in default_macros,
                    "signed_char_probe_passed": True,
                },
                "compiler": {
                    "path": compiler_path,
                    "version_first_line": version_process.stdout.splitlines()[0],
                    "coptimize": COPTIMIZE,
                },
                "command": command,
                "artifacts": {
                    "solver": artifact(solver, relative_to=publication),
                    "build_log": artifact(build_log, relative_to=publication),
                },
            }
            (publication / "build-manifest.json").write_text(
                json.dumps(document, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(publication, output_directory)
        except BaseException:
            shutil.rmtree(publication, ignore_errors=True)
            raise
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--expected-hol-commit", default=EXPECTED_HOL_COMMIT)
    parser.add_argument("--compiler", default="c++")
    arguments = parser.parse_args()
    try:
        document = build(
            arguments.upstream_root,
            arguments.output_directory,
            arguments.expected_hol_commit,
            arguments.compiler,
        )
    except ValueError as error:
        parser.error(str(error))
    solver = document["artifacts"]["solver"]
    print(
        f"built signed-char MiniSat {solver['sha256']} at "
        f"{arguments.output_directory}"
    )


if __name__ == "__main__":
    main()
