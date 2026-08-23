#!/usr/bin/env python3
"""Audit an exact family of generated and freshly loaded HOL4 gluing theories."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "ramsey55.upstream-hol-gluing-theory-audit.v1"
THEORY_SUFFIXES = (
    "Script.sml",
    "Theory.sml",
    "Theory.sig",
    "Theory.dat",
    "Theory.ui",
    "Theory.uo",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def read_problem_list(path: Path) -> list[tuple[int, int]]:
    pairs = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if len(fields) != 2:
                raise ValueError(
                    f"{path}:{line_number}: expected exactly two integer fields"
                )
            try:
                pair = (int(fields[0]), int(fields[1]))
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid problem pair"
                ) from error
            if pair[0] <= 0 or pair[1] <= 0:
                raise ValueError(f"{path}:{line_number}: nonpositive problem code")
            pairs.append(pair)
    if not pairs or len(pairs) != len(set(pairs)):
        raise ValueError("problem pairs must be nonempty and unique")
    return pairs


def theory_name(pair: tuple[int, int]) -> str:
    return f"r45_{pair[0]}_{pair[1]}"


def expected_script(pair: tuple[int, int]) -> str:
    name = theory_name(pair)
    return (
        "open HolKernel kernel glue\n"
        f'val _ = new_theory "{name}"\n'
        f'val _ = save_thm ("{name}", glue_pair '
        f'(stinf "{pair[0]}", stinf "{pair[1]}"))\n'
        "val _ = export_theory ()\n"
    )


def require_exit_zero(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"^\s*Exit status:\s*(\d+)\s*$", text, re.MULTILINE)
    if matches != ["0"]:
        raise ValueError(f"expected one GNU-time exit status 0: {path}")


def require_clean_log(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    forbidden = (
        "Static Errors",
        "uncaught exception",
        "RAMSEY55_GLUE_KERNEL_AUDIT_FAIL",
        "KERNEL_FULL_FAIL",
        "KERNEL_LOAD_FAIL",
    )
    for token in forbidden:
        if token in text:
            raise ValueError(f"forbidden failure marker {token!r} in {path}")
    return text


def require_buildheap_log(path: Path, name: str) -> None:
    text = require_clean_log(path)
    required = (
        f'Created theory "{name}"',
        f'Saved theorem _____ "{name}"',
        f'Exporting theory "{name}" ... done.',
        f'Theory "{name}" took ',
    )
    if any(text.count(marker) != 1 for marker in required):
        raise ValueError(f"buildheap log lacks exact success markers: {path}")
    forbidden = ("fallback", "warning", "error", "exception")
    lowered = text.lower()
    for token in forbidden:
        if token in lowered:
            raise ValueError(f"forbidden buildheap token {token!r}: {path}")


def require_build_markers(
    text: str, label: str, pairs: list[tuple[int, int]]
) -> None:
    prefix = f"RAMSEY55_{label}"
    starts = [
        (int(index), int(left), int(right))
        for index, left, right in re.findall(
            rf"{re.escape(prefix)}_START\s+(\d+)\s+(\d+)\s+(\d+)", text
        )
    ]
    expected_starts = [
        (index, pair[0], pair[1]) for index, pair in enumerate(pairs)
    ]
    if starts != expected_starts:
        raise ValueError("build START markers do not exactly match the problem list")
    done = [
        int(index)
        for index in re.findall(rf"{re.escape(prefix)}_DONE\s+(\d+)", text)
    ]
    if done != list(range(len(pairs))):
        raise ValueError("build DONE markers are not exact and ordered")
    cursor = 0
    for index, pair in enumerate(pairs):
        start_marker = f"{prefix}_START {index} {pair[0]} {pair[1]}"
        done_marker = f"{prefix}_DONE {index}"
        start_position = text.find(start_marker, cursor)
        done_position = text.find(done_marker, start_position + len(start_marker))
        if start_position < 0 or done_position < 0:
            raise ValueError("build START/DONE markers are not sequential")
        cursor = done_position + len(done_marker)
    final_marker = f"{prefix}_KERNEL_FULL_{len(pairs)}_OK"
    if text.count(final_marker) != 1 or text.find(final_marker, cursor) < 0:
        raise ValueError(f"expected one final build marker: {final_marker}")


def require_load_markers(
    text: str, label: str, pairs: list[tuple[int, int]]
) -> None:
    prefix = f"RAMSEY55_{label}"
    suffix = "F C4524B C4524R NO_FALSE_HYP"
    loaded = [
        int(index)
        for index in re.findall(
            rf"{re.escape(prefix)}_LOAD\s+(\d+)\s+{suffix}", text
        )
    ]
    if loaded != list(range(len(pairs))):
        raise ValueError("fresh-load theorem-shape markers are not exact and ordered")
    final_marker = f"{prefix}_KERNEL_LOAD_{len(pairs)}_OK"
    last_load = text.rfind(f"{prefix}_LOAD {len(pairs) - 1} {suffix}")
    if text.count(final_marker) != 1 or text.find(final_marker, last_load) < 0:
        raise ValueError(f"expected one final load marker: {final_marker}")


def audit(
    problem_list: Path,
    theory_directory: Path,
    label: str,
    build_log: Path,
    build_time_log: Path,
    load_log: Path,
    load_time_log: Path,
    evidence: list[Path] | None = None,
) -> dict[str, object]:
    if not re.fullmatch(r"GLUE\d+", label):
        raise ValueError("label must match GLUE followed by decimal digits")
    problem_list = problem_list.resolve()
    theory_directory = theory_directory.resolve()
    pairs = read_problem_list(problem_list)
    build_text = require_clean_log(build_log)
    load_text = require_clean_log(load_log)
    require_build_markers(build_text, label, pairs)
    require_load_markers(load_text, label, pairs)
    require_exit_zero(build_time_log)
    require_exit_zero(load_time_log)

    expected_names = {theory_name(pair) for pair in pairs}
    observed_names = set()
    for suffix in THEORY_SUFFIXES:
        observed_names.update(
            path.name.removesuffix(suffix)
            for path in theory_directory.glob(f"r45_*{suffix}")
        )
    if observed_names != expected_names:
        missing = sorted(expected_names - observed_names)
        extra = sorted(observed_names - expected_names)
        raise ValueError(
            f"theory stem set mismatch: missing={missing[:3]}, extra={extra[:3]}"
        )
    buildheap_directory = theory_directory / "buildheap"
    observed_buildheap_names = {
        path.name.removeprefix("buildheap_").removesuffix("Script")
        for path in buildheap_directory.glob("buildheap_r45_*Script")
    }
    if observed_buildheap_names != expected_names:
        missing = sorted(expected_names - observed_buildheap_names)
        extra = sorted(observed_buildheap_names - expected_names)
        raise ValueError(
            f"buildheap-log stem set mismatch: missing={missing[:3]}, "
            f"extra={extra[:3]}"
        )

    theories = []
    for index, pair in enumerate(pairs):
        name = theory_name(pair)
        script_path = theory_directory / f"{name}Script.sml"
        if script_path.read_text(encoding="utf-8") != expected_script(pair):
            raise ValueError(f"generated script is not exact: {script_path}")
        files = {
            suffix: artifact(theory_directory / f"{name}{suffix}")
            for suffix in THEORY_SUFFIXES
        }
        buildheap_log = buildheap_directory / f"buildheap_{name}Script"
        require_buildheap_log(buildheap_log, name)
        theories.append(
            {
                "index": index,
                "left_code": pair[0],
                "right_code": pair[1],
                "theory_name": name,
                "files": files,
                "buildheap_log": artifact(buildheap_log),
                "fresh_loaded_conclusion": "F",
                "fresh_loaded_required_hypotheses": ["C4524B", "C4524R"],
                "fresh_loaded_contains_false_hypothesis": False,
            }
        )

    return {
        "schema": SCHEMA,
        "claim": (
            "the exact listed gluing scripts produced nonempty HOL4 theory "
            "artifacts and a fresh HOL4 session loaded each exported theorem "
            "with conclusion F, both C4524 hypotheses, and no F hypothesis; "
            "global cover exhaustiveness is separate"
        ),
        "verified": True,
        "label": label,
        "auditor": artifact(Path(__file__)),
        "problem_list": artifact(problem_list),
        "theory_directory": str(theory_directory),
        "build_log": artifact(build_log),
        "build_time_log": artifact(build_time_log),
        "load_log": artifact(load_log),
        "load_time_log": artifact(load_time_log),
        "evidence": [artifact(path.resolve()) for path in evidence or []],
        "summary": {
            "pairs": len(pairs),
            "unique_pairs": len(set(pairs)),
            "exact_generated_scripts": len(theories),
            "complete_six_file_theories": len(theories),
            "exact_successful_buildheap_logs": len(theories),
            "fresh_loaded_false_theorems": len(theories),
            "fresh_loaded_theorems_without_false_hypothesis": len(theories),
        },
        "theories": theories,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("problem_list", type=Path)
    parser.add_argument("--theory-directory", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--build-log", type=Path, required=True)
    parser.add_argument("--build-time-log", type=Path, required=True)
    parser.add_argument("--load-log", type=Path, required=True)
    parser.add_argument("--load-time-log", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    try:
        document = audit(
            arguments.problem_list,
            arguments.theory_directory,
            arguments.label,
            arguments.build_log,
            arguments.build_time_log,
            arguments.load_log,
            arguments.load_time_log,
            arguments.evidence,
        )
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"audited {document['summary']['pairs']} fresh-loaded HOL4 gluing theorems")


if __name__ == "__main__":
    main()
