#!/usr/bin/env python3
"""Split only UNKNOWN cubes from a solve_cadical_cubes result table."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path


def read_cubes(path: Path) -> list[list[int]]:
    cubes: list[list[int]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("c"):
            continue
        fields = line.split()
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError("invalid cube line")
        cubes.append([int(field) for field in fields[1:-1]])
    return cubes


def read_statuses(path: Path) -> list[int]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "cube\tstatus\tseconds\tmodel":
        raise ValueError("invalid cube result header")
    statuses: list[int] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if int(fields[0]) != expected:
            raise ValueError("cube result indices are not consecutive")
        statuses.append(int(fields[1]))
    return statuses


def parse_variables(text: str) -> list[int]:
    if text == "none":
        return []
    variables: list[int] = []
    for field in text.split(","):
        if "-" in field:
            start_text, stop_text = field.split("-", 1)
            variables.extend(range(int(start_text), int(stop_text) + 1))
        else:
            variables.append(int(field))
    if any(variable <= 0 for variable in variables):
        raise ValueError("variables must be positive")
    if len(set(variables)) != len(variables):
        raise ValueError("variables must be distinct")
    return variables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("variables")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--sample",
        type=int,
        help="evenly sample this many UNKNOWN parents for a branching pilot",
    )
    parser.add_argument(
        "--min-from",
        help="only emit new bit vectors lexicographically at least these assigned variables",
    )
    arguments = parser.parse_args()
    cubes = read_cubes(arguments.cubes)
    statuses = read_statuses(arguments.results)
    variables = parse_variables(arguments.variables)
    minimum_variables = (
        parse_variables(arguments.min_from) if arguments.min_from else []
    )
    if minimum_variables and len(minimum_variables) != len(variables):
        raise ValueError("--min-from and refinement ranges must have equal length")
    if len(cubes) != len(statuses):
        raise ValueError("cube and result counts differ")
    if any(status == 10 for status in statuses):
        raise ValueError("refusing to refine after a SAT result")

    unknown = [cube for cube, status in zip(cubes, statuses, strict=True) if status == 0]
    if arguments.sample is not None:
        if arguments.sample <= 0 or arguments.sample > len(unknown):
            raise ValueError("sample size must be between 1 and the UNKNOWN count")
        unknown = [
            unknown[index * len(unknown) // arguments.sample]
            for index in range(arguments.sample)
        ]
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    emitted = 0
    with temporary.open("w", encoding="ascii") as output:
        for cube in unknown:
            assigned = {abs(literal) for literal in cube}
            if assigned.intersection(variables):
                raise ValueError("a refinement variable is already assigned")
            values_by_variable = {
                abs(literal): literal > 0 for literal in cube
            }
            try:
                minimum = tuple(
                    values_by_variable[variable]
                    for variable in minimum_variables
                )
            except KeyError as error:
                raise ValueError("a --min-from variable is not assigned") from error
            for values in itertools.product((False, True), repeat=len(variables)):
                if minimum_variables and values < minimum:
                    continue
                extension = [
                    variable if value else -variable
                    for variable, value in zip(variables, values, strict=True)
                ]
                output.write(
                    "a " + " ".join(map(str, cube + extension)) + " 0\n"
                )
                emitted += 1
    temporary.replace(arguments.output)
    print(
        f"refined {len(unknown)} unknown cubes into "
        f"{emitted} cubes"
    )


if __name__ == "__main__":
    main()
