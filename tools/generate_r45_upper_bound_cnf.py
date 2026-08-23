#!/usr/bin/env python3
"""Generate the direct order-25 CNF for the upper bound R(4,5) <= 25."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path

from ramsey55.sat import edge_variable


SCHEMA = "ramsey55.r45-upper-bound.v1"
ORDER = 25
VARIABLES = comb(ORDER, 2)
CLAUSES = comb(ORDER, 4) + comb(ORDER, 5)


def r45_upper_bound_clauses():
    """Forbid true K4s and false K5s in lexicographic vertex-set order."""

    for vertices in itertools.combinations(range(ORDER), 4):
        yield tuple(
            -edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertices in itertools.combinations(range(ORDER), 5):
        yield tuple(
            edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("build/r45-upper-bound/r45-n25.cnf")
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("build/r45-upper-bound/manifest.json"),
    )
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {VARIABLES} {CLAUSES}\n")
        count = 0
        for count, clause in enumerate(r45_upper_bound_clauses(), 1):
            output.write(" ".join(map(str, clause)))
            output.write(" 0\n")
    if count != CLAUSES:
        raise RuntimeError(f"generated {count} clauses, expected {CLAUSES}")
    record = {
        "schema": SCHEMA,
        "order": ORDER,
        "red_clique": 4,
        "blue_clique": 5,
        "variables": VARIABLES,
        "clauses": CLAUSES,
        "path": arguments.output.name,
        "sha256": sha256(arguments.output),
    }
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {arguments.output}: variables={VARIABLES} clauses={CLAUSES} "
        f"sha256={record['sha256']}"
    )


if __name__ == "__main__":
    main()
