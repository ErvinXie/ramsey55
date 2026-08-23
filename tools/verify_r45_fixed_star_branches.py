#!/usr/bin/env python3
"""Independently verify every fixed-star R(4,5,25) branch."""

from __future__ import annotations

import argparse
import hashlib
import json
from math import comb
from pathlib import Path

from tools.verify_r45_upper_bound_cnf import expected_clauses


SCHEMA = "ramsey55.r45-fixed-star-branches.v1"
BASE_SCHEMA = "ramsey55.r45-upper-bound.v1"
ORDER = 25


def edge_from_zero(vertex: int) -> int:
    if not 1 <= vertex < ORDER:
        raise ValueError("fixed-star endpoint outside graph")
    return vertex * (vertex - 1) // 2 + 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_branch(path: Path, record: dict[str, object]) -> None:
    degree = int(record["degree"])
    variables = comb(ORDER, 2)
    clause_count = comb(ORDER, 4) + comb(ORDER, 5) + ORDER - 1
    if record.get("variables") != variables or record.get("clauses") != clause_count:
        raise ValueError(f"d{degree}: incorrect dimensions")
    with path.open("r", encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(variables), str(clause_count)]:
            raise ValueError(f"d{degree}: incorrect header")
        count = 0
        for count, expected in enumerate(expected_clauses(ORDER), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0" or tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"d{degree}: base clause {count} differs")
        for vertex in range(1, ORDER):
            count += 1
            variable = edge_from_zero(vertex)
            expected = (variable,) if vertex <= degree else (-variable,)
            fields = stream.readline().split()
            if not fields or fields[-1] != "0" or tuple(map(int, fields[:-1])) != expected:
                raise ValueError(f"d{degree}: fixed clause at vertex {vertex} differs")
        if count != clause_count or stream.readline():
            raise ValueError(f"d{degree}: incorrect clause count")
    if sha256(path) != record.get("sha256"):
        raise ValueError(f"d{degree}: hash differs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA or document.get("base_schema") != BASE_SCHEMA:
        raise ValueError("unexpected manifest schema")
    records = document.get("records")
    if not isinstance(records, list) or [record.get("degree") for record in records] != list(
        range(ORDER)
    ):
        raise ValueError("branch family does not contain degrees 0 through 24 exactly once")
    root = arguments.cnf_dir or arguments.manifest.parent
    for record in records:
        verify_branch(root / str(record["path"]), record)
    print(f"verified {len(records)} fixed-star branches")


if __name__ == "__main__":
    main()
