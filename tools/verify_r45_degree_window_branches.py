#!/usr/bin/env python3
"""Independently reconstruct the degree-window R(4,5,25) branch CNFs."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections.abc import Iterator
from pathlib import Path

SCHEMA = "ramsey55.r45-degree-window-branches.v1"
ORDER = 25
PRIMARY_VARIABLES = 300
BASE_CLAUSES = 65780
LOWER_DEGREE = 7
UPPER_DEGREE = 13
ALLOWED_DEGREES = {8, 10, 12}
RAW_HASHES = {
    8: "8c0935f6f795dfb059e6f9c5ba3bd1ae48856e90d3b652b7a81886629b6744db",
    10: "974750e1771b1d81687d075faa112f545a7fab34dd4148358ed40755def51339",
    12: "f9864879bd1e57f1f0448d89373be24b44cb6228dc299a6ae75c78febc798e7d",
}


def edge_variable(left: int, right: int) -> int:
    if left == right or min(left, right) < 0:
        raise ValueError("invalid edge")
    if left > right:
        left, right = right, left
    return right * (right - 1) // 2 + left + 1


def raw_branch_clauses(degree: int) -> Iterator[tuple[int, ...]]:
    for vertices in itertools.combinations(range(ORDER), 4):
        yield tuple(
            -edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertices in itertools.combinations(range(ORDER), 5):
        yield tuple(
            edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertex in range(1, ORDER):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def independent_range_encoding(
    inputs: tuple[int, ...],
    lower: int,
    upper: int,
    maximum_variable: int,
) -> tuple[int, list[tuple[int, ...]]]:
    """Second implementation of the bidirectional counter recurrence."""
    width = min(len(inputs), max(lower, upper + 1))
    table: dict[tuple[int, int], int] = {}
    clauses: list[tuple[int, ...]] = []
    variable = maximum_variable
    for prefix, item in enumerate(inputs, start=1):
        for count in range(1, min(prefix, width) + 1):
            variable += 1
            table[prefix, count] = variable
            current = variable
            if prefix == count == 1:
                clauses += [(-current, item), (-item, current)]
            elif count == 1:
                old = table[prefix - 1, 1]
                clauses += [(-old, current), (-item, current), (-current, old, item)]
            elif count == prefix:
                diagonal = table[prefix - 1, count - 1]
                clauses += [
                    (-current, diagonal),
                    (-current, item),
                    (-diagonal, -item, current),
                ]
            else:
                old = table[prefix - 1, count]
                diagonal = table[prefix - 1, count - 1]
                clauses += [
                    (-old, current),
                    (-diagonal, -item, current),
                    (-current, old, diagonal),
                    (-current, old, item),
                ]
    clauses += [
        (table[len(inputs), lower],),
        (-table[len(inputs), upper + 1],),
    ]
    return variable, clauses


def expected_clauses(degree: int) -> Iterator[tuple[int, ...]]:
    yield from raw_branch_clauses(degree)
    maximum_variable = PRIMARY_VARIABLES
    for vertex in range(1, ORDER):
        incident = tuple(
            edge_variable(vertex, other)
            for other in range(ORDER)
            if other != vertex
        )
        maximum_variable, clauses = independent_range_encoding(
            incident,
            LOWER_DEGREE,
            UPPER_DEGREE,
            maximum_variable,
        )
        yield from clauses


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, record: dict[str, object]) -> None:
    expected_variables = int(record["variables"])
    expected_count = int(record["clauses"])
    with path.open(encoding="ascii") as stream:
        header = stream.readline().split()
        if header != ["p", "cnf", str(expected_variables), str(expected_count)]:
            raise ValueError(f"{path}: incorrect DIMACS header")
        count = 0
        for count, expected in enumerate(expected_clauses(int(record["degree"])), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0":
                raise ValueError(f"{path}: missing or unterminated clause {count}")
            if tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"{path}: clause {count} differs")
        if count != expected_count:
            raise ValueError(
                f"{path}: expected {expected_count} clauses, rebuilt {count}"
            )
        if stream.readline():
            raise ValueError(f"{path}: extra data")


def verify_manifest(manifest_path: Path, cnf_dir: Path | None = None) -> None:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected degree-window manifest schema")
    if (
        document.get("order") != ORDER
        or document.get("primary_variables") != PRIMARY_VARIABLES
        or document.get("degree_window") != [LOWER_DEGREE, UPPER_DEGREE]
        or document.get("bounded_vertices") != [1, ORDER - 1]
    ):
        raise ValueError("incorrect degree-window benchmark scope")
    degrees = document.get("fixed_star_degrees")
    records = document.get("files")
    if (
        not isinstance(degrees, list)
        or not degrees
        or len(set(degrees)) != len(degrees)
        or not set(degrees) <= ALLOWED_DEGREES
        or not isinstance(records, list)
        or [record.get("degree") for record in records] != degrees
    ):
        raise ValueError("invalid degree-window branch family")
    root = cnf_dir or manifest_path.parent
    for record in records:
        degree = int(record["degree"])
        if record.get("raw_sha256") != RAW_HASHES[degree]:
            raise ValueError(f"d{degree:02d}: raw CNF hash mismatch")
        path = root / str(record["path"])
        verify_file(path, record)
        if file_sha256(path) != record.get("sha256"):
            raise ValueError(f"{path}: SHA-256 mismatch")
        print(
            f"verified {path}: variables={record['variables']} "
            f"clauses={record['clauses']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    arguments = parser.parse_args()
    verify_manifest(arguments.manifest, arguments.cnf_dir)


if __name__ == "__main__":
    main()
