#!/usr/bin/env python3
"""Append one assumption cube as unit clauses to a DIMACS CNF."""

from __future__ import annotations

import argparse
from pathlib import Path


def read_cube(path: Path, target: int) -> tuple[int, ...]:
    index = 0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if not line.strip() or line.startswith("c"):
                continue
            fields = line.split()
            if fields[0] == "a":
                literals = fields[1:]
            else:
                if int(fields[0]) != index:
                    raise ValueError(f"nonconsecutive cube id in {path}")
                literals = fields[1:]
            if len(literals) < 2 or literals[-1] != "0":
                raise ValueError(f"invalid cube line in {path}")
            cube = tuple(map(int, literals[:-1]))
            if not cube or 0 in cube:
                raise ValueError(f"invalid cube in {path}")
            if index == target:
                return cube
            index += 1
    raise IndexError(f"cube index {target} is out of range in {path}")


def materialize_cnf_cube(
    cnf: Path, cube: tuple[int, ...], output: Path
) -> tuple[int, int]:
    header_seen = False
    variables = clauses = actual_clauses = 0
    with cnf.open(encoding="ascii") as source, output.open(
        "w", encoding="ascii", newline="\n"
    ) as target:
        for line in source:
            fields = line.split()
            if fields and fields[0] == "p":
                if header_seen or len(fields) != 4 or fields[1] != "cnf":
                    raise ValueError(f"invalid DIMACS header in {cnf}")
                variables, clauses = map(int, fields[2:])
                if any(abs(literal) > variables for literal in cube):
                    raise ValueError("cube literal is outside the CNF range")
                target.write(f"p cnf {variables} {clauses + len(cube)}\n")
                header_seen = True
            else:
                target.write(line)
                if fields and fields[0] != "c":
                    if not header_seen or fields[-1] != "0":
                        raise ValueError(f"invalid DIMACS clause in {cnf}")
                    actual_clauses += 1
        if not header_seen or actual_clauses != clauses:
            raise ValueError(f"DIMACS clause count mismatch in {cnf}")
        for literal in cube:
            target.write(f"{literal} 0\n")
    return variables, clauses + len(cube)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("cube_index", type=int)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.cube_index < 0:
        parser.error("negative cube index")
    cube = read_cube(arguments.cubes, arguments.cube_index)
    variables, clauses = materialize_cnf_cube(arguments.cnf, cube, arguments.output)
    print(
        f"wrote {arguments.output}: {variables} variables, {clauses} clauses, "
        f"{len(cube)} assumptions"
    )


if __name__ == "__main__":
    main()
