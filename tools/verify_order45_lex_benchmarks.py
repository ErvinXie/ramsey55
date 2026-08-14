#!/usr/bin/env python3
"""Independently reconstruct the degree-bounded cross-row lex formulas."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verify_order45_strengthened_benchmarks import edge_variable, expected_clauses


SCHEMA = "ramsey55.order45-lex-benchmarks.v1"


def independent_lex(left, right, maximum):
    clauses = []
    prefix = None
    for index in range(len(left)):
        x, y = left[index], right[index]
        clauses.append((-x, y) if prefix is None else (-prefix, -x, y))
        if index == len(left) - 1:
            break
        maximum += 1
        next_prefix = maximum
        if prefix is not None:
            clauses.append((-next_prefix, prefix))
        clauses += [(-next_prefix, -x, y), (-next_prefix, x, -y)]
        if prefix is None:
            clauses += [(-x, -y, next_prefix), (x, y, next_prefix)]
        else:
            clauses += [
                (-prefix, -x, -y, next_prefix),
                (-prefix, x, y, next_prefix),
            ]
        prefix = next_prefix
    return maximum, clauses


def all_expected(degree):
    yield from expected_clauses(degree)
    maximum = 36190
    cross = range(degree + 1, 45)
    rows = [tuple(edge_variable(a, b) for b in cross) for a in range(1, degree + 1)]
    for left, right in zip(rows, rows[1:]):
        maximum, clauses = independent_lex(left, right, maximum)
        yield from clauses


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path, record):
    variables, clause_count = record["variables"], record["clauses"]
    with path.open("r", encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(variables), str(clause_count)]:
            raise ValueError(f"{path}: bad header")
        rebuilt = 0
        for rebuilt, expected in enumerate(all_expected(record["degree"]), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0" or tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"{path}: clause {rebuilt} differs")
        if rebuilt != clause_count or stream.readline():
            raise ValueError(f"{path}: clause count or trailing data differs")
    if sha256(path) != record["sha256"]:
        raise ValueError(f"{path}: SHA-256 mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected lex manifest schema")
    records = document.get("files")
    if not isinstance(records, list) or [item.get("degree") for item in records] != [20, 22]:
        raise ValueError("lex manifest does not cover d20 and d22")
    root = arguments.cnf_dir or arguments.manifest.parent
    for record in records:
        path = root / record["path"]
        verify_file(path, record)
        print(f"verified {path}: variables={record['variables']} clauses={record['clauses']}")


if __name__ == "__main__":
    main()
