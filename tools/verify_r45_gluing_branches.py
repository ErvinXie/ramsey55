#!/usr/bin/env python3
"""Independently reconstruct generalized-graph R(4,5,24) gluing CNFs."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections.abc import Iterator
from pathlib import Path

SCHEMA = "ramsey55.r45-gluing-branches.v1"
ORDER = 24
VARIABLES = 276
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


def independent_edge_variable(first: int, second: int) -> int:
    low, high = sorted((first, second))
    if low < 0 or low == high or high >= ORDER:
        raise ValueError("invalid edge")
    return high * (high - 1) // 2 + low + 1


def independent_decode(code: int, size: int) -> list[list[int]]:
    entries: list[int] = []
    value = code
    while value >= 3:
        entries.insert(0, value % 3)
        value //= 3
    if value != 1 or len(entries) != size * (size - 1) // 2:
        raise ValueError("invalid generalized graph encoding")
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    cursor = iter(entries)
    for first in range(size):
        for second in range(first + 1, size):
            color = next(cursor)
            matrix[first][second] = color
            matrix[second][first] = color
    return matrix


def read_codes(path: Path, size: int) -> list[int]:
    codes = [int(line.split()[0]) for line in path.read_text(encoding="ascii").splitlines()]
    if not codes:
        raise ValueError(f"{path}: empty cover")
    for code in codes:
        independent_decode(code, size)
    return codes


def expected_clauses(
    split: int,
    left: list[list[int]],
    right: list[list[int]],
) -> Iterator[tuple[int, ...]]:
    for clique_size, forbidden in ((4, 1), (5, 2)):
        polarity = -1 if forbidden == 1 else 1
        for clique in itertools.combinations(range(ORDER), clique_size):
            literals: list[int] = []
            valid = True
            for first, second in itertools.combinations(clique, 2):
                if second < split:
                    color = left[first][second]
                elif first >= split:
                    color = right[first - split][second - split]
                else:
                    color = 0
                if color == 0:
                    literals.append(polarity * independent_edge_variable(first, second))
                elif color != forbidden:
                    valid = False
                    break
            if valid:
                yield tuple(literals)


def verify_cnf(
    path: Path,
    record: dict[str, object],
    split: int,
    left: list[list[int]],
    right: list[list[int]],
) -> None:
    clause_total = int(record["clauses"])
    with path.open(encoding="ascii") as stream:
        if stream.readline().split() != ["p", "cnf", str(VARIABLES), str(clause_total)]:
            raise ValueError(f"{path}: incorrect DIMACS header")
        rebuilt = 0
        for rebuilt, clause in enumerate(expected_clauses(split, left, right), 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0":
                raise ValueError(f"{path}: missing or unterminated clause {rebuilt}")
            if tuple(map(int, fields[:-1])) != clause:
                raise ValueError(f"{path}: clause {rebuilt} differs")
        if rebuilt != clause_total:
            raise ValueError(
                f"{path}: manifest has {clause_total} clauses, rebuilt {rebuilt}"
            )
        if stream.readline():
            raise ValueError(f"{path}: extra data")
    if file_sha256(path) != record.get("sha256"):
        raise ValueError(f"{path}: SHA-256 mismatch")


def verify_manifest(
    manifest_path: Path,
    cover_dir: Path,
    cnf_dir: Path | None = None,
    archive_path: Path | None = None,
) -> None:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected gluing manifest schema")
    degree = document.get("fixed_star_degree")
    if (
        degree not in DEGREE_SOURCES
        or document.get("order") != ORDER
        or document.get("ramsey_parameters") != [4, 5]
        or document.get("variables") != VARIABLES
    ):
        raise ValueError("incorrect gluing branch scope")
    left_name, left_size, right_name, right_size = DEGREE_SOURCES[int(degree)]
    covers = document.get("covers")
    if not isinstance(covers, list) or len(covers) != 2:
        raise ValueError("incorrect cover records")
    expected_sources = ((left_name, left_size), (right_name, right_size))
    code_sets: list[list[int]] = []
    for record, (name, size) in zip(covers, expected_sources, strict=True):
        path = cover_dir / name
        codes = read_codes(path, size)
        if (
            record.get("file") != name
            or record.get("order") != size
            or record.get("rows") != len(codes)
            or record.get("sha256") != file_sha256(path)
        ):
            raise ValueError(f"{name}: cover metadata mismatch")
        code_sets.append(codes)
    left_codes, right_codes = code_sets
    total_pairs = len(left_codes) * len(right_codes)
    interval = document.get("pair_interval")
    if (
        not isinstance(interval, list)
        or len(interval) != 2
        or not all(isinstance(value, int) for value in interval)
        or not 0 <= interval[0] < interval[1] <= total_pairs
        or document.get("total_pairs") != total_pairs
    ):
        raise ValueError("invalid Cartesian pair interval")

    archive = document.get("archive")
    if archive_path is not None and (
        not isinstance(archive, dict)
        or archive.get("sha256") != file_sha256(archive_path)
    ):
        raise ValueError("cover archive SHA-256 mismatch")

    records = document.get("files")
    expected_indices = list(range(interval[0], interval[1]))
    if (
        not isinstance(records, list)
        or [record.get("pair_index") for record in records] != expected_indices
    ):
        raise ValueError("branch records do not match pair interval")
    root = cnf_dir or manifest_path.parent
    for record in records:
        pair_index = int(record["pair_index"])
        left_index, right_index = divmod(pair_index, len(right_codes))
        if (
            record.get("left_index") != left_index
            or record.get("right_index") != right_index
            or record.get("left_code") != str(left_codes[left_index])
            or record.get("right_code") != str(right_codes[right_index])
            or record.get("variables") != VARIABLES
        ):
            raise ValueError(f"pair {pair_index}: source binding mismatch")
        expected_name = (
            f"r45-glue-d{degree:02d}-i{left_index:05d}-j{right_index:05d}.cnf"
        )
        if record.get("path") != expected_name:
            raise ValueError(f"pair {pair_index}: unexpected CNF name")
        verify_cnf(
            root / expected_name,
            record,
            left_size,
            independent_decode(left_codes[left_index], left_size),
            independent_decode(right_codes[right_index], right_size),
        )
        print(
            f"verified pair {pair_index}/{total_pairs}: {expected_name} "
            f"clauses={record['clauses']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cover-dir", type=Path, required=True)
    parser.add_argument("--cnf-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    arguments = parser.parse_args()
    verify_manifest(
        arguments.manifest,
        arguments.cover_dir,
        arguments.cnf_dir,
        arguments.archive,
    )


if __name__ == "__main__":
    main()
