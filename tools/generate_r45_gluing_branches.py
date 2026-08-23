#!/usr/bin/env python3
"""Materialize Gauthier--Brown generalized-graph gluing branches."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections.abc import Iterator
from pathlib import Path

CONTIGUOUS_SCHEMA = "ramsey55.r45-gluing-branches.v1"
SPARSE_SCHEMA = "ramsey55.r45-gluing-branches.v2"
ORDER = 24
VARIABLES = ORDER * (ORDER - 1) // 2
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
    if left == right or min(left, right) < 0 or max(left, right) >= ORDER:
        raise ValueError("invalid edge")
    if left > right:
        left, right = right, left
    return right * (right - 1) // 2 + left + 1


def decode_generalized_graph(code: int, size: int) -> dict[tuple[int, int], int]:
    """Decode graph.zip_mat's leading-one, row-major base-three format."""
    if code < 1:
        raise ValueError("generalized graph code must be positive")
    digits: list[int] = []
    remainder = code
    while remainder >= 3:
        digits.append(remainder % 3)
        remainder //= 3
    if remainder != 1:
        raise ValueError("generalized graph code has the wrong leading digit")
    digits.reverse()
    edges = [(left, right) for left in range(size) for right in range(left + 1, size)]
    if len(digits) != len(edges):
        raise ValueError(
            f"generalized graph has {len(digits)} ternary entries, expected {len(edges)}"
        )
    return dict(zip(edges, digits, strict=True))


def read_cover(path: Path, size: int) -> list[int]:
    codes: list[int] = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields:
                raise ValueError(f"{path}:{line_number}: empty cover row")
            try:
                code = int(fields[0])
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid generalized graph code"
                ) from error
            decode_generalized_graph(code, size)
            codes.append(code)
    if not codes:
        raise ValueError(f"{path}: empty generalized-graph cover")
    return codes


def fixed_color(
    edge: tuple[int, int],
    split: int,
    left: dict[tuple[int, int], int],
    right: dict[tuple[int, int], int],
) -> int:
    first, second = edge
    if second < split:
        return left[edge]
    if first >= split:
        return right[(first - split, second - split)]
    return 0


def reduced_ramsey_clauses(
    split: int,
    left: dict[tuple[int, int], int],
    right: dict[tuple[int, int], int],
) -> Iterator[tuple[int, ...]]:
    """Substitute both diagonal blocks into the R(4,5,24) CNF."""
    for clique_size, target_color in ((4, 1), (5, 2)):
        sign = -1 if target_color == 1 else 1
        for vertices in itertools.combinations(range(ORDER), clique_size):
            clause: list[int] = []
            for edge in itertools.combinations(vertices, 2):
                color = fixed_color(edge, split, left, right)
                if color == 0:
                    clause.append(sign * edge_variable(*edge))
                elif color != target_color:
                    break
            else:
                yield tuple(clause)


