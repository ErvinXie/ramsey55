#!/usr/bin/env python3
"""Independently reconstruct the degree-strengthened order-45 CNFs."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


SCHEMA = "ramsey55.order45-strengthened-benchmarks.v1"


def edge_variable(u: int, v: int) -> int:
    if u > v:
        u, v = v, u
    return v * (v - 1) // 2 + u + 1


def base_clauses(degree: int):
    for vertices in itertools.combinations(range(45), 5):
        edges = tuple(
            edge_variable(u, v) for u, v in itertools.combinations(vertices, 2)
        )
        yield tuple(-edge for edge in edges)
        yield edges
    for vertex in range(1, 45):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def independent_range_encoding(
    inputs: tuple[int, ...], lower: int, upper: int, maximum_variable: int
) -> tuple[int, list[tuple[int, ...]]]:
    """Second implementation of the explicit counter recurrence."""

    width = min(len(inputs), upper + 1)
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
    clauses += [(table[len(inputs), lower],), (-table[len(inputs), upper + 1],)]
    return variable, clauses


def expected_clauses(degree: int):
    yield from base_clauses(degree)
    maximum = 45 * 44 // 2
    for vertex in range(1, 45):
        incident = tuple(
            edge_variable(vertex, other) for other in range(45) if other != vertex
        )
        maximum, clauses = independent_range_encoding(incident, 20, 24, maximum)
        yield from clauses


def verify_file(path: Path, record: dict[str, object]) -> None:
    expected_variables = int(record["variables"])
    expected_count = int(record["clauses"])
    with path.open("r", encoding="ascii") as stream:
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
            raise ValueError(f"{path}: expected {expected_count} clauses, rebuilt {count}")
        if stream.readline():
            raise ValueError(f"{path}: extra data")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(manifest_path: Path, cnf_dir: Path | None) -> None:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected strengthened manifest schema")
    if document.get("order") != 45 or document.get("degree_window") != [20, 24]:
        raise ValueError("incorrect strengthened benchmark scope")
    records = document.get("files")
    if not isinstance(records, list) or [item.get("degree") for item in records] != [20, 22]:
        raise ValueError("strengthened manifest does not cover d20 and d22")
    root = cnf_dir or manifest_path.parent
    for record in records:
        path = root / str(record["path"])
        verify_file(path, record)
        if sha256(path) != record.get("sha256"):
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
