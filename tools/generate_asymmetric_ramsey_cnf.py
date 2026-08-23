#!/usr/bin/env python3
"""Generate the direct CNF for an asymmetric two-colour Ramsey upper bound."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from math import comb
from pathlib import Path

from ramsey55.sat import edge_variable


SCHEMA = "ramsey55.asymmetric-ramsey-upper-bound.v1"


def asymmetric_ramsey_clauses(order: int, red: int, blue: int):
    """Forbid true red-cliques and false blue-cliques in combination order."""

    for vertices in itertools.combinations(range(order), red):
        yield tuple(
            -edge_variable(left, right)
            for left, right in itertools.combinations(vertices, 2)
        )
    for vertices in itertools.combinations(range(order), blue):
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
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--red", type=int, required=True)
    parser.add_argument("--blue", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()
    if not 2 <= arguments.red <= arguments.order:
        parser.error("--red must lie between 2 and --order")
    if not 2 <= arguments.blue <= arguments.order:
        parser.error("--blue must lie between 2 and --order")
    variables = comb(arguments.order, 2)
    clauses = comb(arguments.order, arguments.red) + comb(
        arguments.order, arguments.blue
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clauses}\n")
        count = 0
        for count, clause in enumerate(
            asymmetric_ramsey_clauses(
                arguments.order, arguments.red, arguments.blue
            ),
            1,
        ):
            output.write(" ".join(map(str, clause)))
            output.write(" 0\n")
    if count != clauses:
        raise RuntimeError(f"generated {count} clauses, expected {clauses}")
    document = {
        "schema": SCHEMA,
        "order": arguments.order,
        "red_clique": arguments.red,
        "blue_clique": arguments.blue,
        "variables": variables,
        "clauses": clauses,
        "path": arguments.output.name,
        "sha256": sha256(arguments.output),
    }
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {arguments.output}: variables={variables} clauses={clauses} "
        f"sha256={document['sha256']}"
    )


if __name__ == "__main__":
    main()
