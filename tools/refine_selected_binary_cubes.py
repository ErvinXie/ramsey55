#!/usr/bin/env python3
"""Split each parent cube on one explicitly selected DIMACS variable."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from tools.audit_binary_cube_refinement import HEADER
    from tools.screen_cube_variables import read_cubes
else:
    from audit_binary_cube_refinement import HEADER
    from screen_cube_variables import read_cubes


def parse_splits(text: str) -> list[int]:
    splits = [int(field) for field in text.split(",")]
    if not splits or any(split <= 0 for split in splits):
        raise ValueError("split variables must be positive")
    return splits


def refine(cubes: list[list[int]], splits: list[int]) -> list[list[int]]:
    if len(cubes) != len(splits):
        raise ValueError("one split variable is required per parent cube")
    children: list[list[int]] = []
    for parent_index, (cube, split) in enumerate(
        zip(cubes, splits, strict=True)
    ):
        if split in {abs(literal) for literal in cube}:
            raise ValueError(
                f"parent {parent_index} already assigns split variable {split}"
            )
        children.extend((cube + [split], cube + [-split]))
    return children


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="ascii", newline="\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", type=Path)
    parser.add_argument("splits", help="one comma-separated variable per parent")
    parser.add_argument("children", type=Path)
    parser.add_argument("results", type=Path)
    arguments = parser.parse_args()
    for output in (arguments.children, arguments.results):
        if output.exists():
            parser.error(f"refusing to overwrite {output}")

    cubes = read_cubes(arguments.parents)
    splits = parse_splits(arguments.splits)
    children = refine(cubes, splits)
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
    print(f"refined {len(cubes)} parents into {len(children)} children")


if __name__ == "__main__":
    main()
