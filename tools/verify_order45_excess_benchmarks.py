#!/usr/bin/env python3
"""Independently reconstruct the complete order-45 excess-witness cover."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from verify_order45_lex_benchmarks import independent_lex
from verify_order45_strengthened_benchmarks import edge_variable, expected_clauses


SCHEMA = "ramsey55.order45-excess-witness-benchmarks.v1"
THRESHOLDS = {20: 226, 21: 222, 22: 220}


def lower_counter(inputs, lower, maximum):
    table = {}
    clauses = []
    for prefix, item in enumerate(inputs, 1):
        for count in range(1, min(prefix, lower) + 1):
            maximum += 1
            current = table[prefix, count] = maximum
            if prefix == count == 1:
                clauses += [(-current, item), (-item, current)]
            elif count == 1:
                old = table[prefix - 1, 1]
                clauses += [(-old, current), (-item, current), (-current, old, item)]
            elif count == prefix:
                diagonal = table[prefix - 1, count - 1]
                clauses += [(-current, diagonal), (-current, item),
                            (-diagonal, -item, current)]
            else:
                old, diagonal = table[prefix - 1, count], table[prefix - 1, count - 1]
                clauses += [(-old, current), (-diagonal, -item, current),
                            (-current, old, diagonal), (-current, old, item)]
    clauses.append((table[len(inputs), lower],))
    return maximum, clauses


def all_expected(degree):
    yield from expected_clauses(degree)
    maximum = 36190
    right_vertices = range(degree + 1, 45)
    rows = [tuple(edge_variable(a, b) for b in right_vertices)
            for a in range(1, degree + 1)]
    for left, right in zip(rows, rows[1:]):
        maximum, clauses = independent_lex(left, right, maximum)
        yield from clauses
    neighbours = range(1, degree + 1)
    nonneighbours = range(degree + 1, 45)
    literals = tuple(edge_variable(u, v)
                     for u, v in itertools.combinations(neighbours, 2)) + tuple(
        -edge_variable(u, v)
        for u, v in itertools.combinations(nonneighbours, 2)
    )
    maximum, clauses = lower_counter(literals, THRESHOLDS[degree], maximum)
    yield from clauses


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def verify(path, record):
    with path.open("r", encoding="ascii") as stream:
        header = stream.readline().split()
        if header != ["p", "cnf", str(record["variables"]), str(record["clauses"])]:
            raise ValueError(f"{path}: bad header")
        count = 0
        for count, expected in enumerate(all_expected(record["degree"]), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0" or tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"{path}: clause {count} differs")
        if count != record["clauses"] or stream.readline():
            raise ValueError(f"{path}: bad clause count or trailing data")
    if digest(path) != record["sha256"]:
        raise ValueError(f"{path}: SHA-256 mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    args = parser.parse_args()
    document = json.loads(args.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected excess-witness manifest schema")
    records = document.get("files")
    if not isinstance(records, list) or [r.get("degree") for r in records] != [20, 21, 22]:
        raise ValueError("manifest does not cover d20/d21/d22")
    root = args.cnf_dir or args.manifest.parent
    for record in records:
        path = root / record["path"]
        verify(path, record)
        print(f"verified {path}: variables={record['variables']} clauses={record['clauses']}")


if __name__ == "__main__":
    main()
