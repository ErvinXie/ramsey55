#!/usr/bin/env python3
"""Independently audit a retained small asymmetric-Ramsey DRAT certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


SCHEMA = "ramsey55.checked-small-ramsey-certificate.v1"
GENERATOR_SCHEMA = "ramsey55.asymmetric-ramsey-upper-bound.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_file_record(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest lacks {label} file record")
    if not isinstance(value.get("path"), str) or not value["path"]:
        raise ValueError(f"manifest has invalid {label} path")
    digest = value.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"manifest has invalid {label} hash")
    if not isinstance(value.get("size"), int) or value["size"] < 0:
        raise ValueError(f"manifest has invalid {label} size")
    return value


def resolve_path(root: Path, recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else root / path


def checked_file_record(
    value: Any, label: str, root: Path
) -> tuple[dict[str, Any], Path]:
    record = validate_file_record(value, label)
    path = resolve_path(root, record["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != record["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    if file_sha256(path) != record["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    return record, path


def exact_status_line(path: Path, expected: str) -> bool:
    return any(
        line.strip("\r") == expected
        for line in path.read_text(encoding="utf-8", errors="strict").splitlines()
    )


def read_cnf_dimensions(path: Path) -> tuple[int, int, int]:
    variables: int | None = None
    declared: int | None = None
    observed = 0
    pending = False
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.strip().split()
            if not fields or fields[0] == "c":
                continue
            if fields[0] == "p":
                if (
                    variables is not None
                    or fields[:2] != ["p", "cnf"]
                    or len(fields) != 4
                ):
                    raise ValueError(f"invalid CNF header at line {line_number}")
                variables, declared = int(fields[2]), int(fields[3])
                continue
            if variables is None:
                raise ValueError(f"CNF clause precedes header at line {line_number}")
            for field in fields:
                literal = int(field)
                if literal == 0:
                    observed += 1
                    pending = False
                else:
                    if abs(literal) > variables:
                        raise ValueError(
                            f"CNF literal outside header at line {line_number}"
                        )
                    pending = True
    if variables is None or declared is None:
        raise ValueError("CNF header is missing")
    if pending:
        raise ValueError("unterminated final CNF clause")
    if observed != declared:
        raise ValueError("CNF observed clause count differs from header")
    return variables, declared, observed


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"manifest has invalid {label} hash")
    return value


def audit(
    manifest_path: Path,
    root: Path,
    checker_path: Path | None,
    rerun_checker: bool,
    rerun_reconstructor: bool,
    rerun_typed: bool,
) -> dict[str, Any]:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("unexpected small-certificate manifest schema")
    if document.get("verified") is not True:
        raise ValueError("certificate manifest lacks verified=true")
    dimensions = document.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("certificate manifest lacks dimensions")
    variables = dimensions.get("variables")
    clauses = dimensions.get("clauses")
    if not isinstance(variables, int) or variables < 0:
        raise ValueError("invalid variable count")
    if not isinstance(clauses, int) or clauses < 0:
        raise ValueError("invalid clause count")

    cnf_record, cnf_path = checked_file_record(document.get("cnf"), "cnf", root)
    observed_variables, declared_clauses, observed_clauses = read_cnf_dimensions(
        cnf_path
    )
    if (observed_variables, declared_clauses, observed_clauses) != (
        variables,
        clauses,
        clauses,
    ):
        raise ValueError("CNF dimensions do not match certificate manifest")
    generator_record, generator_path = checked_file_record(
        document.get("generator_manifest"), "generator manifest", root
    )
    generator = json.loads(generator_path.read_text(encoding="utf-8"))
    if not isinstance(generator, dict) or generator.get("schema") != GENERATOR_SCHEMA:
        raise ValueError("unexpected generator manifest schema")
    if generator.get("variables") != variables or generator.get("clauses") != clauses:
        raise ValueError("generator manifest dimensions mismatch")
    if generator.get("sha256") != cnf_record["sha256"]:
        raise ValueError("generator manifest CNF hash mismatch")

    proof_record, proof_path = checked_file_record(document.get("proof"), "proof", root)
    if document["proof"].get("format") != "binary DRAT":
        raise ValueError("unexpected proof format")
    solver = document.get("solver")
    if not isinstance(solver, dict) or solver.get("exit_status") != 20:
        raise ValueError("solver record lacks exit status 20")
    solver_log_record, solver_log_path = checked_file_record(
        solver.get("log"), "solver log", root
    )
    if not exact_status_line(solver_log_path, "s UNSATISFIABLE"):
        raise ValueError("solver log lacks an exact s UNSATISFIABLE line")
    require_sha256(solver.get("sha256"), "solver")

    checker = document.get("checker")
    if not isinstance(checker, dict) or checker.get("verified") is not True:
        raise ValueError("checker record lacks verified=true")
    checker_hash = require_sha256(checker.get("sha256"), "checker")
    checker_log_record, checker_log_path = checked_file_record(
        checker.get("log"), "checker log", root
    )
    if not exact_status_line(checker_log_path, "s VERIFIED"):
        raise ValueError("checker log lacks an exact s VERIFIED line")

    typed = document.get("typed_formula_check")
    if not isinstance(typed, dict) or typed.get("verified") is not True:
        raise ValueError("typed-formula record lacks verified=true")
    typed_tool = resolve_path(root, typed.get("tool", ""))
    if not typed_tool.is_file():
        raise ValueError(f"typed-formula tool does not exist: {typed_tool}")
    if file_sha256(typed_tool) != require_sha256(
        typed.get("tool_sha256"), "typed tool"
    ):
        raise ValueError("typed-formula tool hash mismatch")
    typed_log_record, typed_log_path = checked_file_record(
        typed.get("log"), "typed-formula log", root
    )
    timing_record, _ = checked_file_record(
        typed.get("timing_log"), "typed-formula timing log", root
    )
    matched = typed.get("matched_clauses")
    if matched != clauses:
        raise ValueError("typed-formula clause count mismatch")
    typed_text = typed_log_path.read_text(encoding="utf-8", errors="strict")
    if not re.search(rf"^verified .+: {clauses} clauses$", typed_text, re.MULTILINE):
        raise ValueError("typed-formula log lacks the expected verification line")

    checker_rerun: dict[str, Any] | None = None
    if checker_path is not None:
        if not checker_path.is_file():
            raise ValueError(f"checker does not exist: {checker_path}")
        if file_sha256(checker_path) != checker_hash:
            raise ValueError("provided checker hash mismatch")
    if rerun_checker:
        if checker_path is None:
            raise ValueError("--rerun-checker requires --checker")
        completed = subprocess.run(
            [str(checker_path), str(cnf_path), str(proof_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode or not any(
            line.strip("\r") == "s VERIFIED" for line in completed.stdout.splitlines()
        ):
            raise RuntimeError(
                f"checker rerun rejected proof (exit {completed.returncode})"
            )
        checker_rerun = {
            "returncode": completed.returncode,
            "verified": True,
            "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        }

    reconstructor_rerun: dict[str, Any] | None = None
    if rerun_reconstructor:
        verifier = root / "tools/verify_asymmetric_ramsey_cnf.py"
        completed = subprocess.run(
            [
                sys.executable,
                str(verifier),
                str(generator_path),
                "--cnf-dir",
                str(cnf_path.parent),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                f"CNF reconstructor rerun failed (exit {completed.returncode})"
            )
        reconstructor_rerun = {
            "verifier_sha256": file_sha256(verifier),
            "verified": True,
            "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        }

    typed_rerun: dict[str, Any] | None = None
    if rerun_typed:
        completed = subprocess.run(
            ["lake", "env", "lean", "--run", str(typed_tool), str(cnf_path)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        expected = f"verified {cnf_path}: {clauses} clauses"
        if completed.returncode or expected not in completed.stdout.splitlines():
            raise RuntimeError(
                f"typed-formula rerun failed (exit {completed.returncode})"
            )
        typed_rerun = {
            "returncode": completed.returncode,
            "verified": True,
            "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        }

    return {
        "schema": "ramsey55.checked-small-ramsey-certificate-audit.v1",
        "manifest_sha256": file_sha256(manifest_path),
        "cnf_sha256": cnf_record["sha256"],
        "generator_manifest_sha256": generator_record["sha256"],
        "proof_sha256": proof_record["sha256"],
        "solver_log_sha256": solver_log_record["sha256"],
        "checker_log_sha256": checker_log_record["sha256"],
        "typed_log_sha256": typed_log_record["sha256"],
        "typed_timing_log_sha256": timing_record["sha256"],
        "checker_rerun": checker_rerun,
        "reconstructor_rerun": reconstructor_rerun,
        "typed_rerun": typed_rerun,
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--checker", type=Path)
    parser.add_argument("--rerun-checker", action="store_true")
    parser.add_argument("--rerun-reconstructor", action="store_true")
    parser.add_argument("--rerun-typed", action="store_true")
    arguments = parser.parse_args()
    if not arguments.manifest.is_file():
        parser.error(f"manifest does not exist: {arguments.manifest}")
    report = audit(
        arguments.manifest,
        arguments.root,
        arguments.checker,
        arguments.rerun_checker,
        arguments.rerun_reconstructor,
        arguments.rerun_typed,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
