#!/usr/bin/env python3
"""Replay screened-split telemetry at a smaller time/variable budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.generate_cartesian_cubes import parse_variables
    from tools.prove_materialized_cubes import file_sha256
    from tools.select_screened_binary_splits import SCHEMA, read_results
else:
    from generate_cartesian_cubes import parse_variables
    from prove_materialized_cubes import file_sha256
    from select_screened_binary_splits import SCHEMA, read_results


ANALYSIS_SCHEMA = "ramsey55.screened-split-budget-analysis.v1"


def effective_status(status: int, elapsed: float, seconds: float) -> int:
    """Return the status that the recorded run had reached by ``seconds``."""

    if status not in (0, 10, 20) or elapsed < 0 or seconds <= 0:
        raise ValueError("invalid solver status, elapsed time, or replay budget")
    return status if status in (10, 20) and elapsed <= seconds else 0


def checked_path(binding: dict[str, Any], label: str) -> Path:
    path = Path(str(binding["path"]))
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    if file_sha256(path) != binding["sha256"]:
        raise ValueError(f"{label} hash mismatch: {path}")
    return path


def analyze_selection(
    selection_path: Path,
    seconds: float,
    permitted_variables: set[int] | None,
) -> dict[str, Any]:
    if seconds <= 0:
        raise ValueError("screen budget must be positive")
    document = json.loads(selection_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError(f"unexpected selection schema in {selection_path}")

    parents = int(document["parents"]["count"])
    if parents <= 0:
        raise ValueError("selection has no parents")
    variables_path = checked_path(document["variables"], "variable list")
    variables = parse_variables(
        variables_path.read_text(encoding="ascii").strip(), maximum_count=None
    )
    if len(variables) != int(document["variables"]["count"]):
        raise ValueError("variable count mismatch")
    eligible = [
        variable
        for variable in variables
        if permitted_variables is None or variable in permitted_variables
    ]
    if not eligible:
        raise ValueError("replay variable range selects no recorded variables")

    solver_bindings = document.get("screen_solvers")
    if not isinstance(solver_bindings, list) or len(solver_bindings) < 2:
        raise ValueError("selection must bind at least two screen solvers")
    tables = []
    expected_rows = 2 * parents * len(variables)
    for source, binding in enumerate(solver_bindings):
        results_binding = {
            "path": binding["results"],
            "sha256": binding["results_sha256"],
        }
        results_path = checked_path(results_binding, f"solver {source} results")
        table = read_results(results_path)
        if len(table) != expected_rows:
            raise ValueError(f"solver {source} result count mismatch")
        if any(result.status == 10 for result in table):
            raise RuntimeError(f"SAT result in solver {source} requires investigation")
        tables.append(table)

    variable_indices = [
        index for index, variable in enumerate(variables) if variable in eligible
    ]
    candidates: list[list[dict[str, Any]]] = []
    width = 2 * len(variables)
    for parent in range(parents):
        parent_candidates: list[dict[str, Any]] = []
        for variable_index in variable_indices:
            variable = variables[variable_index]
            negative = parent * width + 2 * variable_index
            positive = negative + 1
            pairs = [
                (
                    effective_status(
                        table[negative].status, table[negative].seconds, seconds
                    ),
                    effective_status(
                        table[positive].status, table[positive].seconds, seconds
                    ),
                )
                for table in tables
            ]
            if len(set(pairs)) != 1 or pairs[0] not in ((20, 0), (0, 20)):
                continue
            unsat_index = negative if pairs[0][0] == 20 else positive
            parent_candidates.append(
                {
                    "variable": variable,
                    "contradictory_literal": -variable
                    if unsat_index == negative
                    else variable,
                    "worst_contradiction_seconds": max(
                        table[unsat_index].seconds for table in tables
                    ),
                }
            )
        candidates.append(parent_candidates)

    counts = [len(items) for items in candidates]
    return {
        "selection": {
            "path": str(selection_path.resolve()),
            "sha256": file_sha256(selection_path),
        },
        "recorded_screen_seconds": float(document["screen_seconds"]),
        "replay_screen_seconds": seconds,
        "parents": parents,
        "recorded_variables": len(variables),
        "eligible_variables": len(eligible),
        "candidate_counts": counts,
        "feasible": all(count > 0 for count in counts),
        "candidates": candidates,
    }


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("selection", type=Path, nargs="+")
    parser.add_argument("--screen-seconds", type=float, required=True)
    parser.add_argument(
        "--variables", help="optional comma-separated variables or ranges"
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    permitted = (
        set(parse_variables(arguments.variables, maximum_count=None))
        if arguments.variables
        else None
    )
    analyses = [
        analyze_selection(path.resolve(), arguments.screen_seconds, permitted)
        for path in arguments.selection
    ]
    counts = [
        count for analysis in analyses for count in analysis["candidate_counts"]
    ]
    document = {
        "schema": ANALYSIS_SCHEMA,
        "screen_seconds": arguments.screen_seconds,
        "variables": arguments.variables,
        "selections": analyses,
        "selection_count": len(analyses),
        "parent_count": len(counts),
        "minimum_candidates": min(counts),
        "all_parents_feasible": all(analysis["feasible"] for analysis in analyses),
    }
    if arguments.output is not None:
        atomic_json(arguments.output, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
