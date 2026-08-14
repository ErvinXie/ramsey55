#!/usr/bin/env python3
"""Solve assumption cubes with independent external solver processes."""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Result:
    status: int
    seconds: float
    model: str = ""


def read_cnf(path: Path) -> tuple[str, str, int, int]:
    lines = path.read_text(encoding="ascii").splitlines()
    headers = [index for index, line in enumerate(lines) if line.startswith("p cnf ")]
    if len(headers) != 1:
        raise ValueError("expected exactly one DIMACS header")
    header = headers[0]
    fields = lines[header].split()
    if len(fields) != 4:
        raise ValueError("invalid DIMACS header")
    variables, clauses = int(fields[2]), int(fields[3])
    before = "\n".join(lines[:header])
    after = "\n".join(lines[header + 1 :])
    return before, after, variables, clauses


def read_cubes(path: Path, variables: int) -> list[list[int]]:
    cubes: list[list[int]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("c"):
            continue
        fields = line.split()
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError("invalid cube line")
        cube = [int(field) for field in fields[1:-1]]
        if any(literal == 0 or abs(literal) > variables for literal in cube):
            raise ValueError("cube literal is outside the CNF range")
        cubes.append(cube)
    if not cubes:
        raise ValueError("cube file is empty")
    return cubes


def render_cnf(
    before: str,
    after: str,
    variables: int,
    clauses: int,
    cube: list[int],
) -> str:
    sections = []
    if before:
        sections.append(before)
    sections.append(f"p cnf {variables} {clauses + len(cube)}")
    if after:
        sections.append(after)
    sections.extend(f"{literal} 0" for literal in cube)
    return "\n".join(sections) + "\n"


def parse_model(output: str, variables: int) -> str:
    values = [False] * (variables + 1)
    assigned = [False] * (variables + 1)
    for line in output.splitlines():
        fields = line.split()
        if not fields or fields[0] != "v":
            continue
        for field in fields[1:]:
            literal = int(field)
            if literal == 0:
                continue
            if abs(literal) > variables:
                raise ValueError("solver model literal is outside the CNF range")
            assigned[abs(literal)] = True
            values[abs(literal)] = literal > 0
    if not all(assigned[1:]):
        raise ValueError("SAT solver did not print a complete model")
    return "".join("1" if values[variable] else "0" for variable in range(1, variables + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("per_cube_seconds", type=float)
    parser.add_argument("jobs", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument("solver", type=Path)
    parser.add_argument("solver_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.per_cube_seconds <= 0 or arguments.jobs <= 0:
        raise ValueError("time limit and job count must be positive")
    before, after, variables, clauses = read_cnf(arguments.cnf)
    cubes = read_cubes(arguments.cubes, variables)
    results: list[Result | None] = [None] * len(cubes)
    completed = 0
    output_lock = threading.Lock()

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="external-cubes-", dir=arguments.output.parent
    ) as temporary_directory:
        temporary = Path(temporary_directory)

        def solve(item: tuple[int, list[int]]) -> tuple[int, Result]:
            index, cube = item
            formula = temporary / f"cube-{index}.cnf"
            formula.write_text(
                render_cnf(before, after, variables, clauses, cube), encoding="ascii"
            )
            started = time.monotonic()
            try:
                process = subprocess.run(
                    [
                        str(arguments.solver),
                        *arguments.solver_arguments,
                        str(formula),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=arguments.per_cube_seconds,
                    check=False,
                )
                elapsed = time.monotonic() - started
                if process.returncode not in (10, 20):
                    raise RuntimeError(
                        f"solver exited with {process.returncode} on cube {index}: "
                        f"{process.stderr[-1000:]}"
                    )
                model = parse_model(process.stdout, variables) if process.returncode == 10 else ""
                return index, Result(process.returncode, elapsed, model)
            except subprocess.TimeoutExpired:
                return index, Result(0, time.monotonic() - started)
            finally:
                formula.unlink(missing_ok=True)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(arguments.jobs, len(cubes))
        ) as executor:
            for index, result in executor.map(solve, enumerate(cubes)):
                results[index] = result
                completed += 1
                if completed == len(cubes) or completed % 16 == 0 or result.status == 10:
                    with output_lock:
                        print(
                            f"finished {completed}/{len(cubes)} "
                            f"cube={index} status={result.status}",
                            flush=True,
                        )

    if any(result is None for result in results):
        raise RuntimeError("missing solver result")
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary_output.open("w", encoding="ascii") as output:
        output.write("cube\tstatus\tseconds\tmodel\n")
        for index, optional_result in enumerate(results):
            assert optional_result is not None
            output.write(
                f"{index}\t{optional_result.status}\t"
                f"{optional_result.seconds:.6f}\t{optional_result.model}\n"
            )
    temporary_output.replace(arguments.output)
    print(f"completed\t{len(cubes)}")
    print(f"sat\t{sum(result is not None and result.status == 10 for result in results)}")


if __name__ == "__main__":
    main()
