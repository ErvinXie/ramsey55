#!/usr/bin/env python3
"""Verify a cube file covers every Boolean assignment by sound reductions."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


Cube = frozenset[int]
Clause = frozenset[int]


def read_cubes(path: Path) -> list[Cube]:
    cubes: list[Cube] = []
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        if not line or line.startswith("c"):
            continue
        fields = line.split()
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError(f"invalid cube line {line_number}")
        literals = [int(field) for field in fields[1:-1]]
        if any(literal == 0 for literal in literals):
            raise ValueError(f"zero literal before terminator on line {line_number}")
        if len(set(literals)) != len(literals):
            raise ValueError(f"duplicate literal on line {line_number}")
        literal_set = frozenset(literals)
        if any(-literal in literal_set for literal in literal_set):
            raise ValueError(f"contradictory cube on line {line_number}")
        cubes.append(literal_set)
    if not cubes:
        raise ValueError("cube file is empty")
    if len(set(cubes)) != len(cubes):
        raise ValueError("cube file contains duplicate cubes")
    return cubes


def ordered(cube: Cube) -> list[int]:
    return sorted(cube, key=lambda literal: (abs(literal), literal < 0))


def reduce_cover(cubes: list[Cube]) -> tuple[bool, list[dict], set[Cube]]:
    """Reduce `(B & x) | (B & !x)` to `B`, plus sound absorption."""
    active = set(cubes)
    steps: list[dict] = []
    while active and frozenset() not in active:
        indexed: dict[tuple[Cube, int], dict[int, Cube]] = {}
        for cube in sorted(active, key=ordered):
            for literal in ordered(cube):
                base = cube - {literal}
                indexed.setdefault((base, abs(literal)), {})[
                    1 if literal > 0 else -1
                ] = cube
        pair = next(
            (
                (base, variable, signs[-1], signs[1])
                for (base, variable), signs in indexed.items()
                if -1 in signs and 1 in signs
            ),
            None,
        )
        if pair is not None:
            base, variable, negative, positive = pair
            active.remove(negative)
            active.remove(positive)
            active.add(base)
            steps.append(
                {
                    "kind": "merge",
                    "negative": ordered(negative),
                    "positive": ordered(positive),
                    "result": ordered(base),
                    "variable": variable,
                }
            )
            continue

        absorbed = False
        by_size = sorted(active, key=lambda cube: (len(cube), ordered(cube)))
        for index, smaller in enumerate(by_size):
            for larger in by_size[index + 1 :]:
                if len(larger) == len(smaller):
                    continue
                if smaller < larger:
                    active.remove(larger)
                    steps.append(
                        {
                            "kind": "absorb",
                            "kept": ordered(smaller),
                            "removed": ordered(larger),
                        }
                    )
                    absorbed = True
                    break
            if absorbed:
                break
        if not absorbed:
            break
    return frozenset() in active, steps, active


def _normalize_cnf(clauses: set[Clause]) -> tuple[Clause, ...]:
    ordered_clauses = sorted(
        clauses, key=lambda clause: (len(clause), ordered(clause))
    )
    minimal: list[Clause] = []
    for clause in ordered_clauses:
        if not any(smaller <= clause for smaller in minimal):
            minimal.append(clause)
    return tuple(minimal)


def cover_by_dpll(cubes: list[Cube]) -> tuple[bool, int, list[int] | None]:
    """Decide whether the negations of the cubes form an UNSAT CNF."""
    initial = _normalize_cnf({frozenset(-literal for literal in cube) for cube in cubes})
    nodes = 0
    known_unsat: set[tuple[Clause, ...]] = set()

    def search(
        formula: tuple[Clause, ...], assignment: dict[int, bool]
    ) -> dict[int, bool] | None:
        nonlocal nodes
        nodes += 1
        if formula in known_unsat:
            return None
        clauses = set(formula)
        local_assignment = dict(assignment)
        while True:
            if frozenset() in clauses:
                known_unsat.add(formula)
                return None
            if not clauses:
                return local_assignment
            unit = next((next(iter(clause)) for clause in clauses if len(clause) == 1), None)
            if unit is None:
                break
            variable, value = abs(unit), unit > 0
            if variable in local_assignment and local_assignment[variable] != value:
                known_unsat.add(formula)
                return None
            local_assignment[variable] = value
            simplified: set[Clause] = set()
            for clause in clauses:
                if unit in clause:
                    continue
                simplified.add(clause - {-unit})
            clauses = simplified
        normalized = _normalize_cnf(clauses)
        if normalized in known_unsat:
            known_unsat.add(formula)
            return None
        occurrences = Counter(abs(literal) for clause in normalized for literal in clause)
        shortest = min(normalized, key=lambda clause: (len(clause), ordered(clause)))
        variable = max(
            (abs(literal) for literal in shortest),
            key=lambda candidate: (occurrences[candidate], -candidate),
        )
        for value in (False, True):
            literal = variable if value else -variable
            branch: set[Clause] = set()
            for clause in normalized:
                if literal in clause:
                    continue
                branch.add(clause - {-literal})
            branch_assignment = dict(local_assignment)
            branch_assignment[variable] = value
            witness = search(_normalize_cnf(branch), branch_assignment)
            if witness is not None:
                return witness
        known_unsat.add(normalized)
        known_unsat.add(formula)
        return None

    witness_map = search(initial, {})
    if witness_map is None:
        return True, nodes, None
    variables = sorted({abs(literal) for cube in cubes for literal in cube})
    witness = [
        variable if witness_map.get(variable, False) else -variable
        for variable in variables
    ]
    values = {abs(literal): literal > 0 for literal in witness}
    if any(all(values[abs(literal)] == (literal > 0) for literal in cube) for cube in cubes):
        raise RuntimeError("internal DPLL witness does not avoid every cube")
    return False, nodes, witness


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("--certificate", type=Path)
    arguments = parser.parse_args()
    cubes = read_cubes(arguments.cubes)
    reduced, steps, residual = reduce_cover(cubes)
    covered, dpll_nodes, witness = cover_by_dpll(cubes)
    digest = hashlib.sha256(arguments.cubes.read_bytes()).hexdigest()
    summary = {
        "covered": covered,
        "cube_count": len(cubes),
        "dpll_nodes": dpll_nodes,
        "depth_histogram": dict(sorted(Counter(map(len, cubes)).items())),
        "input": str(arguments.cubes),
        "input_sha256": digest,
        "max_variable": max(abs(literal) for cube in cubes for literal in cube),
        "reduction_steps": len(steps),
        "reduction_completed": reduced,
        "residual_count": len(residual),
    }
    if arguments.certificate is not None:
        certificate = dict(summary)
        certificate["steps"] = steps
        certificate["residual"] = [
            ordered(cube) for cube in sorted(residual, key=lambda c: (len(c), ordered(c)))
        ]
        certificate["uncovered_witness"] = witness
        temporary = arguments.certificate.with_suffix(
            arguments.certificate.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(certificate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(arguments.certificate)
    print(json.dumps(summary, sort_keys=True))
    if not covered:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
