#!/usr/bin/env python3
"""Independently reconstruct the unique-H100 d20 formula."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from verify_order45_excess_benchmarks import lower_counter
from verify_order45_strengthened_benchmarks import edge_variable, expected_clauses


SCHEMA = "ramsey55.order45-fixed-h100.v1"


def decode_short_graph6(record: str) -> tuple[int, dict[tuple[int, int], bool]]:
    values = [ord(character) - 63 for character in record]
    if not values or any(value < 0 or value > 63 for value in values):
        raise ValueError("invalid short graph6 record")
    order = values[0]
    bits = [
        (value >> shift) & 1
        for value in values[1:]
        for shift in range(5, -1, -1)
    ]
    needed = order * (order - 1) // 2
    if len(bits) < needed or any(bits[needed:]):
        raise ValueError("truncated graph6 record or nonzero padding")
    edges: dict[tuple[int, int], bool] = {}
    index = 0
    for right in range(1, order):
        for left in range(right):
            edges[left, right] = bool(bits[index])
            index += 1
    return order, edges


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected fixed-H100 manifest schema")
    catalog = Path(document["catalog"])
    if file_sha256(catalog) != document["catalog_sha256"]:
        raise ValueError("H100 catalog hash differs")
    order, edges = decode_short_graph6(document["graph6"])
    if order != 20 or sum(edges.values()) != 100:
        raise ValueError("bad H100 graph6 record")

    fixed_h = []
    for left, right in itertools.combinations(range(20), 2):
        variable = edge_variable(left + 1, right + 1)
        fixed_h.append((variable,) if edges[left, right] else (-variable,))
    j_literals = tuple(
        -edge_variable(left, right)
        for left, right in itertools.combinations(range(21, 45), 2)
    )
    maximum, dense_j = lower_counter(j_literals, 126, 36190)
    expected = itertools.chain(expected_clauses(20), fixed_h, dense_j)
    path = arguments.cnf or arguments.manifest.parent / document["path"]
    with path.open(encoding="ascii") as stream:
        expected_header = ["p", "cnf", str(maximum), str(document["clauses"])]
        if stream.readline().split() != expected_header:
            raise ValueError("bad DIMACS header")
        count = 0
        for count, clause in enumerate(expected, 1):
            fields = stream.readline().split()
            if (
                not fields
                or fields[-1] != "0"
                or tuple(map(int, fields[:-1])) != clause
            ):
                raise ValueError(f"clause {count} differs")
        if count != document["clauses"] or stream.readline():
            raise ValueError("bad clause count")
    if maximum != document["variables"] or file_sha256(path) != document["sha256"]:
        raise ValueError("variable count or CNF hash differs")
    print(f"verified unique H100 formula: {maximum} variables, {count} clauses")


if __name__ == "__main__":
    main()
