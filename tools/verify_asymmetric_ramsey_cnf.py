#!/usr/bin/env python3
"""Independently reconstruct an asymmetric Ramsey upper-bound CNF."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path


SCHEMA = "ramsey55.asymmetric-ramsey-upper-bound.v1"


def independent_edge_variable(left: int, right: int) -> int:
    if not 0 <= left < right:
        raise ValueError("expected an increasing nonnegative edge")
    return right * (right - 1) // 2 + left + 1


def expected_clauses(order: int, red: int, blue: int):
    for vertices in itertools.combinations(range(order), red):
        yield tuple(
            -independent_edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertices in itertools.combinations(range(order), blue):
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
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected manifest schema")
    order = int(document["order"])
    red = int(document["red_clique"])
    blue = int(document["blue_clique"])
    if not 2 <= red <= order or not 2 <= blue <= order:
        raise ValueError("invalid asymmetric Ramsey dimensions")
    variables = comb(order, 2)
    clauses = comb(order, red) + comb(order, blue)
    if document.get("variables") != variables or document.get("clauses") != clauses:
        raise ValueError("manifest dimensions differ")
    path = (arguments.cnf_dir or arguments.manifest.parent) / str(document["path"])
    with path.open("r", encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(variables), str(clauses)]:
            raise ValueError("DIMACS header differs")
        count = 0
        for count, expected in enumerate(expected_clauses(order, red, blue), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0":
                raise ValueError(f"clause {count} is missing or unterminated")
            if tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"clause {count} differs")
        if count != clauses or stream.readline():
            raise ValueError("DIMACS clause count differs")
    digest = sha256(path)
    if document.get("sha256") != digest:
        raise ValueError("CNF hash differs")
    print(
        f"verified {path}: variables={variables} clauses={clauses} sha256={digest}"
    )


if __name__ == "__main__":
    main()
