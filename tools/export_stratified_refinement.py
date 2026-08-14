#!/usr/bin/env python3
"""Evenly sample frontier strata and emit complete Cartesian refinements."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path

from generate_cartesian_cubes import parse_variables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("variables")
    parser.add_argument("output", type=Path)
    parser.add_argument("--per-stratum", type=int, default=4)
    parser.add_argument("--primary-through", type=int, default=432)
    parser.add_argument("--min-primary", type=int, default=0)
    parser.add_argument("--max-primary", type=int)
    arguments = parser.parse_args()
    if (
        arguments.per_stratum <= 0
        or arguments.primary_through <= 0
        or arguments.min_primary < 0
        or (
            arguments.max_primary is not None
            and arguments.max_primary < arguments.min_primary
        )
    ):
        raise ValueError("sampling and primary cutoff must be positive")
    variables = parse_variables(arguments.variables)
    state = json.loads(arguments.state.read_text(encoding="utf-8"))
    strata: dict[int, list[list[int]]] = defaultdict(list)
    for cube in state["frontier"]:
        primary = sum(abs(literal) <= arguments.primary_through for literal in cube)
        if primary < arguments.min_primary:
            continue
        if arguments.max_primary is not None and primary > arguments.max_primary:
            continue
        strata[primary].append(cube)
    if not strata:
        raise ValueError("no frontier stratum matches the selection")
    selected: list[list[int]] = []
    selection_counts: dict[int, int] = {}
    for primary, cubes in sorted(strata.items()):
        count = min(arguments.per_stratum, len(cubes))
        sample = [cubes[index * len(cubes) // count] for index in range(count)]
        if any(
            {abs(literal) for literal in cube}.intersection(variables)
            for cube in sample
        ):
            raise ValueError("a refinement variable is already assigned")
        selected.extend(sample)
        selection_counts[primary] = count
    assignments = [
        [
            variable if value else -variable
            for variable, value in zip(variables, values, strict=True)
        ]
        for values in itertools.product((False, True), repeat=len(variables))
    ]
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        for cube in selected:
            for assignment in assignments:
                output.write("a " + " ".join(map(str, cube + assignment)) + " 0\n")
    temporary.replace(arguments.output)
    print(
        f"selected={selection_counts} parents={len(selected)} "
        f"children={len(selected) * len(assignments)}"
    )


if __name__ == "__main__":
    main()
