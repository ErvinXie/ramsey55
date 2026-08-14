#!/usr/bin/env python3
"""Export all or an even sample of an adaptive cube-tree frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample", type=int)
    arguments = parser.parse_args()
    state = json.loads(arguments.state.read_text(encoding="utf-8"))
    frontier: list[list[int]] = state["frontier"]
    if arguments.sample is not None:
        if arguments.sample <= 0 or arguments.sample > len(frontier):
            raise ValueError("invalid sample size")
        frontier = [
            frontier[index * len(frontier) // arguments.sample]
            for index in range(arguments.sample)
        ]
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        for cube in frontier:
            output.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary.replace(arguments.output)
    print(f"exported {len(frontier)} cubes from round {state['round']}")


if __name__ == "__main__":
    main()
