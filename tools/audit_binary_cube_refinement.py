#!/usr/bin/env python3
"""Audit that each parent cube was replaced by one complementary child pair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

try:
    from tools.export_proof_frontier import read_cubes
except ModuleNotFoundError:
    from export_proof_frontier import read_cubes


SCHEMA = "ramsey55.binary-cube-refinement.v1"
HEADER = ("cube", "status", "split", "seconds", "model")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_splits(path: Path, count: int) -> tuple[int, ...]:
    splits: list[int] = []
    with path.open(newline="", encoding="ascii") as stream:
        rows = csv.reader(stream, delimiter="\t")
        if tuple(next(rows, ())) != HEADER:
            raise ValueError("unexpected refinement result header")
        for expected, fields in enumerate(rows):
            if len(fields) != len(HEADER) or int(fields[0]) != expected:
                raise ValueError("invalid refinement result row")
            status, split = map(int, fields[1:3])
            seconds = float(fields[3])
            if status != 0 or split == 0 or seconds < 0 or fields[4]:
                raise ValueError("refinement must record one UNKNOWN split per parent")
            splits.append(split)
    if len(splits) != count:
        raise ValueError("parent/result count mismatch")
    return tuple(splits)


def audit(
    parents: tuple[tuple[int, ...], ...],
    children: tuple[tuple[int, ...], ...],
    splits: tuple[int, ...],
) -> None:
    if len(children) != 2 * len(parents):
        raise ValueError("binary refinement child count mismatch")
    for index, (parent, split) in enumerate(zip(parents, splits, strict=True)):
        if any(abs(literal) == abs(split) for literal in parent):
            raise ValueError(f"split repeats a parent variable at index {index}")
        if children[2 * index] != parent + (split,):
            raise ValueError(f"positive child mismatch at index {index}")
        if children[2 * index + 1] != parent + (-split,):
            raise ValueError(f"negative child mismatch at index {index}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", type=Path)
    parser.add_argument("children", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    parents = read_cubes(arguments.parents)
    children = read_cubes(arguments.children)
    splits = read_splits(arguments.results, len(parents))
    audit(parents, children, splits)
    document = {
        "schema": SCHEMA,
        "parents": {
            "path": str(arguments.parents),
            "sha256": file_sha256(arguments.parents),
            "count": len(parents),
        },
        "children": {
            "path": str(arguments.children),
            "sha256": file_sha256(arguments.children),
            "count": len(children),
        },
        "results": {
            "path": str(arguments.results),
            "sha256": file_sha256(arguments.results),
        },
        "splits": list(splits),
        "complete_binary_refinement": True,
    }
    if arguments.manifest is not None:
        temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
        temporary.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(arguments.manifest)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
