#!/usr/bin/env python3
"""Export a complete Cartesian refinement for selected frontier strata."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from generate_cartesian_cubes import parse_variables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("variables")
    parser.add_argument("output", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--primary-through", type=int, default=432)
    parser.add_argument("--min-primary", type=int, default=1)
    parser.add_argument("--max-primary", type=int)
    arguments = parser.parse_args()
    if arguments.primary_through <= 0 or arguments.min_primary < 0:
        raise ValueError("invalid primary selection bounds")
    if (
        arguments.max_primary is not None
        and arguments.max_primary < arguments.min_primary
    ):
        raise ValueError("--max-primary is below --min-primary")
    variables = parse_variables(arguments.variables)
    state_bytes = arguments.state.read_bytes()
    state = json.loads(state_bytes)
    selected: list[int] = []
    for index, cube in enumerate(state["frontier"]):
        primary = sum(abs(literal) <= arguments.primary_through for literal in cube)
        if primary < arguments.min_primary:
            continue
        if arguments.max_primary is not None and primary > arguments.max_primary:
            continue
        if {abs(literal) for literal in cube}.intersection(variables):
            raise ValueError("a refinement variable is already assigned")
        selected.append(index)
    if not selected:
        raise ValueError("selection is empty")
    assignments = [
        [
            variable if value else -variable
            for variable, value in zip(variables, values, strict=True)
        ]
        for values in itertools.product((False, True), repeat=len(variables))
    ]
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary_output.open("w", encoding="ascii") as output:
        for index in selected:
            for assignment in assignments:
                output.write(
                    "a "
                    + " ".join(map(str, state["frontier"][index] + assignment))
                    + " 0\n"
                )
    temporary_output.replace(arguments.output)
    manifest = {
        "frontier_size": len(state["frontier"]),
        "parent_indices": selected,
        "primary_through": arguments.primary_through,
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "variables": variables,
    }
    temporary_selection = arguments.selection.with_suffix(
        arguments.selection.suffix + ".tmp"
    )
    temporary_selection.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_selection.replace(arguments.selection)
    print(
        f"selected {len(selected)}/{len(state['frontier'])} parents; "
        f"emitted {len(selected) * len(assignments)} children"
    )


if __name__ == "__main__":
    main()
