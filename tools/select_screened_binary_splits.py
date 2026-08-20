#!/usr/bin/env python3
"""Select reproducible one-sided binary splits from solver screen results."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__:
    from tools.generate_cartesian_cubes import parse_variables
    from tools.prove_materialized_cubes import file_sha256
    from tools.screen_cube_variables import extend_cubes, read_cubes
else:
    from generate_cartesian_cubes import parse_variables
    from prove_materialized_cubes import file_sha256
    from screen_cube_variables import extend_cubes, read_cubes


SCHEMA = "ramsey55.screened-binary-split-selection.v1"


@dataclass(frozen=True)
class ScreenResult:
    status: int
    seconds: float


def read_results(path: Path) -> list[ScreenResult]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].split("\t") != ["cube", "status", "seconds", "model"]:
        raise ValueError(f"invalid screen-result header in {path}")
    results: list[ScreenResult] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if len(fields) != 4 or int(fields[0]) != expected:
            raise ValueError(f"invalid screen-result row {expected} in {path}")
        status = int(fields[1])
        seconds = float(fields[2])
        if status not in (0, 10, 20) or seconds < 0:
            raise ValueError(f"invalid screen result at cube {expected} in {path}")
        results.append(ScreenResult(status, seconds))
    return results


def choose_splits(
    parents: list[list[int]],
    variables: list[int],
    screened: list[list[int]],
    result_tables: list[list[ScreenResult]],
) -> list[dict[str, Any]]:
    if not variables:
        raise ValueError("empty screen-variable list")
    expected = extend_cubes(parents, variables)
    if screened != expected:
        raise ValueError("screen cube file does not match parents and variables")
    if len(result_tables) < 2:
        raise ValueError("at least two solver-result tables are required")
    for source, results in enumerate(result_tables):
        if len(results) != len(screened):
            raise ValueError(f"screen-result source {source} count mismatch")
        for index, result in enumerate(results):
            if result.status == 10:
                raise ValueError(
                    f"SAT result at source {source} cube {index} requires investigation"
                )

    selections: list[dict[str, Any]] = []
    width = 2 * len(variables)
    for parent_index in range(len(parents)):
        candidates: list[tuple[float, int, dict[str, Any]]] = []
        for variable_index, variable in enumerate(variables):
            negative_index = parent_index * width + 2 * variable_index
            positive_index = negative_index + 1
            pairs = [
                (results[negative_index].status, results[positive_index].status)
                for results in result_tables
            ]
            if len(set(pairs)) != 1 or pairs[0] not in ((20, 0), (0, 20)):
                continue
            negative_is_unsat = pairs[0][0] == 20
            unsat_index = negative_index if negative_is_unsat else positive_index
            worst_seconds = max(
                results[unsat_index].seconds for results in result_tables
            )
            contradictory_literal = -variable if negative_is_unsat else variable
            candidates.append(
                (
                    worst_seconds,
                    variable,
                    {
                        "parent_index": parent_index,
                        "variable": variable,
                        "negative_cube_index": negative_index,
                        "positive_cube_index": positive_index,
                        "contradictory_literal": contradictory_literal,
                        "surviving_literal": -contradictory_literal,
                        "worst_contradiction_seconds": worst_seconds,
                        "solver_seconds": [
                            results[unsat_index].seconds for results in result_tables
                        ],
                    },
                )
            )
        if not candidates:
            raise ValueError(f"parent {parent_index} has no agreed one-sided split")
        selections.append(min(candidates, key=lambda item: (item[0], item[1]))[2])
    return selections


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", type=Path)
    parser.add_argument("variables", type=Path)
    parser.add_argument("screened", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("results", type=Path, nargs="+")
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")

    arguments.parents = arguments.parents.resolve()
    arguments.variables = arguments.variables.resolve()
    arguments.screened = arguments.screened.resolve()
    arguments.results = [path.resolve() for path in arguments.results]

    parents = read_cubes(arguments.parents)
    variables = parse_variables(
        arguments.variables.read_text(encoding="ascii").strip(), maximum_count=None
    )
    screened = read_cubes(arguments.screened)
    tables = [read_results(path) for path in arguments.results]
    selections = choose_splits(parents, variables, screened, tables)
    document = {
        "schema": SCHEMA,
        "parents": {
            "path": str(arguments.parents),
            "sha256": file_sha256(arguments.parents),
            "count": len(parents),
        },
        "variables": {
            "path": str(arguments.variables),
            "sha256": file_sha256(arguments.variables),
            "count": len(variables),
        },
        "screened_cubes": {
            "path": str(arguments.screened),
            "sha256": file_sha256(arguments.screened),
            "count": len(screened),
        },
        "result_sources": [
            {"path": str(path), "sha256": file_sha256(path)}
            for path in arguments.results
        ],
        "selections": selections,
        "split_variables": [item["variable"] for item in selections],
    }
    atomic_json(arguments.output, document)
    print(",".join(str(item["variable"]) for item in selections))


if __name__ == "__main__":
    main()
