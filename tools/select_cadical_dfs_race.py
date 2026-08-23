#!/usr/bin/env python3
"""Select one completed or checkpointed CaDiCaL DFS race exactly."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "ramsey55.cadical-dfs-race-selection.v1"
HEADER = "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def read_single_root(path: Path) -> tuple[int, ...]:
    roots: list[tuple[int, ...]] = []
    for line_number, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        fields = raw.split()
        if not fields or fields[0] == "c":
            continue
        if fields[0] == "a":
            literals = fields[1:]
        else:
            if int(fields[0]) != len(roots):
                raise ValueError(f"nonconsecutive root id at line {line_number}")
            literals = fields[1:]
        if len(literals) < 2 or literals[-1] != "0":
            raise ValueError(f"invalid root row at line {line_number}")
        cube = tuple(map(int, literals[:-1]))
        if not cube or 0 in cube or len({abs(value) for value in cube}) != len(cube):
            raise ValueError(f"invalid root cube at line {line_number}")
        roots.append(cube)
    if len(roots) != 1:
        raise ValueError("exactly one source root is required")
    return roots[0]


def parse_log(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        fields = raw.split()
        if len(fields) != 2:
            continue
        key, value = fields
        if key in {
            "proof_fragment",
            "checkpoint",
            "status",
            "cubes",
            "attempts",
            "splits",
            "maximum_extra_depth",
        }:
            if key in values:
                raise ValueError(f"duplicate {key} in producer log: {path}")
            values[key] = int(value)
    if values.get("proof_fragment") != 1:
        raise ValueError(f"producer log is not for a proof fragment: {path}")
    if values.get("status") not in (0, 20):
        raise ValueError(f"producer log lacks final status 0 or 20: {path}")
    if values["status"] == 0 and values.get("checkpoint") != 1:
        raise ValueError(f"status-0 producer log lacks checkpoint=1: {path}")
    if values["status"] == 20 and values.get("cubes") != 1:
        raise ValueError(f"completed producer log does not record one cube: {path}")
    for key in ("attempts", "splits", "maximum_extra_depth"):
        if key not in values or values[key] < 0:
            raise ValueError(f"producer log lacks valid {key}: {path}")
    return values


def replay_snapshot(
    root: tuple[int, ...], snapshot: Path
) -> tuple[list[tuple[int, ...]], dict[str, int]]:
    lines = snapshot.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != HEADER:
        raise ValueError(f"unexpected DFS snapshot header: {snapshot}")
    stack: list[tuple[tuple[int, ...], int]] = [(root, 0)]
    attempts = splits = closed = maximum_depth = 0
    for line_number, raw in enumerate(lines[1:], 2):
        if not raw:
            continue
        fields = raw.split("\t")
        if len(fields) != 8:
            raise ValueError(f"invalid DFS row at line {line_number}: {snapshot}")
        root_index, attempt, depth, limit, status, core, split, seconds = fields
        if int(root_index) != 0 or int(attempt) != attempts:
            raise ValueError(f"unexpected root or attempt at line {line_number}")
        if not stack:
            raise ValueError(f"DFS snapshot continues after root closure at line {line_number}")
        cube, expected_depth = stack.pop()
        parsed_depth = int(depth)
        parsed_limit = int(limit)
        parsed_status = int(status)
        parsed_core = int(core)
        parsed_split = int(split)
        parsed_seconds = float(seconds)
        if (
            parsed_depth != expected_depth
            or parsed_limit <= 0
            or parsed_core < 0
            or parsed_seconds < 0
        ):
            raise ValueError(f"invalid DFS telemetry at line {line_number}")
        maximum_depth = max(maximum_depth, parsed_depth)
        attempts += 1
        if parsed_status == 20:
            if parsed_split != 0:
                raise ValueError(f"UNSAT row has a split at line {line_number}")
            closed += 1
            continue
        if parsed_status == 10:
            raise ValueError(f"SAT row requires investigation at line {line_number}")
        if parsed_status != 0 or parsed_split == 0:
            raise ValueError(f"invalid status or split at line {line_number}")
        if abs(parsed_split) in {abs(literal) for literal in cube}:
            raise ValueError(f"repeated split variable at line {line_number}")
        splits += 1
        stack.append((cube + (-parsed_split,), parsed_depth + 1))
        stack.append((cube + (parsed_split,), parsed_depth + 1))
    return [cube for cube, _ in reversed(stack)], {
        "attempts": attempts,
        "splits": splits,
        "closed": closed,
        "maximum_depth": maximum_depth,
    }


def proof_is_framed(path: Path) -> bool:
    if path.stat().st_size == 0:
        return True
    with path.open("rb") as stream:
        stream.seek(-1, 2)
        return stream.read(1) == b"\0"


def inspect_race(
    root: tuple[int, ...], proof: Path, snapshot: Path, log: Path
) -> dict[str, Any]:
    for path in (proof, snapshot, log):
        if not path.is_file():
            raise ValueError(f"race input does not exist: {path}")
    if not proof_is_framed(proof):
        raise ValueError(f"proof is not binary-clause framed: {proof}")
    producer = parse_log(log)
    frontier, replay = replay_snapshot(root, snapshot)
    if producer["attempts"] != replay["attempts"]:
        raise ValueError(f"producer/replay attempt mismatch: {log}")
    if producer["splits"] != replay["splits"]:
        raise ValueError(f"producer/replay split mismatch: {log}")
    if producer["maximum_extra_depth"] != replay["maximum_depth"]:
        raise ValueError(f"producer/replay maximum-depth mismatch: {log}")
    completed = producer["status"] == 20
    if completed != (not frontier):
        raise ValueError(f"producer status disagrees with replayed frontier: {log}")
    return {
        "proof": {**file_record(proof), "binary_clause_framed": True},
        "snapshot": file_record(snapshot),
        "producer_log": file_record(log),
        "producer_status": producer["status"],
        "completed": completed,
        "attempts": replay["attempts"],
        "splits": replay["splits"],
        "closed_nodes": replay["closed"],
        "maximum_depth": replay["maximum_depth"],
        "frontier_count": len(frontier),
        "frontier_sha256": hashlib.sha256(
            "".join(
                "a " + " ".join(map(str, cube)) + " 0\n" for cube in frontier
            ).encode("ascii")
        ).hexdigest(),
    }


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument(
        "--race",
        action="append",
        nargs=3,
        metavar=("PROOF", "TSV", "LOG"),
        required=True,
    )
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.manifest.exists() or arguments.manifest.with_suffix(
        arguments.manifest.suffix + ".tmp"
    ).exists():
        parser.error("refusing to overwrite the output manifest")
    if not arguments.source_root.is_file():
        parser.error(f"source root does not exist: {arguments.source_root}")

    root = read_single_root(arguments.source_root)
    races = [
        inspect_race(root, *(Path(value) for value in race))
        for race in arguments.race
    ]
    chosen_index = min(
        range(len(races)),
        key=lambda index: (
            not races[index]["completed"],
            races[index]["frontier_count"],
            races[index]["proof"]["size"],
            index,
        ),
    )
    document = {
        "schema": SCHEMA,
        "source_root": file_record(arguments.source_root),
        "races": races,
        "selection_policy": [
            "completed first",
            "minimum frontier count",
            "minimum proof size",
            "input order",
        ],
        "chosen_index": chosen_index,
        "chosen_completed": races[chosen_index]["completed"],
        "chosen_proof_sha256": races[chosen_index]["proof"]["sha256"],
    }
    atomic_json(arguments.manifest, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
