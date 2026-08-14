#!/usr/bin/env python3
"""Choose primary variables per frontier parent from assigned counter context."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path


def read_adjacency(
    cnf: Path, ramsey_clauses: int, primary_through: int
) -> dict[int, set[int]]:
    clauses: list[list[int]] = []
    for line in cnf.read_text(encoding="ascii").splitlines():
        if not line or line[0] in "cp":
            continue
        clauses.append([int(field) for field in line.split()[:-1]])
    if ramsey_clauses < 0 or ramsey_clauses > len(clauses):
        raise ValueError("invalid Ramsey clause count")
    adjacency: dict[int, set[int]] = defaultdict(set)
    for clause in clauses[ramsey_clauses:]:
        primary = {abs(literal) for literal in clause if abs(literal) <= primary_through}
        auxiliary = {abs(literal) for literal in clause if abs(literal) > primary_through}
        for variable in primary:
            adjacency[variable].update(auxiliary)
    if set(adjacency) != set(range(1, primary_through + 1)):
        raise ValueError("degree clauses do not cover every primary variable")
    return adjacency


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("state", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--ramsey-clauses", type=int, required=True)
    parser.add_argument("--primary-through", type=int, default=432)
    parser.add_argument("--split", type=int, default=4)
    parser.add_argument("--primary-count", type=int)
    parser.add_argument("--sample", type=int)
    arguments = parser.parse_args()
    if arguments.primary_through <= 0 or arguments.split <= 0 or arguments.split > 16:
        raise ValueError("invalid primary cutoff or split width")
    adjacency = read_adjacency(
        arguments.cnf, arguments.ramsey_clauses, arguments.primary_through
    )
    state_bytes = arguments.state.read_bytes()
    state = json.loads(state_bytes)
    parent_indices = [
        index
        for index, cube in enumerate(state["frontier"])
        if arguments.primary_count is None
        or sum(abs(literal) <= arguments.primary_through for literal in cube)
        == arguments.primary_count
    ]
    if arguments.sample is not None:
        if arguments.sample <= 0 or arguments.sample > len(parent_indices):
            raise ValueError("invalid sample size")
        parent_indices = [
            parent_indices[index * len(parent_indices) // arguments.sample]
            for index in range(arguments.sample)
        ]
    if not parent_indices:
        raise ValueError("selection is empty")
    entries: list[dict] = []
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary_output.open("w", encoding="ascii") as output:
        for parent_index in parent_indices:
            cube = state["frontier"][parent_index]
            assigned = {abs(literal) for literal in cube}
            auxiliary = {variable for variable in assigned if variable > arguments.primary_through}
            candidates = [
                variable
                for variable in range(1, arguments.primary_through + 1)
                if variable not in assigned
            ]
            candidates.sort(
                key=lambda variable: (
                    -len(adjacency[variable].intersection(auxiliary)),
                    variable,
                )
            )
            variables = candidates[: arguments.split]
            if len(variables) != arguments.split:
                raise ValueError("not enough unassigned primary variables")
            entries.append(
                {
                    "parent_index": parent_index,
                    "scores": [
                        len(adjacency[variable].intersection(auxiliary))
                        for variable in variables
                    ],
                    "variables": variables,
                }
            )
            for values in itertools.product((False, True), repeat=len(variables)):
                extension = [
                    variable if value else -variable
                    for variable, value in zip(variables, values, strict=True)
                ]
                output.write("a " + " ".join(map(str, cube + extension)) + " 0\n")
    temporary_output.replace(arguments.output)
    manifest = {
        "cnf": str(arguments.cnf),
        "cnf_sha256": hashlib.sha256(arguments.cnf.read_bytes()).hexdigest(),
        "entries": entries,
        "frontier_size": len(state["frontier"]),
        "primary_through": arguments.primary_through,
        "ramsey_clauses": arguments.ramsey_clauses,
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
    }
    temporary_selection = arguments.selection.with_suffix(
        arguments.selection.suffix + ".tmp"
    )
    temporary_selection.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_selection.replace(arguments.selection)
    print(
        f"selected {len(entries)}/{len(state['frontier'])} parents; "
        f"emitted {len(entries) * (1 << arguments.split)} children"
    )


if __name__ == "__main__":
    main()
