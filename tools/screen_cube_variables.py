#!/usr/bin/env python3
"""Extend every input cube by both polarities of selected variables."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from tools.generate_cartesian_cubes import parse_variables
else:
    from generate_cartesian_cubes import parse_variables


def read_cubes(path: Path) -> list[list[int]]:
    cubes: list[list[int]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("c"):
            continue
        fields = line.split()
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError(f"invalid cube line in {path}")
        cube = [int(field) for field in fields[1:-1]]
        if not cube or any(literal == 0 for literal in cube):
            raise ValueError(f"invalid cube literals in {path}")
        if len({abs(literal) for literal in cube}) != len(cube):
            raise ValueError(f"repeated cube variable in {path}")
        cubes.append(cube)
    if not cubes:
        raise ValueError(f"empty cube file {path}")
    return cubes


def extend_cubes(cubes: list[list[int]], variables: list[int]) -> list[list[int]]:
    output: list[list[int]] = []
    for parent_index, cube in enumerate(cubes):
        assigned = {abs(literal) for literal in cube}
        overlap = assigned.intersection(variables)
        if overlap:
            raise ValueError(
                f"parent {parent_index} already assigns screened variables "
                f"{sorted(overlap)}"
            )
        for variable in variables:
            output.append(cube + [-variable])
            output.append(cube + [variable])
    return output


def write_cubes(path: Path, cubes: list[list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as stream:
        for cube in cubes:
            stream.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("variables", help="comma-separated variables or ranges")
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    cubes = read_cubes(arguments.cubes)
    # This operation grows linearly in the number of variables.  The default
    # parser limit protects the Cartesian generator, whose output grows as
    # 2^n, and does not apply here.
    variables = parse_variables(arguments.variables, maximum_count=None)
    output = extend_cubes(cubes, variables)
    write_cubes(arguments.output, output)
    print(
        f"screened {len(variables)} variables on {len(cubes)} parents: "
        f"wrote {len(output)} children"
    )


if __name__ == "__main__":
    main()
