#!/usr/bin/env python3
"""Independently rebuild a generalized-graph gluing selector CNF."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections.abc import Iterator
from pathlib import Path

SCHEMA = "ramsey55.r45-gluing-selector-formula.v1"
ORDER = 24
EDGE_VARIABLES = 276
DEGREE_SOURCES = {
    8: ("gen358", 8, "gen4416", 16),
    10: ("gen3510", 10, "gen4414", 14),
    12: ("gen3512", 12, "gen4412", 12),
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def independent_edge(first: int, second: int) -> int:
    low, high = sorted((first, second))
    if low < 0 or low == high or high >= ORDER:
        raise ValueError("invalid edge")
    return high * (high - 1) // 2 + low + 1


def independent_rows(path: Path, size: int) -> list[list[list[int]]]:
    matrices = []
    for line in path.read_text(encoding="ascii").splitlines():
        value = int(line.split()[0])
        colors = []
        while value >= 3:
            colors.insert(0, value % 3)
            value //= 3
        if value != 1 or len(colors) != size * (size - 1) // 2:
            raise ValueError(f"{path}: invalid graph code")
        matrix = [[0] * size for _ in range(size)]
        cursor = iter(colors)
        for first in range(size):
            for second in range(first + 1, size):
                matrix[first][second] = next(cursor)
        matrices.append(matrix)
    if not matrices:
        raise ValueError(f"{path}: empty cover")
    return matrices


def expected_formula(
    split: int,
    left_rows: list[list[list[int]]],
    right_rows: list[list[list[int]]],
) -> Iterator[tuple[int, ...]]:
    for size, polarity in ((4, -1), (5, 1)):
        for vertices in itertools.combinations(range(ORDER), size):
            yield tuple(
                polarity * independent_edge(first, second)
                for first, second in itertools.combinations(vertices, 2)
            )
    left_first = EDGE_VARIABLES + 1
    right_first = left_first + len(left_rows)
    for matrices, size, offset, first_selector in (
        (left_rows, split, 0, left_first),
        (right_rows, ORDER - split, split, right_first),
    ):
        yield tuple(range(first_selector, first_selector + len(matrices)))
        for row_index, matrix in enumerate(matrices):
            selector = first_selector + row_index
            for first in range(size):
                for second in range(first + 1, size):
                    color = matrix[first][second]
                    if color:
                        variable = independent_edge(first + offset, second + offset)
                        yield (-selector, variable if color == 1 else -variable)


def verify(
    manifest_path: Path,
    cover_dir: Path,
    cnf_path: Path | None,
    archive_path: Path | None,
) -> None:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    degree = document.get("fixed_star_degree")
    if (
        document.get("schema") != SCHEMA
        or degree not in DEGREE_SOURCES
        or document.get("order") != ORDER
        or document.get("ramsey_parameters") != [4, 5]
        or document.get("edge_variables") != EDGE_VARIABLES
    ):
        raise ValueError("incorrect selector-formula scope")
    left_name, left_size, right_name, right_size = DEGREE_SOURCES[int(degree)]
    covers = document.get("covers")
    if not isinstance(covers, list) or len(covers) != 2:
        raise ValueError("incorrect cover records")
    rows = []
    for record, (name, size) in zip(
        covers, ((left_name, left_size), (right_name, right_size)), strict=True
    ):
        path = cover_dir / name
        matrices = independent_rows(path, size)
        if (
            record.get("file") != name
            or record.get("order") != size
            or record.get("rows") != len(matrices)
            or record.get("sha256") != file_sha256(path)
        ):
            raise ValueError(f"{name}: cover metadata mismatch")
        rows.append(matrices)
    left_rows, right_rows = rows
    variables = EDGE_VARIABLES + len(left_rows) + len(right_rows)
    expected_selectors = (EDGE_VARIABLES + 1, EDGE_VARIABLES + 1 + len(left_rows))
    if (
        [record.get("first_selector") for record in covers] != list(expected_selectors)
        or document.get("variables") != variables
        or document.get("pair_count") != len(left_rows) * len(right_rows)
    ):
        raise ValueError("selector metadata mismatch")
    archive = document.get("archive")
    if archive_path is not None and (
        not isinstance(archive, dict)
        or archive.get("sha256") != file_sha256(archive_path)
    ):
        raise ValueError("cover archive SHA-256 mismatch")

    cnf = document.get("cnf")
    if not isinstance(cnf, dict):
        raise TypeError("missing or malformed CNF record")
    path = cnf_path or manifest_path.parent / str(cnf.get("path"))
    expected = expected_formula(left_size, left_rows, right_rows)
    clause_count = int(document["clauses"])
    with path.open(encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(variables), str(clause_count)]:
            raise ValueError("incorrect DIMACS header")
        rebuilt = 0
        for rebuilt, clause in enumerate(expected, 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0" or tuple(map(int, fields[:-1])) != clause:
                raise ValueError(f"clause {rebuilt} differs")
        if rebuilt != clause_count or stream.readline():
            raise ValueError("incorrect DIMACS clause count or trailing data")
    if (
        cnf.get("path") != path.name
        or cnf.get("bytes") != path.stat().st_size
        or cnf.get("sha256") != file_sha256(path)
    ):
        raise ValueError("CNF artifact mismatch")
    print(
        f"verified d{degree:02d} selector formula: variables={variables} "
        f"clauses={clause_count} pairs={document['pair_count']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cover-dir", type=Path, required=True)
    parser.add_argument("--cnf", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    verify(arguments.manifest, arguments.cover_dir, arguments.cnf, arguments.archive)


if __name__ == "__main__":
    main()