def write_cnf(
    path: Path,
    split: int,
    left: dict[tuple[int, int], int],
    right: dict[tuple[int, int], int],
) -> int:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    clauses = tuple(reduced_ramsey_clauses(split, left, right))
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {VARIABLES} {len(clauses)}\n")
        for clause in clauses:
            output.write(" ".join(map(str, clause)))
            output.write(" 0\n")
    return len(clauses)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover-dir", type=Path, required=True)
    parser.add_argument("--degree", type=int, choices=DEGREE_SOURCES, default=8)
    parser.add_argument("--start-pair", type=int, default=0)
    parser.add_argument("--pair-count", type=int)
    parser.add_argument(
        "--pair-index",
        type=int,
        action="append",
        dest="pair_indices",
        help="select one Cartesian pair; repeat for a sparse family",
    )
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/r45-gluing-branches-v1"),
    )
    arguments = parser.parse_args()
    if arguments.start_pair < 0:
        parser.error("--start-pair must be nonnegative")
    if arguments.pair_count is not None and arguments.pair_count <= 0:
        parser.error("--pair-count must be positive")
    if arguments.pair_indices is not None and (
        arguments.start_pair != 0 or arguments.pair_count is not None
    ):
        parser.error("--pair-index cannot be combined with an interval selection")

    manifest_path = arguments.output_dir / "manifest.json"
    if manifest_path.exists():
        parser.error(f"refusing to overwrite {manifest_path}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    left_name, left_size, right_name, right_size = DEGREE_SOURCES[arguments.degree]
    left_path = arguments.cover_dir / left_name
    right_path = arguments.cover_dir / right_name
    left_codes = read_cover(left_path, left_size)
    right_codes = read_cover(right_path, right_size)
    total_pairs = len(left_codes) * len(right_codes)
    if arguments.pair_indices is not None:
        pair_indices = sorted(arguments.pair_indices)
        if len(pair_indices) != len(set(pair_indices)):
            parser.error("--pair-index values must be distinct")
        if not pair_indices or pair_indices[0] < 0 or pair_indices[-1] >= total_pairs:
            parser.error(f"--pair-index values must lie in [0, {total_pairs})")
        schema = SPARSE_SCHEMA
        selection = {"pair_indices": pair_indices}
    else:
        stop_pair = total_pairs
        if arguments.pair_count is not None:
            stop_pair = min(total_pairs, arguments.start_pair + arguments.pair_count)
        if arguments.start_pair >= stop_pair:
            parser.error(
                f"empty pair interval [{arguments.start_pair}, {stop_pair}) "
                f"for {total_pairs} pairs"
            )
        pair_indices = list(range(arguments.start_pair, stop_pair))
        schema = CONTIGUOUS_SCHEMA
        selection = {"pair_interval": [arguments.start_pair, stop_pair]}

    records = []
    for pair_index in pair_indices:
        left_index, right_index = divmod(pair_index, len(right_codes))
        left_code = left_codes[left_index]
        right_code = right_codes[right_index]
        left = decode_generalized_graph(left_code, left_size)
        right = decode_generalized_graph(right_code, right_size)
        name = (
            f"r45-glue-d{arguments.degree:02d}-"
            f"i{left_index:05d}-j{right_index:05d}.cnf"
        )
        path = arguments.output_dir / name
        clause_count = write_cnf(path, left_size, left, right)
        record = {
            "pair_index": pair_index,
            "left_index": left_index,
            "right_index": right_index,
            "left_code": str(left_code),
            "right_code": str(right_code),
            "path": name,
            "variables": VARIABLES,
            "clauses": clause_count,
            "sha256": file_sha256(path),
        }
        records.append(record)
        print(
            f"generated pair {pair_index}/{total_pairs}: {path} "
            f"clauses={clause_count} sha256={record['sha256']}"
        )

    archive = None
    if arguments.archive is not None:
        archive = {
            "name": arguments.archive.name,
            "sha256": file_sha256(arguments.archive),
            "source_url": SOURCE_URL,
        }
    document = {
        "schema": schema,
        "claim": "branch formulas only; this manifest contains no UNSAT result",
        "order": ORDER,
        "ramsey_parameters": [4, 5],
        "fixed_star_degree": arguments.degree,
        "variables": VARIABLES,
        "substitution": "two generalized diagonal blocks; color 0 remains free",
        "graph_encoding": "leading-one row-major upper-triangle base three",
        "total_pairs": total_pairs,
        "archive": archive,
        "covers": [
            {
                "side": "R(3,5)",
                "file": left_name,
                "order": left_size,
                "rows": len(left_codes),
                "sha256": file_sha256(left_path),
            },
            {
                "side": "R(4,4)",
                "file": right_name,
                "order": right_size,
                "rows": len(right_codes),
                "sha256": file_sha256(right_path),
            },
        ],
        "files": records,
    }
    document.update(selection)
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
