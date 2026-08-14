#!/usr/bin/env python3
"""Certify that a DIMACS CNF is obtained by appending clauses and variables."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Formula:
    variables: int
    clauses: tuple[tuple[int, ...], ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_dimacs(path: Path) -> Formula:
    variables: int | None = None
    declared_clauses: int | None = None
    clauses: list[tuple[int, ...]] = []
    pending: list[int] = []
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("c"):
            continue
        if stripped.startswith("p"):
            if variables is not None or pending or clauses:
                raise ValueError(f"misplaced or duplicate header at line {line_number}")
            fields = stripped.split()
            if len(fields) != 4 or fields[:2] != ["p", "cnf"]:
                raise ValueError(f"invalid header at line {line_number}")
            variables, declared_clauses = map(int, fields[2:])
            if variables < 0 or declared_clauses < 0:
                raise ValueError("negative DIMACS size")
            continue
        if variables is None:
            raise ValueError(f"clause before header at line {line_number}")
        for field in stripped.split():
            literal = int(field)
            if literal == 0:
                clauses.append(tuple(pending))
                pending.clear()
            else:
                if abs(literal) > variables:
                    raise ValueError(f"literal outside variable range at line {line_number}")
                pending.append(literal)
    if variables is None or declared_clauses is None:
        raise ValueError("missing DIMACS header")
    if pending:
        raise ValueError("unterminated final clause")
    if len(clauses) != declared_clauses:
        raise ValueError(
            f"declared {declared_clauses} clauses but parsed {len(clauses)}"
        )
    return Formula(variables, tuple(clauses))


def strengthening_manifest(base_path: Path, stronger_path: Path) -> dict[str, object]:
    base = read_dimacs(base_path)
    stronger = read_dimacs(stronger_path)
    if stronger.variables < base.variables:
        raise ValueError("stronger formula has fewer variables")
    if len(stronger.clauses) < len(base.clauses):
        raise ValueError("stronger formula has fewer clauses")
    if stronger.clauses[: len(base.clauses)] != base.clauses:
        raise ValueError("base clauses are not an exact prefix of the stronger formula")
    return {
        "added_clauses": len(stronger.clauses) - len(base.clauses),
        "added_variables": stronger.variables - base.variables,
        "base": str(base_path),
        "base_clauses": len(base.clauses),
        "base_sha256": sha256(base_path),
        "base_variables": base.variables,
        "relation": "exact-clause-prefix",
        "stronger": str(stronger_path),
        "stronger_clauses": len(stronger.clauses),
        "stronger_sha256": sha256(stronger_path),
        "stronger_variables": stronger.variables,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("stronger", type=Path)
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    manifest = strengthening_manifest(arguments.base, arguments.stronger)
    temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(arguments.manifest)
    print(
        f"verified exact clause prefix; added "
        f"{manifest['added_variables']} variables and {manifest['added_clauses']} clauses"
    )


if __name__ == "__main__":
    main()
