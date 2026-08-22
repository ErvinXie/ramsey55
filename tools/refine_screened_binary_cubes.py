#!/usr/bin/env python3
"""Choose one solver-agreed one-sided binary split for every parent cube."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

if __package__:
    from tools.audit_binary_cube_refinement import HEADER
    from tools.generate_cartesian_cubes import parse_variables
    from tools.prove_materialized_cubes import file_sha256
    from tools.refine_selected_binary_cubes import refine
    from tools.screen_cube_variables import extend_cubes, read_cubes, write_cubes
    from tools.select_screened_binary_splits import (
        SCHEMA,
        ScreenResult,
        atomic_json,
        choose_splits,
        read_results,
    )
else:
    from audit_binary_cube_refinement import HEADER
    from generate_cartesian_cubes import parse_variables
    from prove_materialized_cubes import file_sha256
    from refine_selected_binary_cubes import refine
    from screen_cube_variables import extend_cubes, read_cubes, write_cubes
    from select_screened_binary_splits import (
        SCHEMA,
        ScreenResult,
        atomic_json,
        choose_splits,
        read_results,
    )


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="ascii", newline="\n")
    temporary.replace(path)


def available_variables(
    parents: list[list[int]], candidates: list[int]
) -> list[int]:
    assigned = {abs(literal) for cube in parents for literal in cube}
    return [variable for variable in candidates if variable not in assigned]


def primary_candidate_variables(
    parents: list[list[int]],
    variables: list[int],
    screened: list[list[int]],
    results: list[ScreenResult],
) -> list[int]:
    """Return variables with a one-sided UNSAT report for any parent."""

    if screened != extend_cubes(parents, variables):
        raise ValueError(
            "primary screen cube file does not match parents and variables"
        )
    if len(results) != len(screened):
        raise ValueError("primary screen-result count mismatch")
    width = 2 * len(variables)
    selected: set[int] = set()
    for parent_index in range(len(parents)):
        for variable_index, variable in enumerate(variables):
            negative_index = parent_index * width + 2 * variable_index
            positive_index = negative_index + 1
            negative = results[negative_index]
            positive = results[positive_index]
            pair = (negative.status, positive.status)
            if 10 in pair:
                raise ValueError(
                    f"SAT result at primary parent {parent_index} "
                    f"variable {variable} requires investigation"
                )
            if pair == (20, 20):
                raise ValueError(
                    f"both sides UNSAT at primary parent {parent_index} "
                    f"variable {variable}"
                )
            if pair in ((20, 0), (0, 20)):
                selected.add(variable)
    return [variable for variable in variables if variable in selected]


def subset_results(
    parents: list[list[int]],
    variables: list[int],
    selected: list[int],
    results: list[ScreenResult],
) -> list[ScreenResult]:
    """Project a complete screen table onto a variable subsequence."""

    positions = {variable: index for index, variable in enumerate(variables)}
    if len(positions) != len(variables) or any(
        variable not in positions for variable in selected
    ):
        raise ValueError("selected variables are not a subset of the screen")
    if len(set(selected)) != len(selected):
        raise ValueError("selected variables contain duplicates")
    width = 2 * len(variables)
    if len(results) != len(parents) * width:
        raise ValueError("screen-result count mismatch")
    output: list[ScreenResult] = []
    for parent_index in range(len(parents)):
        for variable in selected:
            negative = parent_index * width + 2 * positions[variable]
            output.extend(results[negative : negative + 2])
    return output


def write_screen_results(path: Path, results: list[ScreenResult]) -> None:
    atomic_text(
        path,
        "cube\tstatus\tseconds\tmodel\n"
        + "".join(
            f"{index}\t{result.status}\t{result.seconds:.6f}\t\n"
            for index, result in enumerate(results)
        ),
    )


def artifact_prefix(results: Path) -> Path:
    suffix = "-refine.tsv"
    if not results.name.endswith(suffix):
        raise ValueError("refinement result path must end in -refine.tsv")
    return results.with_name(results.name[: -len(suffix)])


def run_screen(
    tool: Path,
    formula: Path,
    cubes: Path,
    seconds: float,
    jobs: int,
    output: Path,
    log: Path,
    solver: Path,
    solver_arguments: list[str],
) -> None:
    command = [
        sys.executable,
        str(tool),
        str(formula),
        str(cubes),
        str(seconds),
        str(jobs),
        str(output),
        str(solver),
        *solver_arguments,
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(
            f"screen solver {solver} failed with {completed.returncode}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("formula", type=Path)
    parser.add_argument("parents", type=Path)
    parser.add_argument("jobs", type=int)
    parser.add_argument("children", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--variables", required=True)
    parser.add_argument("--screen-solver", type=Path, action="append", default=[])
    parser.add_argument("--screen-solver-argument", action="append", default=[])
    parser.add_argument("--screen-seconds", type=float, default=1.0)
    parser.add_argument("--screen-jobs", type=int)
    parser.add_argument(
        "--staged-screening",
        action="store_true",
        help=(
            "run the first solver on every variable and the second only on "
            "the first solver's one-sided candidates"
        ),
    )
    arguments = parser.parse_args()
    if len(arguments.screen_solver) < 2:
        parser.error("at least two --screen-solver values are required")
    if arguments.staged_screening and len(arguments.screen_solver) != 2:
        parser.error("staged screening requires exactly two screen solvers")
    if arguments.jobs <= 0 or arguments.screen_seconds <= 0:
        parser.error("jobs and screen-seconds must be positive")
    screen_jobs = arguments.screen_jobs or arguments.jobs
    if screen_jobs <= 0:
        parser.error("screen-jobs must be positive")

    formula = arguments.formula.resolve()
    parents_path = arguments.parents.resolve()
    children_path = arguments.children.resolve()
    results_path = arguments.results.resolve()
    solvers = [path.resolve() for path in arguments.screen_solver]
    for path in (formula, parents_path, *solvers):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")
    prefix = artifact_prefix(results_path)
    variables_path = prefix.with_name(prefix.name + "-screen-variables.txt")
    screened_path = prefix.with_name(prefix.name + "-screen.icnf")
    selection_path = prefix.with_name(prefix.name + "-screen-selection.json")
    selection_log = prefix.with_name(prefix.name + "-screen-selection.log")
    solver_outputs = [
        prefix.with_name(prefix.name + f"-screen-solver-{index}.tsv")
        for index in range(len(solvers))
    ]
    solver_logs = [output.with_suffix(".log") for output in solver_outputs]
    primary_variables_path = prefix.with_name(
        prefix.name + "-primary-screen-variables.txt"
    )
    primary_screened_path = prefix.with_name(prefix.name + "-primary-screen.icnf")
    primary_output = prefix.with_name(prefix.name + "-primary-screen-solver.tsv")
    primary_log = primary_output.with_suffix(".log")
    outputs = (
        children_path,
        results_path,
        variables_path,
        screened_path,
        selection_path,
        selection_log,
        *solver_outputs,
        *solver_logs,
    )
    if arguments.staged_screening:
        outputs += (
            primary_variables_path,
            primary_screened_path,
            primary_output,
            primary_log,
        )
    existing = [path for path in outputs if path.exists()]
    if existing:
        parser.error(f"refusing to overwrite {existing[0]}")

    parents = read_cubes(parents_path)
    candidates = parse_variables(arguments.variables, maximum_count=None)
    variables = available_variables(parents, candidates)
    if not variables:
        raise ValueError("no unassigned screen variables remain")
    solve_tool = Path(__file__).with_name("solve_external_cubes.py")
    staged_primary: dict[str, object] | None = None
    if arguments.staged_screening:
        primary_variables = list(variables)
        atomic_text(primary_variables_path, ",".join(map(str, variables)) + "\n")
        primary_screened = extend_cubes(parents, variables)
        write_cubes(primary_screened_path, primary_screened)
        run_screen(
            solve_tool,
            formula,
            primary_screened_path,
            arguments.screen_seconds,
            screen_jobs,
            primary_output,
            primary_log,
            solvers[0],
            arguments.screen_solver_argument,
        )
        primary_table = read_results(primary_output)
        variables = primary_candidate_variables(
            parents, variables, primary_screened, primary_table
        )
        if not variables:
            raise ValueError("primary screen found no one-sided candidate")
        atomic_text(variables_path, ",".join(map(str, variables)) + "\n")
        screened = extend_cubes(parents, variables)
        write_cubes(screened_path, screened)
        write_screen_results(
            solver_outputs[0],
            subset_results(
                parents,
                primary_variables,
                variables,
                primary_table,
            ),
        )
        atomic_text(
            solver_logs[0],
            "projected from " + str(primary_output) + "\n",
        )
        run_screen(
            solve_tool,
            formula,
            screened_path,
            arguments.screen_seconds,
            screen_jobs,
            solver_outputs[1],
            solver_logs[1],
            solvers[1],
            arguments.screen_solver_argument,
        )
        staged_primary = {
            "variables": {
                "path": str(primary_variables_path),
                "sha256": file_sha256(primary_variables_path),
                "count": len(primary_variables),
            },
            "screened_cubes": {
                "path": str(primary_screened_path),
                "sha256": file_sha256(primary_screened_path),
                "count": len(primary_screened),
            },
            "solver": {
                "path": str(solvers[0]),
                "sha256": file_sha256(solvers[0]),
                "arguments": arguments.screen_solver_argument,
                "results": str(primary_output),
                "results_sha256": file_sha256(primary_output),
                "log": str(primary_log),
                "log_sha256": file_sha256(primary_log),
            },
        }
    else:
        atomic_text(variables_path, ",".join(map(str, variables)) + "\n")
        screened = extend_cubes(parents, variables)
        write_cubes(screened_path, screened)
        with concurrent.futures.ThreadPoolExecutor(len(solvers)) as executor:
            futures = [
                executor.submit(
                    run_screen,
                    solve_tool,
                    formula,
                    screened_path,
                    arguments.screen_seconds,
                    screen_jobs,
                    output,
                    log,
                    solver,
                    arguments.screen_solver_argument,
                )
                for solver, output, log in zip(
                    solvers, solver_outputs, solver_logs, strict=True
                )
            ]
            for future in futures:
                future.result()

    tables = [read_results(path) for path in solver_outputs]
    selections = choose_splits(parents, variables, screened, tables)
    selection = {
        "schema": SCHEMA,
        "formula": {"path": str(formula), "sha256": file_sha256(formula)},
        "parents": {
            "path": str(parents_path),
            "sha256": file_sha256(parents_path),
            "count": len(parents),
        },
        "variables": {
            "path": str(variables_path),
            "sha256": file_sha256(variables_path),
            "count": len(variables),
        },
        "screened_cubes": {
            "path": str(screened_path),
            "sha256": file_sha256(screened_path),
            "count": len(screened),
        },
        "screen_seconds": arguments.screen_seconds,
        "screen_jobs": screen_jobs,
        "screen_solvers": [
            {
                "path": str(solver),
                "sha256": file_sha256(solver),
                "arguments": arguments.screen_solver_argument,
                "results": str(output),
                "results_sha256": file_sha256(output),
                "log": str(log),
                "log_sha256": file_sha256(log),
            }
            for solver, output, log in zip(
                solvers, solver_outputs, solver_logs, strict=True
            )
        ],
        "selections": selections,
        "split_variables": [item["variable"] for item in selections],
    }
    if staged_primary is not None:
        selection["staged_primary_screen"] = staged_primary
    atomic_json(selection_path, selection)
    atomic_text(
        selection_log,
        json.dumps(
            {
                "parents": len(parents),
                "screened_cubes": len(screened),
                "split_variables": selection["split_variables"],
            },
            sort_keys=True,
        )
        + "\n",
    )

    splits = [int(item["variable"]) for item in selections]
    selected_children = refine(parents, splits)
    write_cubes(children_path, selected_children)
    atomic_text(
        results_path,
        "\t".join(HEADER)
        + "\n"
        + "".join(
            f"{index}\t0\t{split}\t0.000000\t\n"
            for index, split in enumerate(splits)
        ),
    )
    print(json.dumps(selection["split_variables"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
