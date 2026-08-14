#!/usr/bin/env python3
"""Independently verify exact order-45 fixed-star DIMACS benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterator


SCHEMA = "ramsey55.order45-benchmarks.v1"


def edge_variable(u: int, v: int) -> int:
    if u > v:
        u, v = v, u
    return v * (v - 1) // 2 + u + 1


def expected_clauses(order: int, degree: int) -> Iterator[tuple[int, ...]]:
    for vertices in itertools.combinations(range(order), 5):
        edges = tuple(
            edge_variable(u, v) for u, v in itertools.combinations(vertices, 2)
        )
        yield tuple(-edge for edge in edges)
        yield edges
    for vertex in range(1, order):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_exact_cnf(path: Path, order: int, degree: int) -> tuple[int, int]:
    variables = order * (order - 1) // 2
    clause_count = 2 * _binomial(order, 5) + order - 1
    with path.open("r", encoding="ascii") as stream:
        header = stream.readline().split()
        if header != ["p", "cnf", str(variables), str(clause_count)]:
            raise ValueError(f"{path}: incorrect DIMACS header")
        for index, expected in enumerate(expected_clauses(order, degree)):
            fields = stream.readline().split()
            if not fields:
                raise ValueError(f"{path}: missing clause {index}")
            if fields[-1] != "0":
                raise ValueError(f"{path}: clause {index} lacks terminator")
            actual = tuple(map(int, fields[:-1]))
            if actual != expected:
                raise ValueError(f"{path}: clause {index} differs from exact encoding")
        if stream.readline():
            raise ValueError(f"{path}: extra data after expected clauses")
    return variables, clause_count


def verify_manifest(path: Path, cnf_dir: Path | None = None) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unexpected order-45 manifest schema")
    if manifest.get("order") != 45:
        raise ValueError("manifest does not describe order 45")
    if manifest.get("degree_window") != [20, 24]:
        raise ValueError("manifest has the wrong degree window")
    if manifest.get("normalized_degree_branches") != [20, 22]:
        raise ValueError("manifest does not cover the two normalized branches")
    records = manifest.get("files")
    if not isinstance(records, list) or [item.get("degree") for item in records] != [20, 22]:
        raise ValueError("manifest file records are missing or reordered")
    artifact_root = cnf_dir if cnf_dir is not None else path.parent
    for record in records:
        cnf = artifact_root / record["path"]
        variables, clauses = verify_exact_cnf(cnf, 45, record["degree"])
        if record.get("variables") != variables or record.get("clauses") != clauses:
            raise ValueError(f"{cnf}: manifest count mismatch")
        if record.get("sha256") != file_sha256(cnf):
            raise ValueError(f"{cnf}: SHA-256 mismatch")
        print(
            f"verified {cnf}: degree={record['degree']} "
            f"variables={variables} clauses={clauses}"
        )


def _binomial(n: int, k: int) -> int:
    if k < 0 or n < k:
        return 0
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cnf-dir",
        type=Path,
        help="directory containing CNFs when the manifest is stored separately",
    )
    arguments = parser.parse_args()
    verify_manifest(arguments.manifest, arguments.cnf_dir)


if __name__ == "__main__":
    main()
