#!/usr/bin/env python3
"""Atomically adopt only useful complete Cartesian frontier refinements."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_variables(text: str) -> list[int]:
    variables: list[int] = []
    for field in text.split(","):
        if "-" in field:
            start_text, stop_text = field.split("-", 1)
            start, stop = int(start_text), int(stop_text)
            if start > stop:
                raise ValueError("a variable range must be increasing")
            variables.extend(range(start, stop + 1))
        else:
            variables.append(int(field))
    if not variables or any(variable <= 0 for variable in variables):
        raise ValueError("variables must be positive")
    if len(set(variables)) != len(variables):
        raise ValueError("variables must be distinct")
    if len(variables) > 20:
        raise ValueError("refinement is too wide")
    return variables


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
        raise ValueError("invalid result header")
    statuses: list[int] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if int(fields[0]) != expected:
            raise ValueError("non-consecutive result index")
        status = int(fields[1])
        if status not in (0, 10, 20):
            raise ValueError("unexpected solver status")
        statuses.append(status)
    return statuses


def refine_state(
    state: dict,
    cubes: list[list[int]],
    statuses: list[int],
    variables: list[int],
    max_remaining: int,
) -> tuple[dict, list[int], int]:
    if max_remaining < 0:
        raise ValueError("--max-remaining must be nonnegative")
    if any(status == 10 for status in statuses):
        raise ValueError("SAT candidate present; refusing to adopt")
    parents: list[list[int]] = state["frontier"]
    width = 1 << len(variables)
    if len(cubes) != len(parents) * width or len(statuses) != len(cubes):
        raise ValueError("refinement size does not match the frontier")
    assignments = [
        [
            variable if value else -variable
            for variable, value in zip(variables, values, strict=True)
        ]
        for values in itertools.product((False, True), repeat=len(variables))
    ]
    frontier: list[list[int]] = []
    adopted: list[int] = []
    integrated_closed = 0
    for parent_index, parent in enumerate(parents):
        if {abs(literal) for literal in parent}.intersection(variables):
            raise ValueError("a refinement variable is already assigned")
        start = parent_index * width
        group = cubes[start : start + width]
        expected = [parent + assignment for assignment in assignments]
        if group != expected:
            raise ValueError(f"cube group {parent_index} is not a complete Cartesian split")
        group_statuses = statuses[start : start + width]
        remaining = [
            cube for cube, status in zip(group, group_statuses, strict=True) if status == 0
        ]
        if len(remaining) <= max_remaining:
            adopted.append(parent_index)
            frontier.extend(remaining)
            integrated_closed += group_statuses.count(20)
        else:
            frontier.append(parent)
    updated = dict(state)
    updated["round"] = int(state["round"]) + 1
    updated["frontier"] = frontier
    updated["closed"] = int(state["closed"]) + integrated_closed
    return updated, adopted, integrated_closed


def refine_selected_state(
    state: dict,
    cubes: list[list[int]],
    statuses: list[int],
    variables: list[int],
    max_remaining: int,
    parent_indices: list[int],
) -> tuple[dict, list[int], int]:
    if max_remaining < 0:
        raise ValueError("--max-remaining must be nonnegative")
    if any(status == 10 for status in statuses):
        raise ValueError("SAT candidate present; refusing to adopt")
    parents: list[list[int]] = state["frontier"]
    if parent_indices != sorted(set(parent_indices)):
        raise ValueError("selected parent indices must be sorted and unique")
    if any(index < 0 or index >= len(parents) for index in parent_indices):
        raise ValueError("selected parent index is outside the frontier")
    width = 1 << len(variables)
    if len(cubes) != len(parent_indices) * width or len(statuses) != len(cubes):
        raise ValueError("selected refinement size does not match its parent list")
    selected_by_parent = {parent: position for position, parent in enumerate(parent_indices)}
    assignments = [
        [
            variable if value else -variable
            for variable, value in zip(variables, values, strict=True)
        ]
        for values in itertools.product((False, True), repeat=len(variables))
    ]
    frontier: list[list[int]] = []
    adopted: list[int] = []
    integrated_closed = 0
    for parent_index, parent in enumerate(parents):
        position = selected_by_parent.get(parent_index)
        if position is None:
            frontier.append(parent)
            continue
        if {abs(literal) for literal in parent}.intersection(variables):
            raise ValueError("a refinement variable is already assigned")
        start = position * width
        group = cubes[start : start + width]
        if group != [parent + assignment for assignment in assignments]:
            raise ValueError(
                f"cube group for parent {parent_index} is not a complete Cartesian split"
            )
        group_statuses = statuses[start : start + width]
        remaining = [
            cube for cube, status in zip(group, group_statuses, strict=True) if status == 0
        ]
        if len(remaining) <= max_remaining:
            adopted.append(parent_index)
            frontier.extend(remaining)
            integrated_closed += group_statuses.count(20)
        else:
            frontier.append(parent)
    updated = dict(state)
    updated["round"] = int(state["round"]) + 1
    updated["frontier"] = frontier
    updated["closed"] = int(state["closed"]) + integrated_closed
    return updated, adopted, integrated_closed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("variables")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--max-remaining", type=int, default=1)
    parser.add_argument("--selection", type=Path)
    arguments = parser.parse_args()
    state_bytes = arguments.state.read_bytes()
    state = json.loads(state_bytes)
    cubes = read_cubes(arguments.cubes)
    statuses = read_statuses(arguments.results)
    variables = parse_variables(arguments.variables)
    if arguments.selection is None:
        updated, adopted, integrated_closed = refine_state(
            state, cubes, statuses, variables, arguments.max_remaining
        )
        selection_sha256 = None
    else:
        selection_bytes = arguments.selection.read_bytes()
        selection = json.loads(selection_bytes)
        if selection["state_sha256"] != hashlib.sha256(state_bytes).hexdigest():
            raise ValueError("selection was generated from a different state")
        if selection["frontier_size"] != len(state["frontier"]):
            raise ValueError("selection frontier size does not match")
        if selection["variables"] != variables:
            raise ValueError("selection variables do not match")
        updated, adopted, integrated_closed = refine_selected_state(
            state,
            cubes,
            statuses,
            variables,
            arguments.max_remaining,
            selection["parent_indices"],
        )
        selection_sha256 = hashlib.sha256(selection_bytes).hexdigest()
    updated_bytes = (json.dumps(updated, sort_keys=True) + "\n").encode("utf-8")
    manifest = {
        "adopted_parent_indices": adopted,
        "closed_integrated": integrated_closed,
        "cubes": str(arguments.cubes),
        "cubes_sha256": sha256(arguments.cubes),
        "frontier_after": len(updated["frontier"]),
        "frontier_before": len(state["frontier"]),
        "max_remaining": arguments.max_remaining,
        "results": str(arguments.results),
        "results_sha256": sha256(arguments.results),
        "selection": str(arguments.selection) if arguments.selection else None,
        "selection_sha256": selection_sha256,
        "state_after_sha256": hashlib.sha256(updated_bytes).hexdigest(),
        "state_before_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "variables": variables,
    }
    temporary_manifest = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_state = arguments.state.with_suffix(arguments.state.suffix + ".tmp")
    temporary_state.write_bytes(updated_bytes)
    temporary_manifest.replace(arguments.manifest)
    temporary_state.replace(arguments.state)
    print(
        f"adopted {len(adopted)}/{len(state['frontier'])} parents; "
        f"integrated {integrated_closed} closed children; "
        f"frontier {len(state['frontier'])}->{len(updated['frontier'])}"
    )


if __name__ == "__main__":
    main()
