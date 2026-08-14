#!/usr/bin/env python3
"""Create or replay a linear-size sibling-merge certificate for a cube cover."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from pathlib import Path

if __package__:
    from tools.verify_cube_cover import Cube, ordered, read_cubes
else:
    from verify_cube_cover import Cube, ordered, read_cubes


SCHEMA = "ramsey55.binary-cube-cover.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_certificate(cubes: list[Cube]) -> tuple[list[dict], set[Cube]]:
    active = set(cubes)
    pending: list[tuple[int, tuple[int, ...], int]] = []

    def schedule(cube: Cube) -> None:
        for literal in cube:
            variable = abs(literal)
            base = cube - {literal}
            if base | {-variable} in active and base | {variable} in active:
                heapq.heappush(
                    pending, (len(base), tuple(ordered(base)), variable)
                )

    for cube in active:
        schedule(cube)
    steps: list[dict] = []
    while pending and frozenset() not in active:
        _, base_literals, variable = heapq.heappop(pending)
        base = frozenset(base_literals)
        negative = base | {-variable}
        positive = base | {variable}
        if negative not in active or positive not in active:
            continue
        active.remove(negative)
        active.remove(positive)
        added = base not in active
        active.add(base)
        steps.append(
            {
                "negative": ordered(negative),
                "positive": ordered(positive),
                "result": ordered(base),
                "variable": variable,
            }
        )
        if added:
            schedule(base)
    return steps, active


def replay(cubes: list[Cube], steps: list[dict]) -> set[Cube]:
    active = set(cubes)
    for index, step in enumerate(steps):
        variable = int(step["variable"])
        result = frozenset(map(int, step["result"]))
        negative = frozenset(map(int, step["negative"]))
        positive = frozenset(map(int, step["positive"]))
        if variable <= 0 or negative != result | {-variable}:
            raise ValueError(f"invalid negative merge input at step {index}")
        if positive != result | {variable}:
            raise ValueError(f"invalid positive merge input at step {index}")
        if negative not in active or positive not in active:
            raise ValueError(f"inactive merge input at step {index}")
        active.remove(negative)
        active.remove(positive)
        active.add(result)
    return active


def create(cubes_path: Path, certificate_path: Path) -> None:
    cubes = read_cubes(cubes_path)
    steps, residual = merge_certificate(cubes)
    if frozenset() not in residual:
        raise ValueError(
            f"sibling merging did not prove coverage; residual={len(residual)}"
        )
    document = {
        "schema": SCHEMA,
        "input": str(cubes_path),
        "input_sha256": file_sha256(cubes_path),
        "cube_count": len(cubes),
        "steps": steps,
        "step_count": len(steps),
        "residual": [
            ordered(cube)
            for cube in sorted(residual, key=lambda cube: (len(cube), ordered(cube)))
        ],
        "covered": True,
    }
    temporary = certificate_path.with_suffix(certificate_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(certificate_path)
    print(
        json.dumps(
            {
                "cubes": len(cubes),
                "steps": len(steps),
                "residual": len(residual),
                "covered": True,
            },
            sort_keys=True,
        )
    )


def audit(cubes_path: Path, certificate_path: Path) -> None:
    document = json.loads(certificate_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected binary-cover certificate schema")
    if file_sha256(cubes_path) != document["input_sha256"]:
        raise ValueError("cube input hash mismatch")
    cubes = read_cubes(cubes_path)
    if len(cubes) != int(document["cube_count"]):
        raise ValueError("cube count mismatch")
    steps = document["steps"]
    if len(steps) != int(document["step_count"]):
        raise ValueError("step count mismatch")
    residual = replay(cubes, steps)
    recorded_residual = {
        frozenset(map(int, cube)) for cube in document["residual"]
    }
    if residual != recorded_residual:
        raise ValueError("residual family mismatch")
    if document.get("covered") is not True or frozenset() not in residual:
        raise ValueError("certificate does not establish coverage")
    print(
        json.dumps(
            {
                "cubes": len(cubes),
                "steps": len(steps),
                "residual": len(residual),
                "covered": True,
                "certificate_sha256": file_sha256(certificate_path),
            },
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "audit"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("cubes", type=Path)
        subparser.add_argument("certificate", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "create":
        create(arguments.cubes, arguments.certificate)
    else:
        audit(arguments.cubes, arguments.certificate)


if __name__ == "__main__":
    main()
