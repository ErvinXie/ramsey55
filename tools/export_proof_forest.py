#!/usr/bin/env python3
"""Snapshot every closed leaf and open node in a unified proof DFS forest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from tools.export_proof_frontier import HEADER, Row, read_cubes
else:
    from export_proof_frontier import HEADER, Row, read_cubes


SCHEMA = "ramsey55.proof-forest-snapshot.v1"


@dataclass(frozen=True)
class RootLeaves:
    root: int
    closed: tuple[tuple[int, ...], ...]
    open: tuple[tuple[int, ...], ...]
    rows: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows_bytes(data: bytes, root_count: int) -> dict[int, tuple[Row, ...]]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("result table is not ASCII") from error
    reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t")
    if tuple(next(reader, ())) != HEADER:
        raise ValueError("unexpected result header")
    records = list(reader)
    grouped: dict[int, list[Row]] = {}
    expected_attempt = 0
    previous_root: int | None = None
    for record_index, fields in enumerate(records):
        if len(fields) != len(HEADER):
            if record_index == len(records) - 1:
                break
            raise ValueError("incomplete nonfinal result row")
        root, attempt, depth, limit, status, core, split = map(int, fields[:7])
        seconds = float(fields[7])
        if (
            not 0 <= root < root_count
            or attempt != expected_attempt
            or depth < 0
            or limit <= 0
            or seconds < 0
        ):
            raise ValueError("invalid numeric result field")
        expected_attempt += 1
        if previous_root is not None and root < previous_root:
            raise ValueError("root order decreases")
        previous_root = root
        if status == 0:
            if core or not split:
                raise ValueError("invalid split row")
        elif status == 20:
            if core < 0 or split:
                raise ValueError("invalid UNSAT row")
        else:
            raise ValueError(f"non-proof status {status}")
        grouped.setdefault(root, []).append(Row(root, attempt, depth, status, split))
    return {root: tuple(rows) for root, rows in grouped.items()}


def reconstruct_root(
    root: int, root_cube: tuple[int, ...], rows: tuple[Row, ...]
) -> RootLeaves:
    pending: list[tuple[int, tuple[int, ...]]] = [(0, root_cube)]
    closed: list[tuple[int, ...]] = []
    for row in rows:
        if not pending:
            raise ValueError(f"rows continue after root {root} closed")
        depth, cube = pending.pop()
        if row.depth != depth:
            raise ValueError(
                f"unexpected depth {row.depth} at attempt {row.attempt}; expected {depth}"
            )
        if row.status == 20:
            closed.append(cube)
            continue
        if any(abs(literal) == abs(row.split) for literal in cube):
            raise ValueError(f"repeated split variable at attempt {row.attempt}")
        pending.append((depth + 1, cube + (-row.split,)))
        pending.append((depth + 1, cube + (row.split,)))
    open_cubes = tuple(cube for _, cube in reversed(pending))
    splits = sum(row.status == 0 for row in rows)
    if len(open_cubes) + len(closed) != 1 + splits:
        raise ValueError(f"tree balance fails at root {root}")
    return RootLeaves(root, tuple(closed), open_cubes, len(rows))


def reconstruct_forest(
    cubes: tuple[tuple[int, ...], ...], grouped: dict[int, tuple[Row, ...]]
) -> tuple[RootLeaves, ...]:
    forest: list[RootLeaves] = []
    unfinished = False
    for root, cube in enumerate(cubes):
        rows = grouped.get(root, ())
        if unfinished and rows:
            raise ValueError("a later root has rows after an unfinished root")
        leaves = reconstruct_root(root, cube, rows)
        forest.append(leaves)
        if leaves.open:
            unfinished = True
    return tuple(forest)


def write_cubes(path: Path, cubes: list[tuple[int, ...]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as output:
        for cube in cubes:
            output.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        parser.error(f"refusing to overwrite {manifest_path}")

    cubes = read_cubes(arguments.cubes)
    result_bytes = arguments.results.read_bytes()
    grouped = read_rows_bytes(result_bytes, len(cubes))
    forest = reconstruct_forest(cubes, grouped)
    closed = [cube for leaves in forest for cube in leaves.closed]
    open_cubes = [cube for leaves in forest for cube in leaves.open]
    closed_path = output / "closed.icnf"
    open_path = output / "open.icnf"
    snapshot_path = output / "results.snapshot.tsv"
    write_cubes(closed_path, closed)
    write_cubes(open_path, open_cubes)
    snapshot_path.write_bytes(result_bytes)

    closed_offset = open_offset = 0
    roots: list[dict[str, int]] = []
    for leaves in forest:
        roots.append(
            {
                "root": leaves.root,
                "rows": leaves.rows,
                "closed_start": closed_offset,
                "closed_count": len(leaves.closed),
                "open_start": open_offset,
                "open_count": len(leaves.open),
            }
        )
        closed_offset += len(leaves.closed)
        open_offset += len(leaves.open)
    manifest = {
        "schema": SCHEMA,
        "source_cubes": {
            "path": str(arguments.cubes),
            "sha256": file_sha256(arguments.cubes),
            "count": len(cubes),
        },
        "source_results": {
            "path": str(arguments.results),
            "snapshot": snapshot_path.name,
            "sha256": sha256_bytes(result_bytes),
        },
        "closed": {
            "path": closed_path.name,
            "sha256": file_sha256(closed_path),
            "count": len(closed),
        },
        "open": {
            "path": open_path.name,
            "sha256": file_sha256(open_path),
            "count": len(open_cubes),
        },
        "roots": roots,
    }
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_manifest.replace(manifest_path)
    print(
        json.dumps(
            {
                "roots": len(cubes),
                "rows": sum(leaves.rows for leaves in forest),
                "closed": len(closed),
                "open": len(open_cubes),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
