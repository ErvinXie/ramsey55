#!/usr/bin/env python3
"""Reconstruct a single-root CaDiCaL DFS frontier from a TSV prefix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ramsey55.cadical-dfs-prefix-replay.v1"
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


def replay_prefix(root: tuple[int, ...], snapshot: Path) -> tuple[list[tuple[int, ...]], int]:
    lines = snapshot.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != HEADER:
        raise ValueError("unexpected DFS snapshot header")
    stack: list[tuple[tuple[int, ...], int]] = [(root, 0)]
    maximum_depth = 0
    expected_attempt = 0
    for line_number, raw in enumerate(lines[1:], 2):
        if not raw:
            continue
        fields = raw.split("\t")
        if len(fields) != 8:
            raise ValueError(f"invalid DFS row at line {line_number}")
        root_index, attempt, depth, limit, status, core, split, seconds = fields
        if int(root_index) != 0 or int(attempt) != expected_attempt:
            raise ValueError(f"unexpected root or attempt at line {line_number}")
        expected_attempt += 1
        parsed_depth = int(depth)
        if int(limit) <= 0 or int(core) < 0 or float(seconds) < 0:
            raise ValueError(f"invalid telemetry at line {line_number}")
        if not stack:
            raise ValueError("DFS prefix continues after closing the root")
        cube, pending_depth = stack.pop()
        if parsed_depth != pending_depth:
            raise ValueError(f"DFS depth mismatch at line {line_number}")
        maximum_depth = max(maximum_depth, parsed_depth)
        parsed_status = int(status)
        parsed_split = int(split)
        if parsed_status == 20:
            if parsed_split != 0:
                raise ValueError(f"UNSAT row has a split at line {line_number}")
            continue
        if parsed_status == 10:
            raise ValueError(f"SAT row requires investigation at line {line_number}")
        if parsed_status != 0 or parsed_split == 0:
            raise ValueError(f"invalid status or split at line {line_number}")
        if abs(parsed_split) in {abs(literal) for literal in cube}:
            raise ValueError(f"repeated split variable at line {line_number}")
        # Match prove_cadical_cubes.cpp: negative is pushed first, positive
        # second, and the LIFO stack therefore visits the positive child next.
        stack.append((cube + (-parsed_split,), parsed_depth + 1))
        stack.append((cube + (parsed_split,), parsed_depth + 1))
    if not stack:
        raise ValueError("DFS prefix already closes the source root")
    return [cube for cube, _ in reversed(stack)], maximum_depth


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

    root = read_single_root(arguments.root)
    frontier, maximum_depth = replay_prefix(root, arguments.snapshot)
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
        "maximum_processed_depth": maximum_depth,
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
