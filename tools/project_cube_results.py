#!/usr/bin/env python3
"""Project a cube result table onto an exact ordered subset of its cubes."""

from __future__ import annotations

import argparse
from pathlib import Path

from adopt_cartesian_refinement import read_cubes
from merge_cube_results import Row, read_results, write_results


def project_results(
    source_cubes: list[list[int]],
    source_results: list[Row],
    target_cubes: list[list[int]],
) -> list[Row]:
    if len(source_cubes) != len(source_results):
        raise ValueError("source cube and result counts differ")
    keyed = {tuple(cube): result for cube, result in zip(source_cubes, source_results)}
    if len(keyed) != len(source_cubes):
        raise ValueError("source cubes are not unique")
    if len(set(map(tuple, target_cubes))) != len(target_cubes):
        raise ValueError("target cubes are not unique")
    try:
        return [keyed[tuple(cube)] for cube in target_cubes]
    except KeyError as error:
        raise ValueError("a target cube is absent from the source") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_cubes", type=Path)
    parser.add_argument("source_results", type=Path)
    parser.add_argument("target_cubes", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    source_cubes = read_cubes(arguments.source_cubes)
    source_results = read_results(arguments.source_results)
    target_cubes = read_cubes(arguments.target_cubes)
    projected = project_results(source_cubes, source_results, target_cubes)
    write_results(arguments.output, projected)
    print(
        f"projected {len(projected)}/{len(source_results)} rows: "
        f"closed={sum(row.status == 20 for row in projected)} "
        f"unknown={sum(row.status == 0 for row in projected)}"
    )


if __name__ == "__main__":
    main()
