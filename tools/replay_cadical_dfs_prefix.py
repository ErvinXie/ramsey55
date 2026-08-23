#!/usr/bin/env python3
"""Reconstruct a CaDiCaL DFS-forest frontier from a TSV prefix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ramsey55.cadical-dfs-prefix-replay.v2"
HEADER = "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def binary_drat_is_framed(path: Path) -> bool:
    if path.stat().st_size == 0:
        return True
    with path.open("rb") as stream:
        stream.seek(-1, 2)
        return stream.read(1) == b"\0"


def read_roots(path: Path) -> tuple[tuple[int, ...], ...]:
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
    if not roots:
        raise ValueError("at least one source root is required")
    return tuple(roots)


def read_single_root(path: Path) -> tuple[int, ...]:
    """Compatibility helper for callers that intentionally require one root."""
    roots = read_roots(path)
    if len(roots) != 1:
        raise ValueError("exactly one source root is required")
    return roots[0]


def replay_forest(
    roots: tuple[tuple[int, ...], ...], snapshot: Path
) -> tuple[list[tuple[int, ...]], dict[str, object]]:
    lines = snapshot.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != HEADER:
        raise ValueError("unexpected DFS snapshot header")
    if not roots:
        raise ValueError("at least one source root is required")
    stacks: list[list[tuple[tuple[int, ...], int]]] = [
        [(root, 0)] for root in roots
    ]
    active_root = 0
    globally_unsat = False
    maximum_depth = 0
    expected_attempt = 0
    splits = closed = 0
    for line_number, raw in enumerate(lines[1:], 2):
        if not raw:
            continue
        fields = raw.split("\t")
        if len(fields) != 8:
            raise ValueError(f"invalid DFS row at line {line_number}")
        root_index, attempt, depth, limit, status, core, split, seconds = fields
        parsed_root = int(root_index)
        if int(attempt) != expected_attempt:
            raise ValueError(f"unexpected root or attempt at line {line_number}")
        expected_attempt += 1
        parsed_depth = int(depth)
        parsed_core = int(core)
        if int(limit) <= 0 or parsed_core < 0 or float(seconds) < 0:
            raise ValueError(f"invalid telemetry at line {line_number}")
        while active_root < len(stacks) and not stacks[active_root]:
            active_root += 1
        if globally_unsat or active_root == len(stacks):
            raise ValueError("DFS prefix continues after closing the source forest")
        if parsed_root != active_root:
            raise ValueError(f"unexpected root or attempt at line {line_number}")
        cube, pending_depth = stacks[active_root].pop()
        if parsed_depth != pending_depth:
            raise ValueError(f"DFS depth mismatch at line {line_number}")
        maximum_depth = max(maximum_depth, parsed_depth)
        parsed_status = int(status)
        parsed_split = int(split)
        if parsed_status == 20:
            if parsed_split != 0:
                raise ValueError(f"UNSAT row has a split at line {line_number}")
            closed += 1
            if parsed_core == 0:
                globally_unsat = True
            continue
        if parsed_status == 10:
            raise ValueError(f"SAT row requires investigation at line {line_number}")
        if parsed_status != 0 or parsed_core != 0 or parsed_split == 0:
            raise ValueError(f"invalid status or split at line {line_number}")
        if abs(parsed_split) in {abs(literal) for literal in cube}:
            raise ValueError(f"repeated split variable at line {line_number}")
        # Match prove_cadical_cubes.cpp: negative is pushed first, positive
        # second, and the LIFO stack therefore visits the positive child next.
        splits += 1
        stacks[active_root].append((cube + (-parsed_split,), parsed_depth + 1))
        stacks[active_root].append((cube + (parsed_split,), parsed_depth + 1))
    if globally_unsat:
        frontier: list[tuple[int, ...]] = []
        root_frontier_counts = [0] * len(roots)
    else:
        root_frontiers = [
            [cube for cube, _ in reversed(stack)] for stack in stacks
        ]
        frontier = [cube for root_frontier in root_frontiers for cube in root_frontier]
        root_frontier_counts = [len(root_frontier) for root_frontier in root_frontiers]
    return frontier, {
        "attempts": expected_attempt,
        "splits": splits,
        "closed": closed,
        "maximum_depth": maximum_depth,
        "global_unsat": globally_unsat,
        "root_frontier_counts": root_frontier_counts,
    }


def replay_prefix(
    root: tuple[int, ...], snapshot: Path
) -> tuple[list[tuple[int, ...]], int]:
    """Compatibility wrapper for a single open source root."""
    frontier, replay = replay_forest((root,), snapshot)
    if not frontier:
        raise ValueError("DFS prefix already closes the source root")
    return frontier, int(replay["maximum_depth"])


def atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--proof-prefix", type=Path)
    arguments = parser.parse_args()
    for path in (arguments.root, arguments.snapshot):
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    if arguments.proof_prefix is not None and not arguments.proof_prefix.is_file():
        parser.error(f"proof prefix does not exist: {arguments.proof_prefix}")
    if arguments.proof_prefix is not None and not binary_drat_is_framed(
        arguments.proof_prefix
    ):
        parser.error(
            "proof prefix does not end at a binary DRAT clause boundary; "
            "replay without --proof-prefix, then derive a bound framed replay "
            "with frame_binary_drat_prefix.py"
        )
    if arguments.output.exists() or arguments.manifest.exists():
        parser.error("refusing to overwrite output or manifest")

    roots = read_roots(arguments.root)
    frontier, replay = replay_forest(roots, arguments.snapshot)
    if not frontier:
        raise ValueError("DFS prefix already closes the source forest")
    output_bytes = "".join(
        "a " + " ".join(map(str, cube)) + " 0\n" for cube in frontier
    ).encode("ascii")
    atomic_write(arguments.output, output_bytes)
    document: dict[str, object] = {
        "schema": SCHEMA,
        "source_root": str(arguments.root),
        "source_root_sha256": file_sha256(arguments.root),
        "snapshot": str(arguments.snapshot),
        "snapshot_sha256": file_sha256(arguments.snapshot),
        "snapshot_rows": sum(
            bool(line) for line in arguments.snapshot.read_text(encoding="ascii").splitlines()[1:]
        ),
        "processed_attempts": replay["attempts"],
        "processed_splits": replay["splits"],
        "maximum_processed_depth": replay["maximum_depth"],
        "source_root_count": len(roots),
        "root_frontier_counts": replay["root_frontier_counts"],
        "output": str(arguments.output),
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "output_count": len(frontier),
    }
    if arguments.proof_prefix is not None:
        document["proof_prefix"] = str(arguments.proof_prefix)
        document["proof_prefix_sha256"] = file_sha256(arguments.proof_prefix)
    atomic_write(
        arguments.manifest,
        (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
