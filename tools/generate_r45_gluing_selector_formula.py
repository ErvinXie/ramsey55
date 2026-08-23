#!/usr/bin/env python3
"""Combine every generalized-graph gluing pair into one selector CNF."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections.abc import Iterator
from pathlib import Path

SCHEMA = "ramsey55.r45-gluing-selector-formula.v1"
ORDER = 24
EDGE_VARIABLES = ORDER * (ORDER - 1) // 2
DEGREE_SOURCES = {
    8: ("gen358", 8, "gen4416", 16),
    10: ("gen3510", 10, "gen4414", 14),
    12: ("gen3512", 12, "gen4412", 12),
}
SOURCE_URL = "http://grid01.ciirc.cvut.cz/~thibault/gen.tar.gz"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def edge_variable(left: int, right: int) -> int:
    if left > right:
        left, right = right, left
    if left < 0 or left == right or right >= ORDER:
        raise ValueError("invalid edge")
    return right * (right - 1) // 2 + left + 1


def decode_generalized_graph(code: int, size: int) -> tuple[int, ...]:
    digits: list[int] = []
    value = code
    while value >= 3:
        digits.append(value % 3)
        value //= 3
    digits.reverse()
    if value != 1 or len(digits) != size * (size - 1) // 2:
        raise ValueError("invalid generalized-graph code")
    return tuple(digits)


def read_cover(path: Path, size: int) -> list[tuple[int, tuple[int, ...]]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        fields = line.split()
        if not fields:
            raise ValueError(f"{path}:{line_number}: empty cover row")
        try:
            code = int(fields[0])
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: invalid graph code") from error
        rows.append((code, decode_generalized_graph(code, size)))
    if not rows:
        raise ValueError(f"{path}: empty cover")
    return rows


def base_ramsey_clauses() -> Iterator[tuple[int, ...]]:
    for clique_size, sign in ((4, -1), (5, 1)):
        for vertices in itertools.combinations(range(ORDER), clique_size):
            yield tuple(
                sign * edge_variable(left, right)
                for left, right in itertools.combinations(vertices, 2)
            )


def selector_clauses(
    rows: list[tuple[int, tuple[int, ...]]],
    size: int,
    offset: int,
    first_selector: int,
) -> Iterator[tuple[int, ...]]:
    yield tuple(range(first_selector, first_selector + len(rows)))
    local_edges = tuple(itertools.combinations(range(size), 2))
    for row_index, (_, colors) in enumerate(rows):
        selector = first_selector + row_index
        for (left, right), color in zip(local_edges, colors, strict=True):
            if color == 0:
                continue
            variable = edge_variable(left + offset, right + offset)
            required_literal = variable if color == 1 else -variable
            yield (-selector, required_literal)


def write_formula(
    path: Path,
    split: int,
    left_rows: list[tuple[int, tuple[int, ...]]],
    right_rows: list[tuple[int, tuple[int, ...]]],
) -> tuple[int, int]:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    left_first = EDGE_VARIABLES + 1
    right_first = left_first + len(left_rows)
    variables = EDGE_VARIABLES + len(left_rows) + len(right_rows)
    clauses = tuple(base_ramsey_clauses())
    clauses += tuple(selector_clauses(left_rows, split, 0, left_first))
    clauses += tuple(
        selector_clauses(right_rows, ORDER - split, split, right_first)
    )
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {len(clauses)}\n")
        for clause in clauses:
            output.write(" ".join(map(str, clause)))
            output.write(" 0\n")
    return variables, len(clauses)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover-dir", type=Path, required=True)
    parser.add_argument("--degree", type=int, choices=DEGREE_SOURCES, default=8)
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/r45-gluing-selector-v1")
    )
    arguments = parser.parse_args()
    manifest_path = arguments.output_dir / "manifest.json"
    if manifest_path.exists():
        parser.error(f"refusing to overwrite {manifest_path}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    left_name, left_size, right_name, right_size = DEGREE_SOURCES[arguments.degree]
    left_path = arguments.cover_dir / left_name
    right_path = arguments.cover_dir / right_name
    left_rows = read_cover(left_path, left_size)
    right_rows = read_cover(right_path, right_size)
    cnf_path = arguments.output_dir / f"r45-gluing-d{arguments.degree:02d}-selector.cnf"
    variables, clauses = write_formula(
        cnf_path, left_size, left_rows, right_rows
    )
    archive = None
    if arguments.archive is not None:
        archive = {
            "name": arguments.archive.name,
            "sha256": file_sha256(arguments.archive),
            "source_url": SOURCE_URL,
        }
    document = {
        "schema": SCHEMA,
        "claim": "selector formula only; this manifest contains no UNSAT result",
        "order": ORDER,
        "ramsey_parameters": [4, 5],
        "fixed_star_degree": arguments.degree,
        "edge_variables": EDGE_VARIABLES,
        "variables": variables,
        "clauses": clauses,
        "pair_count": len(left_rows) * len(right_rows),
        "selector_semantics": (
            "at least one row per side; selected rows condition every non-hole edge"
        ),
        "cnf": {
            "path": cnf_path.name,
            "bytes": cnf_path.stat().st_size,
            "sha256": file_sha256(cnf_path),
        },
        "archive": archive,
        "covers": [
            {
                "side": "R(3,5)",
                "file": left_name,
                "order": left_size,
                "rows": len(left_rows),
                "first_selector": EDGE_VARIABLES + 1,
                "sha256": file_sha256(left_path),
            },
            {
                "side": "R(4,4)",
                "file": right_name,
                "order": right_size,
                "rows": len(right_rows),
                "first_selector": EDGE_VARIABLES + 1 + len(left_rows),
                "sha256": file_sha256(right_path),
            },
        ],
    }
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {cnf_path}: variables={variables} clauses={clauses} "
        f"sha256={document['cnf']['sha256']}"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
