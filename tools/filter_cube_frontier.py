#!/usr/bin/env python3
"""Filter an adaptive frontier using an external solve_cadical_cubes table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("results", type=Path)
    arguments = parser.parse_args()
    state = json.loads(arguments.state.read_text(encoding="utf-8"))
    frontier: list[list[int]] = state["frontier"]
    lines = arguments.results.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "cube\tstatus\tseconds\tmodel":
        raise ValueError("invalid result header")
    statuses: list[int] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if int(fields[0]) != expected:
            raise ValueError("non-consecutive result index")
        statuses.append(int(fields[1]))
    if len(frontier) != len(statuses):
        raise ValueError("frontier and result counts differ")
    if any(status == 10 for status in statuses):
        raise ValueError("SAT candidate present; refusing to filter")
    if any(status not in (0, 20) for status in statuses):
        raise ValueError("unexpected result status")
    retained = [
        cube for cube, status in zip(frontier, statuses, strict=True) if status == 0
    ]
    closed = statuses.count(20)
    state["frontier"] = retained
    state["closed"] += closed
    temporary = arguments.state.with_suffix(arguments.state.suffix + ".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(arguments.state)
    print(f"filtered {closed} closed cubes; retained {len(retained)}")


if __name__ == "__main__":
    main()
