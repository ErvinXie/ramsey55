#!/usr/bin/env python3
"""Bind the formal order-45 counter tails to existing mother DIMACS files."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterable, Sequence

if __package__:
    from tools.verify_order45_edge_strata import SCHEMA as FORMULA_SCHEMA, structure
else:
    from verify_order45_edge_strata import SCHEMA as FORMULA_SCHEMA, structure


SCHEMA = "ramsey55.order45-counter-tails.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def clause_bytes(clause: Sequence[int]) -> bytes:
    fields = [*(str(literal) for literal in clause), "0"]
    return (" ".join(fields) + "\n").encode("ascii")


def clause_stream_sha256(clauses: Iterable[Sequence[int]]) -> str:
    digest = hashlib.sha256()
    for clause in clauses:
        digest.update(clause_bytes(clause))
    return digest.hexdigest()


def integer_sequence_sha256(values: Sequence[int]) -> str:
    return hashlib.sha256(
        (" ".join(map(str, values)) + "\n").encode("ascii")
    ).hexdigest()


def edge_variable(left: int, right: int) -> int:
    if not 0 <= left < right:
        raise ValueError("edge endpoints are not increasing")
    return right * (right - 1) // 2 + left + 1


def input_identifiers(degree: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    h_vertices = range(1, degree + 1)
    j_vertices = range(degree + 1, 45)
    h = tuple(edge_variable(*pair) for pair in itertools.combinations(h_vertices, 2))
    j = tuple(edge_variable(*pair) for pair in itertools.combinations(j_vertices, 2))
    return h, j


def parse_clause(line: str, path: Path, clause_index: int) -> tuple[int, ...]:
    fields = line.split()
    if not fields or fields[-1] != "0":
        raise ValueError(f"invalid clause {clause_index + 1} in {path}")
    return tuple(map(int, fields[:-1]))


def audit_formula_tail(
    cnf: Path, formula_record: dict[str, object]
) -> dict[str, object]:
    degree = int(formula_record["degree"])
    maximum, _, h_clauses, j_clauses, bounds, sums, _ = structure(degree)
    tail_sources = (h_clauses, j_clauses, bounds, sums)
    tail_count = sum(len(source) for source in tail_sources)
    total_clauses = int(formula_record["clauses"])
    start = total_clauses - tail_count
    if start < 0 or maximum != int(formula_record["variables"]):
        raise ValueError(f"invalid formula metadata for d{degree}")
    if file_sha256(cnf) != formula_record["sha256"]:
        raise ValueError(f"formula hash mismatch for d{degree}")

    expected_tail = itertools.chain.from_iterable(tail_sources)
    digest = hashlib.sha256()
    with cnf.open(encoding="ascii") as stream:
        header = stream.readline().split()
        if header != ["p", "cnf", str(maximum), str(total_clauses)]:
            raise ValueError(f"formula header mismatch for d{degree}")
        for clause_index in range(total_clauses):
            line = stream.readline()
            if not line:
                raise ValueError(f"formula ends at clause {clause_index} for d{degree}")
            if clause_index < start:
                continue
            actual = parse_clause(line, cnf, clause_index)
            expected = tuple(next(expected_tail))
            if actual != expected:
                raise ValueError(
                    f"counter tail differs at clause {clause_index + 1} for d{degree}"
                )
            digest.update(clause_bytes(actual))
        if stream.readline():
            raise ValueError(f"extra formula data for d{degree}")
    try:
        next(expected_tail)
    except StopIteration:
        pass
    else:
        raise ValueError(f"counter tail reconstruction is longer for d{degree}")

    h_inputs, j_inputs = input_identifiers(degree)
    if degree == 20:
        dimensions = (190, 101, 276, 133, 36627, 50767, 68, 100, 116, 132, 226)
    elif degree == 21:
        dimensions = (210, 108, 253, 123, 36630, 53532, 77, 107, 101, 122, 222)
    elif degree == 22:
        dimensions = (231, 115, 231, 115, 36631, 56641, 88, 114, 88, 114, 220)
    else:
        raise ValueError(f"unexpected degree {degree}")
    (
        h_rows,
        h_width,
        j_rows,
        j_width,
        h_base,
        j_base,
        h_lower,
        h_upper,
        j_lower,
        j_upper,
        threshold,
    ) = dimensions
    if (len(h_inputs), len(j_inputs)) != (h_rows, j_rows):
        raise ValueError(f"input dimensions differ for d{degree}")
    expected_digest = clause_stream_sha256(
        itertools.chain.from_iterable(tail_sources)
    )
    if digest.hexdigest() != expected_digest:
        raise ValueError(f"counter tail digest differs for d{degree}")
    return {
        "degree": degree,
        "formula_path": str(formula_record["path"]),
        "formula_sha256": str(formula_record["sha256"]),
        "variables": maximum,
        "tail_start_clause_zero_based": start,
        "tail_clauses": tail_count,
        "tail_sha256": digest.hexdigest(),
        "h_rows": h_rows,
        "h_width": h_width,
        "h_base": h_base,
        "h_input_identifiers_sha256": integer_sequence_sha256(h_inputs),
        "j_rows": j_rows,
        "j_width": j_width,
        "j_base": j_base,
        "j_input_identifiers_sha256": integer_sequence_sha256(j_inputs),
        "h_range": [h_lower, h_upper],
        "j_range": [j_lower, j_upper],
        "sum_threshold": threshold,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--formula-manifest",
        type=Path,
        default=Path("build/order45-strata/manifest.json"),
    )
    parser.add_argument(
        "--cnf-dir", type=Path, default=Path("build/order45-strata")
    )
    parser.add_argument(
        "--tail-manifest",
        type=Path,
        default=Path("data/order45-counter-tail-manifest.json"),
    )
    parser.add_argument("--emit", action="store_true")
    arguments = parser.parse_args()

    raw_formula_manifest = arguments.formula_manifest.read_bytes()
    formula_manifest = json.loads(raw_formula_manifest)
    if formula_manifest.get("schema") != FORMULA_SCHEMA:
        raise ValueError("unexpected formula manifest schema")
    calculated = {
        "schema": SCHEMA,
        "formula_manifest_sha256": hashlib.sha256(raw_formula_manifest).hexdigest(),
        "clause_encoding": "DIMACS literals and terminal 0 joined by spaces, then LF",
        "input_identifier_encoding": "decimal identifiers joined by spaces, then LF",
        "records": [
            audit_formula_tail(arguments.cnf_dir / record["path"], record)
            for record in formula_manifest["files"]
        ],
    }
    if arguments.emit:
        print(json.dumps(calculated, indent=2, sort_keys=True))
        return
    expected = json.loads(arguments.tail_manifest.read_text(encoding="utf-8"))
    if calculated != expected:
        raise ValueError("counter-tail manifest differs from audited formulas")
    for record in calculated["records"]:
        print(
            f"verified d{record['degree']} counter tail: "
            f"{record['tail_clauses']} clauses, sha256 {record['tail_sha256']}"
        )


if __name__ == "__main__":
    main()
