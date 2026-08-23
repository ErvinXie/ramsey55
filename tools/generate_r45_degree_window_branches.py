#!/usr/bin/env python3
"""Generate the three R(4,5,25) branches with redundant degree windows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ramsey55.cardinality import cardinality_range_encoding
from ramsey55.sat import edge_variable

if __package__:
    from tools import generate_r45_upper_bound_cnf as upper_bound
else:
    import generate_r45_upper_bound_cnf as upper_bound


BASE_CLAUSES = upper_bound.CLAUSES
ORDER = upper_bound.ORDER
PRIMARY_VARIABLES = upper_bound.VARIABLES
r45_upper_bound_clauses = upper_bound.r45_upper_bound_clauses


SCHEMA = "ramsey55.r45-degree-window-branches.v1"
DEGREES = (8, 10, 12)
LOWER_DEGREE = 7
UPPER_DEGREE = 13
RAW_HASHES = {
    8: "8c0935f6f795dfb059e6f9c5ba3bd1ae48856e90d3b652b7a81886629b6744db",
    10: "974750e1771b1d81687d075faa112f545a7fab34dd4148358ed40755def51339",
    12: "f9864879bd1e57f1f0448d89373be24b44cb6228dc299a6ae75c78febc798e7d",
}


def fixed_star_clauses(degree: int):
    if not 0 <= degree < ORDER:
        raise ValueError("fixed-star degree outside graph")
    for vertex in range(1, ORDER):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def degree_window_clauses(
    lower: int = LOWER_DEGREE,
    upper: int = UPPER_DEGREE,
) -> tuple[int, tuple[tuple[int, ...], ...]]:
    """Encode the degree window for every vertex except the fixed vertex zero."""
    maximum_variable = PRIMARY_VARIABLES
    clauses: list[tuple[int, ...]] = []
    for vertex in range(1, ORDER):
        incident = tuple(
            edge_variable(vertex, other)
            for other in range(ORDER)
            if other != vertex
        )
        maximum_variable, encoded = cardinality_range_encoding(
            incident, lower, upper, maximum_variable
        )
        clauses.extend(encoded)
    return maximum_variable, tuple(clauses)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_branch(
    path: Path,
    degree: int,
    variables: int,
    bounded: tuple[tuple[int, ...], ...],
) -> int:
    clause_count = BASE_CLAUSES + ORDER - 1 + len(bounded)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for source in (
            r45_upper_bound_clauses(),
            fixed_star_clauses(degree),
            bounded,
        ):
            for clause in source:
                output.write(" ".join(map(str, clause)))
                output.write(" 0\n")
    return clause_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/r45-fixed-star-degree-window-v1"),
    )
    parser.add_argument("--degree", type=int, action="append", choices=DEGREES)
    arguments = parser.parse_args()
    degrees = tuple(arguments.degree or DEGREES)
    if len(set(degrees)) != len(degrees):
        parser.error("duplicate degree")
    manifest_path = arguments.output_dir / "manifest.json"
    if manifest_path.exists():
        parser.error(f"refusing to overwrite {manifest_path}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    variables, bounded = degree_window_clauses()
    records = []
    for degree in degrees:
        path = arguments.output_dir / f"r45-n25-fixed-d{degree:02d}-deg07-13.cnf"
        clauses = write_branch(path, degree, variables, bounded)
        record = {
            "degree": degree,
            "path": path.name,
            "variables": variables,
            "clauses": clauses,
            "sha256": file_sha256(path),
            "raw_sha256": RAW_HASHES[degree],
        }
        records.append(record)
        print(
            f"generated {path}: variables={variables} clauses={clauses} "
            f"sha256={record['sha256']}"
        )

    document = {
        "schema": SCHEMA,
        "order": ORDER,
        "primary_variables": PRIMARY_VARIABLES,
        "fixed_star_degrees": list(degrees),
        "degree_window": [LOWER_DEGREE, UPPER_DEGREE],
        "bounded_vertices": [1, ORDER - 1],
        "encoding": "bidirectional at-least sequential counter",
        "coverage_dependency": (
            "R(3,5)<=14 and R(4,4)<=18 imply every degree is in [7,13]"
        ),
        "degree_window_clauses": len(bounded),
        "files": records,
    }
    manifest_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
