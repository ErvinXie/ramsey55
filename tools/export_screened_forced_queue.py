#!/usr/bin/env python3
"""Export every reproducible one-sided split found by solver screens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.generate_cartesian_cubes import parse_variables
    from tools.prove_materialized_cubes import file_sha256
    from tools.screen_cube_variables import extend_cubes, read_cubes
    from tools.select_screened_binary_splits import ScreenResult, read_results
else:
    from generate_cartesian_cubes import parse_variables
    from prove_materialized_cubes import file_sha256
    from screen_cube_variables import extend_cubes, read_cubes
    from select_screened_binary_splits import ScreenResult, read_results


SCHEMA = "ramsey55.screened-forced-variable-queue.v1"


def rank_forced_splits(
    parents: list[list[int]],
    variables: list[int],
    screened: list[list[int]],
    result_tables: list[list[ScreenResult]],
    mode: str,
) -> list[list[dict[str, Any]]]:
    if mode not in ("agreement", "union"):
        raise ValueError("mode must be agreement or union")
    if not variables or not result_tables:
        raise ValueError("variables and result tables must be nonempty")
    expected = extend_cubes(parents, variables)
    if screened != expected:
        raise ValueError("screen cube file does not match parents and variables")
    for source, results in enumerate(result_tables):
        if len(results) != len(screened):
            raise ValueError(f"screen-result source {source} count mismatch")
        if any(result.status == 10 for result in results):
            raise ValueError(f"SAT result at source {source} requires investigation")

    width = 2 * len(variables)
    output: list[list[dict[str, Any]]] = []
    for parent_index in range(len(parents)):
        candidates: list[tuple[float, int, dict[str, Any]]] = []
        for variable_index, variable in enumerate(variables):
            negative_index = parent_index * width + 2 * variable_index
            positive_index = negative_index + 1
            reports: list[tuple[int, float, int]] = []
            for source, results in enumerate(result_tables):
                negative = results[negative_index]
                positive = results[positive_index]
                pair = (negative.status, positive.status)
                if pair == (20, 20):
                    raise ValueError(
                        f"both sides UNSAT at parent {parent_index} "
                        f"variable {variable} source {source}"
                    )
                if pair == (20, 0):
                    reports.append((-variable, negative.seconds, source))
                elif pair == (0, 20):
                    reports.append((variable, positive.seconds, source))
            if not reports:
                continue
            directions = {literal for literal, _, _ in reports}
            if len(directions) != 1:
                raise ValueError(
                    f"one-sided direction disagreement at parent {parent_index} "
                    f"variable {variable}"
                )
            if mode == "agreement" and len(reports) != len(result_tables):
                continue
            contradictory = next(iter(directions))
            seconds = [value for _, value, _ in reports]
            rank_seconds = max(seconds) if mode == "agreement" else min(seconds)
            item = {
                "parent_index": parent_index,
                "variable": variable,
                "contradictory_literal": contradictory,
                "surviving_literal": -contradictory,
                "rank_seconds": rank_seconds,
                "source_indices": [source for _, _, source in reports],
                "source_seconds": seconds,
            }
            candidates.append((rank_seconds, variable, item))
        candidates.sort(key=lambda item: (item[0], item[1]))
        output.append([item for _, _, item in candidates])
    return output


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", type=Path)
    parser.add_argument("variables", type=Path)
    parser.add_argument("screened", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--mode", choices=("agreement", "union"), default="agreement")
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")

    parents = read_cubes(arguments.parents)
    variables = parse_variables(
        arguments.variables.read_text(encoding="ascii").strip(), maximum_count=None
    )
    screened = read_cubes(arguments.screened)
    tables = [read_results(path) for path in arguments.results]
    ranked = rank_forced_splits(
        parents, variables, screened, tables, arguments.mode
    )
    document = {
        "schema": SCHEMA,
        "mode": arguments.mode,
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
        "parents_ranked": [
            {
                "parent_index": index,
                "candidate_count": len(candidates),
                "queue": [item["variable"] for item in candidates],
                "candidates": candidates,
            }
            for index, candidates in enumerate(ranked)
        ],
        "candidate_count": sum(map(len, ranked)),
    }
    atomic_json(arguments.output, document)
    print(",".join(str(len(candidates)) for candidates in ranked))


if __name__ == "__main__":
    main()
