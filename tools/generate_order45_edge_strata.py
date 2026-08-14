#!/usr/bin/env python3
"""Generate reusable order-45 mothers and complete exact local-edge cubes."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from ramsey55.cardinality import at_least_counter_encoding
from ramsey55.order45 import ORDER45_EXCESS_WITNESS_DEGREES, order45_excess_minimum_edge_sum
from ramsey55.sat import edge_variable, fixed_star_clauses, ramsey55_clauses
from generate_order45_lex_benchmarks import lex_clauses
from generate_order45_strengthened_benchmarks import degree_bound_clauses


SCHEMA = "ramsey55.order45-edge-strata.v1"
EDGE_RANGES = {20: (68, 100), 21: (77, 107), 22: (88, 114),
               23: (101, 122), 24: (116, 132)}


def internal_literals(degree):
    h = tuple(edge_variable(u, v) for u, v in itertools.combinations(range(1, degree + 1), 2))
    j = tuple(-edge_variable(u, v) for u, v in itertools.combinations(range(degree + 1, 45), 2))
    return h, j


def sum_threshold_clauses(h_outputs, j_outputs, threshold):
    clauses = []
    for split in range(threshold):
        requirements = (split + 1, threshold - split)
        clause = []
        impossible = 0
        for required, outputs in zip(requirements, (h_outputs, j_outputs)):
            if required <= 0:
                break
            if required <= len(outputs):
                clause.append(outputs[required - 1])
            else:
                impossible += 1
        else:
            if impossible == 2:
                clauses.append(())
            elif impossible == 1 and clause:
                clauses.append((clause[0],))
            elif impossible == 0:
                clauses.append(tuple(clause))
    return tuple(clauses)


def build(path, degree):
    variables, bounded = degree_bound_clauses(45, 20, 24, 990)
    variables, lex = lex_clauses(degree, variables)
    h_inputs, j_inputs = internal_literals(degree)
    h_min, h_max = EDGE_RANGES[degree]
    j_min, j_max = EDGE_RANGES[44 - degree]
    variables, h_counter, h_out = at_least_counter_encoding(h_inputs, h_max + 1, variables)
    variables, j_counter, j_out = at_least_counter_encoding(j_inputs, j_max + 1, variables)
    bounds = ((h_out[h_min - 1],), (-h_out[h_max],),
              (j_out[j_min - 1],), (-j_out[j_max],))
    threshold = order45_excess_minimum_edge_sum(degree)
    sum_clauses = sum_threshold_clauses(h_out, j_out, threshold)
    sources = (ramsey55_clauses(45), fixed_star_clauses(45, degree), bounded,
               lex, h_counter, j_counter, bounds, sum_clauses)
    count = 2 * 1_221_759 + 44 + sum(len(tuple(s)) if not isinstance(s, tuple) else len(s) for s in sources[2:])
    # The first two generators have known counts and are streamed only once.
    with path.open("w", encoding="ascii", newline="\n") as out:
        out.write(f"p cnf {variables} {count}\n")
        for source in sources:
            for clause in source:
                out.write(" ".join(map(str, clause)) + " 0\n")
    cubes = []
    for h in range(h_min, h_max + 1):
        for j in range(j_min, j_max + 1):
            if h + j < threshold:
                continue
            cube = [h_out[h - 1], -h_out[h], j_out[j - 1], -j_out[j]]
            cubes.append({"edges_h": h, "edges_j": j, "literals": cube})
    return variables, count, cubes


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/order45-strata"))
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for degree in ORDER45_EXCESS_WITNESS_DEGREES:
        path = args.output_dir / f"r55-n45-strata-d{degree}.cnf"
        variables, clauses, cubes = build(path, degree)
        records.append({"degree": degree, "path": path.name, "variables": variables,
                        "clauses": clauses, "sha256": sha256(path), "cubes": cubes})
        print(degree, variables, clauses, len(cubes))
    (args.output_dir / "manifest.json").write_text(json.dumps({"schema": SCHEMA,
        "order": 45, "files": records}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__": main()
