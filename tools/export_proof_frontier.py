#!/usr/bin/env python3
"""Reconstruct the open DFS frontier of a flushed prove_cadical_cubes TSV."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


HEADER = (
    "root",
    "attempt",
    "depth",
    "limit",
    "status",
    "core",
    "split",
    "seconds",
)


@dataclass(frozen=True)
class Row:
    root: int
    attempt: int
    depth: int
    status: int
    split: int


def read_cubes(path: Path) -> tuple[tuple[int, ...], ...]:
    cubes: list[tuple[int, ...]] = []
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if not line.strip() or line.startswith("c"):
                continue
            fields = line.split()
            if fields[0] == "a":
                literals = fields[1:]
            else:
                if int(fields[0]) != len(cubes):
                    raise ValueError(f"nonconsecutive cube id in {path}")
                literals = fields[1:]
            if len(literals) < 2 or literals[-1] != "0":
                raise ValueError(f"invalid cube in {path}")
            cube = tuple(map(int, literals[:-1]))
            if not cube or len({abs(literal) for literal in cube}) != len(cube):
                raise ValueError(f"invalid cube literals in {path}")
            cubes.append(cube)
    if not cubes:
        raise ValueError(f"empty cube file {path}")
    return tuple(cubes)


def read_rows(path: Path, root: int) -> tuple[Row, ...]:
    rows: list[Row] = []
    expected_attempt = 0
    previous_root: int | None = None
    with path.open(newline="", encoding="ascii") as stream:
        reader = csv.reader(stream, delimiter="\t")
        if tuple(next(reader, ())) != HEADER:
            raise ValueError(f"unexpected result header in {path}")
        records = list(reader)
        for record_index, fields in enumerate(records):
            # A live writer can expose its current row before all eight fields
            # have reached disk. Only complete flushed rows are checkpoints.
            if len(fields) != len(HEADER):
                if record_index == len(records) - 1:
                    break
                raise ValueError(f"incomplete nonfinal result row in {path}")
            row_root, attempt, depth, _, status, core, split = map(
                int, fields[:7]
            )
            float(fields[7])
            if attempt != expected_attempt or depth < 0:
                raise ValueError(f"invalid attempt or depth in {path}")
            expected_attempt += 1
            if previous_root is not None and row_root < previous_root:
                raise ValueError(f"root order decreases in {path}")
            previous_root = row_root
            if status == 0:
                if core or not split:
                    raise ValueError(f"invalid split row in {path}")
            elif status == 20:
                if core < 0 or split:
                    raise ValueError(f"invalid UNSAT row in {path}")
            else:
                raise ValueError(f"non-proof status {status} in {path}")
            if row_root == root:
                rows.append(Row(row_root, attempt, depth, status, split))
    return tuple(rows)


def reconstruct_frontier(
    root_cube: tuple[int, ...], rows: tuple[Row, ...]
) -> tuple[tuple[int, ...], ...]:
    # The runner emits a preorder traversal, visiting its preferred signed
    # split literal first.
    # Keep unvisited nodes in a LIFO stack so reconstruction is independent of
    # Python's recursion limit (the production runner permits depth 1024).
    pending: list[tuple[int, tuple[int, ...]]] = [(0, root_cube)]
    for row in rows:
        if not pending:
            raise ValueError(f"result rows continue after root closed at {row.attempt}")
        depth, cube = pending.pop()
        if row.depth != depth:
            raise ValueError(
                f"unexpected depth {row.depth} at attempt {row.attempt}; "
                f"expected {depth}"
            )
        if row.status == 20:
            continue
        if any(abs(literal) == abs(row.split) for literal in cube):
            raise ValueError(f"repeated split variable at attempt {row.attempt}")
        pending.append((depth + 1, cube + (-row.split,)))
        pending.append((depth + 1, cube + (row.split,)))

    frontier = [cube for _, cube in reversed(pending)]
    splits = sum(row.status == 0 for row in rows)
    closed = sum(row.status == 20 for row in rows)
    if len(frontier) != 1 + splits - closed:
        raise ValueError("reconstructed frontier does not satisfy tree balance")
    return tuple(frontier)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("root", type=int)
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    cubes = read_cubes(arguments.cubes)
    if not 0 <= arguments.root < len(cubes):
        parser.error("root index is outside the cube file")
    rows = read_rows(arguments.results, arguments.root)
    frontier = reconstruct_frontier(cubes[arguments.root], rows)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as output:
        for cube in frontier:
            output.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary.replace(arguments.output)
    print(
        f"wrote {arguments.output}: {len(rows)} complete rows, "
        f"{len(frontier)} open cubes"
    )


if __name__ == "__main__":
    main()
