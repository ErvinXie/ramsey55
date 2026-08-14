#!/usr/bin/env python3
"""Verify and atomically adopt useful per-parent Cartesian refinements."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from adopt_cartesian_refinement import read_cubes, read_statuses, sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--max-remaining", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.max_remaining < 0:
        raise ValueError("--max-remaining must be nonnegative")
    state_bytes = arguments.state.read_bytes()
    state = json.loads(state_bytes)
    selection_bytes = arguments.selection.read_bytes()
    selection = json.loads(selection_bytes)
    if selection["state_sha256"] != hashlib.sha256(state_bytes).hexdigest():
        raise ValueError("selection was generated from a different state")
    if selection["frontier_size"] != len(state["frontier"]):
        raise ValueError("selection frontier size does not match")
    entries = selection["entries"]
    parent_indices = [entry["parent_index"] for entry in entries]
    if parent_indices != sorted(set(parent_indices)):
        raise ValueError("selected parent indices must be sorted and unique")
    cubes = read_cubes(arguments.cubes)
    statuses = read_statuses(arguments.results)
    if len(cubes) != len(statuses):
        raise ValueError("cube and result counts differ")
    if any(status == 10 for status in statuses):
        raise ValueError("SAT candidate present; refusing to adopt")

    offsets: list[tuple[int, int]] = []
    offset = 0
    for entry in entries:
        width = 1 << len(entry["variables"])
        offsets.append((offset, offset + width))
        offset += width
    if offset != len(cubes):
        raise ValueError("refinement size does not match selection")
    by_parent = {
        entry["parent_index"]: (entry, start, stop)
        for entry, (start, stop) in zip(entries, offsets, strict=True)
    }
    frontier: list[list[int]] = []
    adopted: list[int] = []
    integrated_closed = 0
    for parent_index, parent in enumerate(state["frontier"]):
        selected = by_parent.get(parent_index)
        if selected is None:
            frontier.append(parent)
            continue
        entry, start, stop = selected
        variables = entry["variables"]
        if len(set(variables)) != len(variables) or any(
            variable <= 0 for variable in variables
        ):
            raise ValueError("invalid selected variables")
        if {abs(literal) for literal in parent}.intersection(variables):
            raise ValueError("a selected variable is already assigned")
        expected = [
            parent
            + [
                variable if value else -variable
                for variable, value in zip(variables, values, strict=True)
            ]
            for values in itertools.product((False, True), repeat=len(variables))
        ]
        group = cubes[start:stop]
        if group != expected:
            raise ValueError(f"parent {parent_index} is not completely refined")
        group_statuses = statuses[start:stop]
        remaining = [
            cube for cube, status in zip(group, group_statuses, strict=True) if status == 0
        ]
        if len(remaining) <= arguments.max_remaining:
            adopted.append(parent_index)
            frontier.extend(remaining)
            integrated_closed += group_statuses.count(20)
        else:
            frontier.append(parent)
    updated = dict(state)
    updated["round"] = int(state["round"]) + 1
    updated["frontier"] = frontier
    updated["closed"] = int(state["closed"]) + integrated_closed
    updated_bytes = (json.dumps(updated, sort_keys=True) + "\n").encode("utf-8")
    manifest = {
        "adopted_parent_indices": adopted,
        "closed_integrated": integrated_closed,
        "cubes": str(arguments.cubes),
        "cubes_sha256": sha256(arguments.cubes),
        "frontier_after": len(frontier),
        "frontier_before": len(state["frontier"]),
        "max_remaining": arguments.max_remaining,
        "results": str(arguments.results),
        "results_sha256": sha256(arguments.results),
        "selection": str(arguments.selection),
        "selection_sha256": hashlib.sha256(selection_bytes).hexdigest(),
        "state_after_sha256": hashlib.sha256(updated_bytes).hexdigest(),
        "state_before_sha256": hashlib.sha256(state_bytes).hexdigest(),
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
        f"adopted {len(adopted)}/{len(entries)} selected parents; "
        f"integrated {integrated_closed} closed children; "
        f"frontier {len(state['frontier'])}->{len(frontier)}"
    )


if __name__ == "__main__":
    main()
