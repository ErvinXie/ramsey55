#!/usr/bin/env python3
"""Split every UNKNOWN cube into an explicit two-child covering pair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_cubes(path: Path) -> list[tuple[int, ...]]:
    cubes: list[tuple[int, ...]] = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields or fields[0] == "c":
                continue
            if fields[0] == "a":
                literal_fields = fields[1:]
            elif fields[0].isdigit():
                expected_id = len(cubes)
                if int(fields[0]) != expected_id:
                    raise ValueError(f"cube id differs on line {line_number}")
                literal_fields = fields[1:]
            else:
                raise ValueError(f"bad cube marker on line {line_number}")
            if not literal_fields or literal_fields[-1] != "0":
                raise ValueError(f"unterminated cube on line {line_number}")
            cube = tuple(map(int, literal_fields[:-1]))
            if not cube or any(literal == 0 for literal in cube):
                raise ValueError(f"invalid cube on line {line_number}")
            if len({abs(literal) for literal in cube}) != len(cube):
                raise ValueError(f"repeated cube variable on line {line_number}")
            cubes.append(cube)
    if not cubes:
        raise ValueError("cube file is empty")
    return cubes


def read_results(paths: list[Path], cube_count: int) -> list[int]:
    statuses: list[int | None] = [None] * cube_count
    for path in paths:
        with path.open(encoding="ascii") as stream:
            header = stream.readline().rstrip("\n").split("\t")
            if header[:2] != ["cube", "status"]:
                raise ValueError(f"unexpected result header in {path}")
            for line_number, line in enumerate(stream, 2):
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 2:
                    raise ValueError(f"short result line {path}:{line_number}")
                cube_id = int(fields[0])
                status = int(fields[1])
                if not 0 <= cube_id < cube_count or status not in (0, 10, 20):
                    raise ValueError(f"invalid result {path}:{line_number}")
                if statuses[cube_id] is not None:
                    raise ValueError(f"duplicate result for cube {cube_id}")
                statuses[cube_id] = status
    missing = [index for index, status in enumerate(statuses) if status is None]
    if missing:
        raise ValueError(f"missing {len(missing)} cube results")
    return [int(status) for status in statuses]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--primary-variables", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--keep-unknown",
        action="store_true",
        help="filter the UNKNOWN frontier without adding a binary split",
    )
    arguments = parser.parse_args()
    if arguments.primary_variables <= 0:
        raise ValueError("primary variable count must be positive")

    cubes = read_cubes(arguments.cubes)
    statuses = read_results(arguments.results, len(cubes))
    if 10 in statuses:
        raise ValueError("a SAT cube must be investigated instead of refined")
    children: list[tuple[int, ...]] = []
    for cube, status in zip(cubes, statuses):
        if status == 20:
            continue
        if arguments.keep_unknown:
            children.append(cube)
            continue
        used = {abs(literal) for literal in cube}
        variable = next(
            (
                candidate
                for candidate in range(1, arguments.primary_variables + 1)
                if candidate not in used
            ),
            None,
        )
        if variable is None:
            raise ValueError("UNKNOWN cube assigns every primary variable")
        children.extend(((*cube, variable), (*cube, -variable)))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="ascii", newline="\n") as output:
        for cube_id, cube in enumerate(children):
            output.write(f"{cube_id} " + " ".join(map(str, cube)) + " 0\n")
    manifest_path = arguments.manifest or arguments.output.with_suffix(".json")
    document = {
        "schema": "ramsey55.refined-cube-frontier.v1",
        "parent": str(arguments.cubes),
        "parent_sha256": file_sha256(arguments.cubes),
        "parent_cubes": len(cubes),
        "results": [
            {"path": str(path), "sha256": file_sha256(path)}
            for path in arguments.results
        ],
        "unsat_parents": statuses.count(20),
        "unknown_parents": statuses.count(0),
        "refinement": "filter" if arguments.keep_unknown else "binary split",
        "branch_variables": [1, arguments.primary_variables],
        "child_cubes": len(children),
        "path": arguments.output.name,
        "sha256": file_sha256(arguments.output),
    }
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
