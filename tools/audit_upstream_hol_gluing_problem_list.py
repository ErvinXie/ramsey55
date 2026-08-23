#!/usr/bin/env python3
"""Independently audit a HOL4 gluing problem list as an exact cover product."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "ramsey55.upstream-hol-gluing-problem-list.v1"
DEGREE_SOURCES = {
    8: ("gen358", "gen4416"),
    10: ("gen3510", "gen4414"),
    12: ("gen3512", "gen4412"),
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def read_cover_codes(path: Path) -> list[int]:
    codes = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields:
                raise ValueError(f"{path}:{line_number}: empty cover row")
            try:
                code = int(fields[0])
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid cover code"
                ) from error
            if code <= 0:
                raise ValueError(f"{path}:{line_number}: nonpositive cover code")
            codes.append(code)
    if not codes or len(codes) != len(set(codes)):
        raise ValueError(f"cover codes must be nonempty and unique: {path}")
    return codes


def read_problem_list(path: Path) -> list[tuple[int, int]]:
    pairs = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if len(fields) != 2:
                raise ValueError(
                    f"{path}:{line_number}: expected exactly two integer fields"
                )
            try:
                pair = (int(fields[0]), int(fields[1]))
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid problem pair"
                ) from error
            pairs.append(pair)
    if not pairs:
        raise ValueError(f"empty problem list: {path}")
    return pairs


def audit(problem_list: Path, cover_directory: Path, degree: int) -> dict[str, object]:
    try:
        left_name, right_name = DEGREE_SOURCES[degree]
    except KeyError as error:
        raise ValueError(f"unsupported fixed-star degree: {degree}") from error
    problem_list = problem_list.resolve()
    cover_directory = cover_directory.resolve()
    left_path = cover_directory / left_name
    right_path = cover_directory / right_name
    left = read_cover_codes(left_path)
    right = read_cover_codes(right_path)
    observed = read_problem_list(problem_list)
    expected = [(left_code, right_code) for left_code in left for right_code in right]
    if observed != expected:
        mismatch = next(
            (
                index
                for index, (actual, wanted) in enumerate(
                    zip(observed, expected, strict=False)
                )
                if actual != wanted
            ),
            min(len(observed), len(expected)),
        )
        raise ValueError(
            "problem list is not the exact ordered Cartesian product: "
            f"first mismatch at {mismatch}, observed={len(observed)}, "
            f"expected={len(expected)}"
        )
    return {
        "schema": SCHEMA,
        "claim": (
            "exact ordered Cartesian product of the listed generalized-graph "
            "cover rows; global cover exhaustiveness is a separate theorem"
        ),
        "verified": True,
        "fixed_star_degree": degree,
        "left_cover": artifact(left_path),
        "right_cover": artifact(right_path),
        "problem_list": artifact(problem_list),
        "summary": {
            "left_rows": len(left),
            "right_rows": len(right),
            "pairs": len(observed),
            "unique_pairs": len(set(observed)),
            "exact_ordered_cartesian_product": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("problem_list", type=Path)
    parser.add_argument("--cover-directory", type=Path, required=True)
    parser.add_argument("--degree", type=int, choices=DEGREE_SOURCES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    try:
        document = audit(
            arguments.problem_list, arguments.cover_directory, arguments.degree
        )
    except ValueError as error:
        parser.error(str(error))
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = document["summary"]
    print(
        f"audited {summary['left_rows']} x {summary['right_rows']} = "
        f"{summary['pairs']} exact ordered gluing pairs"
    )


if __name__ == "__main__":
    main()
