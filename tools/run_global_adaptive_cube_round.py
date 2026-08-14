#!/usr/bin/env python3
"""Run one resumable adaptive round with a globally balanced conquer queue."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from verify_cube_cover import cover_by_dpll


@dataclass(frozen=True)
class Result:
    status: int
    seconds: float
    model: str


@dataclass
class Generated:
    parent: list[int]
    identifier: str
    cubes_path: Path
    results_path: Path
    log_path: Path
    suffixes: list[list[int]]
    cuber_status: int
    cuber_log: str


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_base(path: Path) -> tuple[list[str], int, int]:
    lines = path.read_text(encoding="ascii").splitlines()
    headers = [index for index, line in enumerate(lines) if line.startswith("p cnf ")]
    if len(headers) != 1:
        raise ValueError("expected exactly one DIMACS header")
    fields = lines[headers[0]].split()
    return lines, headers[0], int(fields[3])


def materialize(
    lines: list[str], header: int, clauses: int, literals: list[int], output: Path
) -> None:
    rendered = list(lines)
    fields = rendered[header].split()
    rendered[header] = f"p cnf {fields[2]} {clauses + len(literals)}"
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as stream:
        for line in rendered:
            stream.write(line + "\n")
        for literal in literals:
            stream.write(f"{literal} 0\n")
    temporary.replace(output)


def read_results(path: Path) -> list[Result]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "cube\tstatus\tseconds\tmodel":
        raise ValueError("invalid solver result header")
    results: list[Result] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if int(fields[0]) != expected:
            raise ValueError("non-consecutive solver result index")
        results.append(
            Result(
                int(fields[1]),
                float(fields[2]),
                fields[3] if len(fields) > 3 else "",
            )
        )
    return results


def read_ordered_cubes(path: Path) -> list[list[int]]:
    cubes: list[list[int]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("c"):
            continue
        fields = line.split()
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError("invalid cube line")
        cube = [int(field) for field in fields[1:-1]]
        if len(cube) != len(set(cube)) or any(-literal in cube for literal in cube):
            raise ValueError("invalid or contradictory cube")
        cubes.append(cube)
    if not cubes:
        raise ValueError("cube file is empty")
    return cubes


def write_results(path: Path, results: list[Result]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        output.write("cube\tstatus\tseconds\tmodel\n")
        for index, result in enumerate(results):
            output.write(
                f"{index}\t{result.status}\t{result.seconds:.6f}\t{result.model}\n"
            )
    temporary.replace(path)


def node_id(literals: list[int]) -> str:
    return hashlib.sha256(" ".join(map(str, literals)).encode("ascii")).hexdigest()[:20]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--cuber", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--jobs", type=int, default=64)
    arguments = parser.parse_args()
    if arguments.depth <= 0 or arguments.seconds <= 0 or arguments.jobs <= 0:
        raise ValueError("depth, time limit, and jobs must be positive")
    state_path = arguments.workdir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    frontier: list[list[int]] = state["frontier"]
    if not frontier:
        print("frontier already closed")
        return
    round_number = int(state["round"])
    base_lines, header, clauses = read_base(arguments.cnf)
    print(
        f"global round {round_number} frontier={len(frontier)} jobs={arguments.jobs}",
        flush=True,
    )

    def generate(parent: list[int]) -> Generated:
        identifier = node_id(parent)
        prefix = arguments.workdir / f"r{round_number:03d}-{identifier}"
        cnf = prefix.with_suffix(".cnf")
        cubes_path = prefix.with_suffix(".cubes")
        results_path = prefix.with_suffix(".tsv")
        log_path = prefix.with_suffix(".log")
        cubes_path.unlink(missing_ok=True)
        materialize(base_lines, header, clauses, parent, cnf)
        process = subprocess.run(
            [
                str(arguments.cuber),
                str(cnf),
                str(arguments.depth),
                str(cubes_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        cnf.unlink(missing_ok=True)
        if process.returncode not in (0, 10, 20):
            raise RuntimeError(f"cuber failed for {identifier}: {process.stderr}")
        suffixes: list[list[int]] = []
        if process.returncode == 0:
            suffixes = read_ordered_cubes(cubes_path)
            covered, _, witness = cover_by_dpll(
                [frozenset(cube) for cube in suffixes]
            )
            if not covered:
                raise RuntimeError(
                    f"cuber output does not cover parent {identifier}: {witness}"
                )
        return Generated(
            parent,
            identifier,
            cubes_path,
            results_path,
            log_path,
            suffixes,
            process.returncode,
            process.stdout + process.stderr,
        )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(arguments.jobs, len(frontier))
    ) as executor:
        generated = list(executor.map(generate, frontier))
    if any(item.cuber_status == 10 for item in generated):
        candidates = [
            {"node": item.identifier, "parent": item.parent, "cuber_sat": True}
            for item in generated
            if item.cuber_status == 10
        ]
        atomic_json(arguments.workdir / "sat-candidates.json", candidates)
        raise RuntimeError("cuber found a SAT candidate; independent validation required")

    combined: list[list[int]] = []
    slices: list[tuple[int, int]] = []
    for item in generated:
        start = len(combined)
        combined.extend(item.parent + suffix for suffix in item.suffixes)
        slices.append((start, len(combined)))
    combined_cubes = arguments.workdir / f"round-{round_number:03d}-global.cubes"
    combined_results = arguments.workdir / f"round-{round_number:03d}-global.tsv"
    temporary_cubes = combined_cubes.with_suffix(combined_cubes.suffix + ".tmp")
    with temporary_cubes.open("w", encoding="ascii") as output:
        for cube in combined:
            output.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary_cubes.replace(combined_cubes)

    results: list[Result] = []
    solver_log = ""
    if combined:
        process = subprocess.run(
            [
                str(arguments.solver),
                str(arguments.cnf),
                str(combined_cubes),
                str(arguments.seconds),
                str(arguments.jobs),
                str(combined_results),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        solver_log = process.stdout + process.stderr
        results = read_results(combined_results)
        if len(results) != len(combined):
            raise RuntimeError("global cube and result counts differ")
    elif combined_results.exists():
        combined_results.unlink()

    next_frontier: list[list[int]] = []
    closed = sum(item.cuber_status == 20 for item in generated)
    candidates: list[dict] = []
    for item, (start, stop) in zip(generated, slices, strict=True):
        local_results = results[start:stop]
        write_results(item.results_path, local_results)
        item.log_path.write_text(
            item.cuber_log
            + f"global_conquer\t{combined_cubes.name}\t{start}\t{stop}\n",
            encoding="utf-8",
        )
        for suffix, result in zip(item.suffixes, local_results, strict=True):
            if result.status == 20:
                closed += 1
            elif result.status == 0:
                next_frontier.append(item.parent + suffix)
            elif result.status == 10:
                candidates.append(
                    {
                        "node": item.identifier,
                        "parent": item.parent,
                        "cube": suffix,
                        "model": result.model,
                    }
                )
            else:
                raise RuntimeError(f"unexpected solver status {result.status}")
    if candidates:
        atomic_json(arguments.workdir / "sat-candidates.json", candidates)
        raise RuntimeError("SAT candidate found; independent validation required")
    updated = dict(state)
    updated["round"] = round_number + 1
    updated["frontier"] = next_frontier
    updated["closed"] = int(state["closed"]) + closed
    atomic_json(state_path, updated)
    print(
        f"global round complete children={len(combined)} closed={closed} "
        f"next={len(next_frontier)} total_closed={updated['closed']}",
        flush=True,
    )
    if solver_log:
        (arguments.workdir / f"round-{round_number:03d}-global.log").write_text(
            solver_log, encoding="utf-8"
        )


if __name__ == "__main__":
    main()
