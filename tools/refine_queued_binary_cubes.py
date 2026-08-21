#!/usr/bin/env python3
"""Split each parent on its first still-unassigned queued variable."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from tools.audit_binary_cube_refinement import HEADER
    from tools.generate_cartesian_cubes import parse_variables
    from tools.refine_selected_binary_cubes import refine
    from tools.screen_cube_variables import read_cubes
else:
    from audit_binary_cube_refinement import HEADER
    from generate_cartesian_cubes import parse_variables
    from refine_selected_binary_cubes import refine
    from screen_cube_variables import read_cubes


def choose_splits(parents: list[list[int]], queues: list[list[int]]) -> list[int]:
    if len(parents) != len(queues):
        raise ValueError("one variable queue is required per parent")
    splits = []
    for index, (parent, queue) in enumerate(zip(parents, queues, strict=True)):
        assigned = {abs(literal) for literal in parent}
        split = next((variable for variable in queue if variable not in assigned), None)
        if split is None:
            raise ValueError(f"parent {index} exhausted its variable queue")
        splits.append(split)
    return splits


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="ascii", newline="\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("formula", type=Path)
    parser.add_argument("parents", type=Path)
    parser.add_argument("jobs", type=int)
    parser.add_argument("children", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument(
        "--variables",
        action="append",
        required=True,
        help="one comma-separated variable/range queue per parent",
    )
    arguments = parser.parse_args()
    if not arguments.formula.is_file() or arguments.jobs <= 0:
        parser.error("formula must exist and jobs must be positive")
    for output in (arguments.children, arguments.results):
        if output.exists():
            parser.error(f"refusing to overwrite {output}")

    parents = read_cubes(arguments.parents)
    queues = [
        parse_variables(value, maximum_count=None) for value in arguments.variables
    ]
    splits = choose_splits(parents, queues)
    children = refine(parents, splits)
    atomic_text(
        arguments.children,
        "".join(f"a {' '.join(map(str, cube))} 0\n" for cube in children),
    )
    atomic_text(
        arguments.results,
        "\t".join(HEADER)
        + "\n"
        + "".join(
            f"{index}\t0\t{split}\t0.000000\t\n"
            for index, split in enumerate(splits)
        ),
    )
    print(",".join(map(str, splits)))


if __name__ == "__main__":
    main()
