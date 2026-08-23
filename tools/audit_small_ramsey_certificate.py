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
import tempfile
from typing import Any


SCHEMA = "ramsey55.checked-small-ramsey-certificate.v2"
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


def output_has_exact_line(output: str, expected: str) -> bool:
    return any(line.strip("\r") == expected for line in output.splitlines())


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
    lrat_checker_source: Path | None,
    rerun_lrat: bool,
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

    lrat = document.get("lrat")
    if not isinstance(lrat, dict) or lrat.get("verified") is not True:
        raise ValueError("LRAT record lacks verified=true")
    actions = lrat.get("actions")
    if not isinstance(actions, int) or actions <= 0:
        raise ValueError("LRAT record has invalid action count")
    original_lrat_record, original_lrat_path = checked_file_record(
        lrat.get("original"), "original LRAT", root
    )
    dense_lrat_record, dense_lrat_path = checked_file_record(
        lrat.get("dense"), "dense LRAT", root
    )

    conversion = lrat.get("conversion")
    if not isinstance(conversion, dict) or conversion.get("verified") is not True:
        raise ValueError("LRAT conversion record lacks verified=true")
    if require_sha256(conversion.get("checker_sha256"), "LRAT converter") != checker_hash:
        raise ValueError("LRAT converter hash differs from DRAT checker hash")
    conversion_log_record, conversion_log_path = checked_file_record(
        conversion.get("log"), "LRAT conversion log", root
    )
    conversion_time_record, _ = checked_file_record(
        conversion.get("timing_log"), "LRAT conversion timing log", root
    )
    if not exact_status_line(conversion_log_path, "s VERIFIED"):
        raise ValueError("LRAT conversion log lacks an exact s VERIFIED line")

    normalizer = lrat.get("normalizer")
    if not isinstance(normalizer, dict) or normalizer.get("verified") is not True:
        raise ValueError("LRAT normalizer record lacks verified=true")
    normalizer_tool = resolve_path(root, normalizer.get("tool", ""))
    if not normalizer_tool.is_file():
        raise ValueError(f"LRAT normalizer does not exist: {normalizer_tool}")
    if file_sha256(normalizer_tool) != require_sha256(
        normalizer.get("tool_sha256"), "LRAT normalizer tool"
    ):
        raise ValueError("LRAT normalizer tool hash mismatch")
    normalizer_log_record, normalizer_log_path = checked_file_record(
        normalizer.get("log"), "LRAT normalizer log", root
    )
    expected_normalizer_line = (
        f"normalized {actions} LRAT actions ({actions} emitted)"
    )
    if not exact_status_line(normalizer_log_path, expected_normalizer_line):
        raise ValueError("LRAT normalizer log lacks the expected action count")

    lean_lrat = lrat.get("lean_core_check")
    if not isinstance(lean_lrat, dict) or lean_lrat.get("verified") is not True:
        raise ValueError("Lean core LRAT record lacks verified=true")
    lean_lrat_tool = resolve_path(root, lean_lrat.get("tool", ""))
    if not lean_lrat_tool.is_file():
        raise ValueError(f"Lean core LRAT tool does not exist: {lean_lrat_tool}")
    if file_sha256(lean_lrat_tool) != require_sha256(
        lean_lrat.get("tool_sha256"), "Lean core LRAT tool"
    ):
        raise ValueError("Lean core LRAT tool hash mismatch")
    lean_lrat_log_record, lean_lrat_log_path = checked_file_record(
        lean_lrat.get("log"), "Lean core LRAT log", root
    )
    expected_lean_lrat_line = f"verified typed r34 LRAT: {actions} actions"
    if not exact_status_line(lean_lrat_log_path, expected_lean_lrat_line):
        raise ValueError("Lean core LRAT log lacks the expected verification line")

    formal_bridge_record, _ = checked_file_record(
        lrat.get("formal_bridge"), "LRAT formal bridge", root
    )
    formal_target_record, _ = checked_file_record(
        lrat.get("formal_target"), "LRAT formal target", root
    )

    independent_lrat = lrat.get("independent_check")
    if (
        not isinstance(independent_lrat, dict)
        or independent_lrat.get("verified") is not True
    ):
        raise ValueError("independent LRAT record lacks verified=true")
    independent_source_hash = require_sha256(
        independent_lrat.get("source_sha256"), "independent LRAT checker source"
    )
    original_lrat_log_record, original_lrat_log_path = checked_file_record(
        independent_lrat.get("original_log"), "original independent LRAT log", root
    )
    dense_lrat_log_record, dense_lrat_log_path = checked_file_record(
        independent_lrat.get("dense_log"), "dense independent LRAT log", root
    )
    for label, log_path in (
        ("original", original_lrat_log_path),
        ("dense", dense_lrat_log_path),
    ):
        if not exact_status_line(log_path, "c VERIFIED"):
            raise ValueError(
                f"{label} independent LRAT log lacks an exact c VERIFIED line"
            )
    if lrat_checker_source is not None:
        if not lrat_checker_source.is_file():
            raise ValueError(
                f"independent LRAT checker source does not exist: {lrat_checker_source}"
            )
        if file_sha256(lrat_checker_source) != independent_source_hash:
            raise ValueError("independent LRAT checker source hash mismatch")

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
        if completed.returncode or not output_has_exact_line(
            completed.stdout, "s VERIFIED"
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

    lrat_rerun: dict[str, Any] | None = None
    if rerun_lrat:
        if checker_path is None:
            raise ValueError("--rerun-lrat requires --checker")
        if lrat_checker_source is None:
            raise ValueError("--rerun-lrat requires --lrat-checker-source")
        with tempfile.TemporaryDirectory(prefix="ramsey55-r34-lrat-") as temporary:
            temporary_root = Path(temporary)
            regenerated_original = temporary_root / "r34-n9.lrat"
            regenerated_dense = temporary_root / "r34-n9-dense.lrat"
            independent_checker = temporary_root / "lrat-check"

            converted = subprocess.run(
                [
                    str(checker_path),
                    str(cnf_path),
                    str(proof_path),
                    "-L",
                    str(regenerated_original),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if converted.returncode or not output_has_exact_line(
                converted.stdout, "s VERIFIED"
            ):
                raise RuntimeError(
                    f"DRAT-to-LRAT rerun failed (exit {converted.returncode})"
                )
            if file_sha256(regenerated_original) != original_lrat_record["sha256"]:
                raise RuntimeError("DRAT-to-LRAT rerun changed original LRAT bytes")

            normalized = subprocess.run(
                [
                    "lake",
                    "env",
                    "lean",
                    "--run",
                    str(normalizer_tool),
                    str(clauses),
                    str(regenerated_original),
                    str(regenerated_dense),
                ],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if normalized.returncode or not output_has_exact_line(
                normalized.stdout, expected_normalizer_line
            ):
                raise RuntimeError(
                    f"LRAT normalization rerun failed (exit {normalized.returncode})"
                )
            if file_sha256(regenerated_dense) != dense_lrat_record["sha256"]:
                raise RuntimeError("LRAT normalization rerun changed dense LRAT bytes")

            lean_checked = subprocess.run(
                [
                    "lake",
                    "env",
                    "lean",
                    "--run",
                    str(lean_lrat_tool),
                    str(regenerated_dense),
                ],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if lean_checked.returncode or not output_has_exact_line(
                lean_checked.stdout, expected_lean_lrat_line
            ):
                raise RuntimeError(
                    f"Lean core LRAT rerun failed (exit {lean_checked.returncode})"
                )

            compiled = subprocess.run(
                ["cc", "-O2", "-o", str(independent_checker), str(lrat_checker_source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if compiled.returncode:
                raise RuntimeError(
                    f"independent LRAT checker compilation failed (exit {compiled.returncode})"
                )
            independent_outputs: dict[str, str] = {}
            for label, candidate in (
                ("original", regenerated_original),
                ("dense", regenerated_dense),
            ):
                checked = subprocess.run(
                    [str(independent_checker), str(cnf_path), str(candidate)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                if checked.returncode or not output_has_exact_line(
                    checked.stdout, "c VERIFIED"
                ):
                    raise RuntimeError(
                        f"independent {label} LRAT rerun failed "
                        f"(exit {checked.returncode})"
                    )
                independent_outputs[label] = hashlib.sha256(
                    checked.stdout.encode()
                ).hexdigest()
            lrat_rerun = {
                "conversion_output_sha256": hashlib.sha256(
                    converted.stdout.encode()
                ).hexdigest(),
                "normalizer_output_sha256": hashlib.sha256(
                    normalized.stdout.encode()
                ).hexdigest(),
                "lean_output_sha256": hashlib.sha256(
                    lean_checked.stdout.encode()
                ).hexdigest(),
                "independent_output_sha256": independent_outputs,
                "verified": True,
            }

    return {
        "schema": "ramsey55.checked-small-ramsey-certificate-audit.v2",
        "manifest_sha256": file_sha256(manifest_path),
        "cnf_sha256": cnf_record["sha256"],
        "generator_manifest_sha256": generator_record["sha256"],
        "proof_sha256": proof_record["sha256"],
        "solver_log_sha256": solver_log_record["sha256"],
        "checker_log_sha256": checker_log_record["sha256"],
        "typed_log_sha256": typed_log_record["sha256"],
        "typed_timing_log_sha256": timing_record["sha256"],
        "original_lrat_sha256": original_lrat_record["sha256"],
        "dense_lrat_sha256": dense_lrat_record["sha256"],
        "lrat_conversion_log_sha256": conversion_log_record["sha256"],
        "lrat_conversion_timing_log_sha256": conversion_time_record["sha256"],
        "lrat_normalizer_log_sha256": normalizer_log_record["sha256"],
        "lean_lrat_log_sha256": lean_lrat_log_record["sha256"],
        "formal_bridge_sha256": formal_bridge_record["sha256"],
        "formal_target_sha256": formal_target_record["sha256"],
        "original_independent_lrat_log_sha256": original_lrat_log_record["sha256"],
        "dense_independent_lrat_log_sha256": dense_lrat_log_record["sha256"],
        "checker_rerun": checker_rerun,
        "reconstructor_rerun": reconstructor_rerun,
        "typed_rerun": typed_rerun,
        "lrat_rerun": lrat_rerun,
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
    parser.add_argument("--lrat-checker-source", type=Path)
    parser.add_argument("--rerun-lrat", action="store_true")
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
        arguments.lrat_checker_source,
        arguments.rerun_lrat,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
