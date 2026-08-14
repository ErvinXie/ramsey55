#!/usr/bin/env python3
"""Append one assumption cube as unit clauses to a DIMACS CNF."""

from __future__ import annotations

import argparse
from pathlib import Path


def read_cube(path: Path, index: int) -> list[int]:
    cubes = [
        line
        for line in path.read_text(encoding="ascii").splitlines()
        if line and not line.startswith("c")
    ]
    if index < 0 or index >= len(cubes):
        raise ValueError("cube index is out of range")
    fields = cubes[index].split()
    if fields[0] != "a" or fields[-1] != "0":
        raise ValueError("invalid cube line")
    return [int(field) for field in fields[1:-1]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("index", type=int)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    literals = read_cube(arguments.cubes, arguments.index)
    lines = arguments.cnf.read_text(encoding="ascii").splitlines()
    header_indices = [
        index for index, line in enumerate(lines) if line.startswith("p cnf ")
    ]
    if len(header_indices) != 1:
        raise ValueError("expected exactly one DIMACS header")
    header_index = header_indices[0]
    fields = lines[header_index].split()
    variables, clauses = int(fields[2]), int(fields[3])
    if any(abs(literal) > variables for literal in literals):
        raise ValueError("cube literal is outside the CNF range")
    lines[header_index] = f"p cnf {variables} {clauses + len(literals)}"

    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        for line in lines:
            output.write(line + "\n")
        for literal in literals:
            output.write(f"{literal} 0\n")
    temporary.replace(arguments.output)
    print(f"applied cube {arguments.index} with {len(literals)} literals")


if __name__ == "__main__":
    main()
