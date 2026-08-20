#!/usr/bin/env python3
"""Generate the complete Cartesian split on selected DIMACS variables."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path


def parse_variables(text: str, *, maximum_count: int | None = 24) -> list[int]:
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
    if maximum_count is not None and len(variables) > maximum_count:
        if maximum_count == 24:
            raise ValueError("refusing to emit more than 2^24 cubes")
        raise ValueError(f"refusing to use more than {maximum_count} variables")
    return variables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("variables", help="comma-separated variables or ranges")
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    variables = parse_variables(arguments.variables)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        for values in itertools.product((False, True), repeat=len(variables)):
            literals = [
                variable if value else -variable
                for variable, value in zip(variables, values, strict=True)
            ]
            output.write("a " + " ".join(map(str, literals)) + " 0\n")
    temporary.replace(arguments.output)
    print(f"wrote {1 << len(variables)} cubes of depth {len(variables)}")


if __name__ == "__main__":
    main()
