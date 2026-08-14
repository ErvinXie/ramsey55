#!/usr/bin/env python3
"""Run a resumable adaptive CaDiCaL cube tree on one fixed CNF."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path


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


def read_results(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "cube\tstatus\tseconds\tmodel":
        raise ValueError("invalid solver result header")
    results: list[tuple[int, str]] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if int(fields[0]) != expected:
            raise ValueError("non-consecutive cube result indices")
        results.append((int(fields[1]), fields[3] if len(fields) > 3 else ""))
    return results


def node_id(literals: list[int]) -> str:
    encoded = " ".join(map(str, literals)).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()[:20]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--cuber", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--jobs", type=int, default=64)
    parser.add_argument("--max-rounds", type=int, default=100)
    arguments = parser.parse_args()
    arguments.workdir.mkdir(parents=True, exist_ok=True)
    state_path = arguments.workdir / "state.json"
    base_lines, header, clauses = read_base(arguments.cnf)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"round": 0, "frontier": [[]], "closed": 0}
        atomic_json(state_path, state)

    while state["frontier"] and state["round"] < arguments.max_rounds:
        frontier: list[list[int]] = state["frontier"]
        parallel = min(len(frontier), arguments.jobs)
        jobs_per_solver = max(1, arguments.jobs // parallel)
        print(
            f"round {state['round']} frontier={len(frontier)} "
            f"parallel={parallel} jobs_per_solver={jobs_per_solver}",
            flush=True,
        )

        def process(parent: list[int]) -> tuple[list[list[int]], int, dict | None]:
            identifier = node_id(parent)
            prefix = arguments.workdir / f"r{state['round']:03d}-{identifier}"
            cnf = prefix.with_suffix(".cnf")
            cubes_path = prefix.with_suffix(".cubes")
            results_path = prefix.with_suffix(".tsv")
            log_path = prefix.with_suffix(".log")
            materialize(base_lines, header, clauses, parent, cnf)
            generated = subprocess.run(
                [
                    str(arguments.cuber),
                    str(cnf),
                    str(arguments.depth),
                    str(cubes_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if generated.returncode not in (0, 10, 20):
                raise RuntimeError(
                    f"cuber failed for {identifier}: {generated.stderr}"
                )
            if generated.returncode == 10:
                cnf.unlink(missing_ok=True)
                return [], 0, {"parent": parent, "node": identifier, "cuber_sat": True}
            if generated.returncode == 20:
                cnf.unlink(missing_ok=True)
                return [], 1, None
            solved = subprocess.run(
                [
                    str(arguments.solver),
                    str(cnf),
                    str(cubes_path),
                    str(arguments.seconds),
                    str(jobs_per_solver),
                    str(results_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log_path.write_text(
                generated.stdout + generated.stderr + solved.stdout + solved.stderr,
                encoding="utf-8",
            )
            cubes = read_cubes(cubes_path)
            results = read_results(results_path)
            if len(cubes) != len(results):
                raise RuntimeError("cube and result counts differ")
            children: list[list[int]] = []
            closed = 0
            candidate: dict | None = None
            for cube, (status, model) in zip(cubes, results, strict=True):
                if status == 20:
                    closed += 1
                elif status == 0:
                    children.append(parent + cube)
                elif status == 10:
                    candidate = {
                        "parent": parent,
                        "cube": cube,
                        "model": model,
                        "node": identifier,
                    }
                else:
                    raise RuntimeError(f"unexpected solver status {status}")
            cnf.unlink(missing_ok=True)
            return children, closed, candidate

        next_frontier: list[list[int]] = []
        closed_this_round = 0
        candidates: list[dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            for children, closed, candidate in executor.map(process, frontier):
                next_frontier.extend(children)
                closed_this_round += closed
                if candidate is not None:
                    candidates.append(candidate)
        if candidates:
            atomic_json(arguments.workdir / "sat-candidates.json", candidates)
            raise RuntimeError("SAT candidate found; independent validation required")
        state = {
            "round": state["round"] + 1,
            "frontier": next_frontier,
            "closed": state["closed"] + closed_this_round,
        }
        atomic_json(state_path, state)
        print(
            f"round complete closed={closed_this_round} "
            f"next={len(next_frontier)} total_closed={state['closed']}",
            flush=True,
        )

    if not state["frontier"]:
        print("UNSAT tree closed (proof traces not generated)")
    else:
        print(
            f"stopped at round {state['round']} with "
            f"{len(state['frontier'])} frontier nodes"
        )


if __name__ == "__main__":
    main()
