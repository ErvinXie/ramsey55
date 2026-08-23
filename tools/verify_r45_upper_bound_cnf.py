#!/usr/bin/env python3
"""Independently reconstruct and verify the direct R(4,5,25) CNF."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path


SCHEMA = "ramsey55.r45-upper-bound.v1"


def independent_edge_variable(left: int, right: int) -> int:
    if not 0 <= left < right:
        raise ValueError("expected an increasing nonnegative edge")
    return right * (right - 1) // 2 + left + 1


def expected_clauses(order: int):
    for vertices in itertools.combinations(range(order), 4):
        yield tuple(
            -independent_edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertices in itertools.combinations(range(order), 5):
        yield tuple(
            independent_edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    arguments = parser.parse_args()
    record = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if record.get("schema") != SCHEMA:
        raise ValueError("unexpected manifest schema")
    if (record.get("order"), record.get("red_clique"), record.get("blue_clique")) != (
        25,
        4,
        5,
    ):
        raise ValueError("unexpected Ramsey instance")
    order = int(record["order"])
    variables = comb(order, 2)
    clauses = comb(order, 4) + comb(order, 5)
    if record.get("variables") != variables or record.get("clauses") != clauses:
        raise ValueError("incorrect manifest dimensions")
    path = (arguments.cnf_dir or arguments.manifest.parent) / str(record["path"])
    with path.open("r", encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(variables), str(clauses)]:
            raise ValueError("incorrect DIMACS header")
        count = 0
        for count, expected in enumerate(expected_clauses(order), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0":
                raise ValueError(f"clause {count} is missing or unterminated")
            if tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"clause {count} differs")
        if count != clauses or stream.readline():
            raise ValueError("incorrect clause count")
    digest = sha256(path)
    if digest != record.get("sha256"):
        raise ValueError("CNF hash differs")
    print(f"verified {path}: variables={variables} clauses={count} sha256={digest}")


if __name__ == "__main__":
    main()
