#!/usr/bin/env python3
"""Compose binary DRAT fragments while protecting original CNF clauses.

Independent solver fragments may delete an original clause that a later
fragment expects to find.  Omitting those deletion instructions is sound and
retains all other deletion instructions, keeping substantially more of the
checker's clause-database cleanup than addition-only normalization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Iterable


SCHEMA = "ramsey55.binary-drat-protected-cnf-composition.v1"
PERSON = b"r55-cnf-clause"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def clause_fingerprint(literals: Iterable[int]) -> bytes:
    canonical = sorted(literals)
    packed = struct.pack(f"<{len(canonical) + 1}i", len(canonical), *canonical)
    return hashlib.blake2b(packed, digest_size=16, person=PERSON).digest()


def read_cnf_clause_fingerprints(path: Path) -> tuple[set[bytes], int, int]:
    variables: int | None = None
    declared_clauses: int | None = None
    clause: list[int] = []
    fingerprints: set[bytes] = set()
    clauses = 0
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("c"):
                continue
            fields = stripped.split()
            if fields[0] == "p":
                if variables is not None or clause or len(fields) != 4:
                    raise ValueError(f"invalid CNF header at line {line_number}")
                if fields[1] != "cnf":
                    raise ValueError(f"unsupported DIMACS kind at line {line_number}")
                variables = int(fields[2])
                declared_clauses = int(fields[3])
                if not 0 <= variables <= 2_147_483_647:
                    raise ValueError("DIMACS variable count is outside int32 range")
                if declared_clauses < 0:
                    raise ValueError("negative DIMACS dimensions")
                continue
            if variables is None:
                raise ValueError(f"CNF clause precedes header at line {line_number}")
            for field in fields:
                literal = int(field)
                if literal:
                    if abs(literal) > variables:
                        raise ValueError(
                            f"CNF literal outside header at line {line_number}"
                        )
                    clause.append(literal)
                    continue
                fingerprints.add(clause_fingerprint(clause))
                clauses += 1
                clause = []
    if variables is None or declared_clauses is None:
        raise ValueError("CNF header is missing")
    if clause:
        raise ValueError("unterminated final CNF clause")
    if clauses != declared_clauses:
        raise ValueError(
            f"CNF clause count {clauses} does not match header {declared_clauses}"
        )
    return fingerprints, variables, clauses


def decode_binary_clause(clause: bytes, variables: int) -> tuple[bool, list[int]]:
    if not clause or clause[0] not in (ord("a"), ord("d")):
        raise ValueError("invalid binary DRAT clause marker")
    literals: list[int] = []
    value = 0
    shift = 0
    for byte in clause[1:]:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            if shift > 35:
                raise ValueError("oversized binary DRAT literal")
            continue
        variable = value >> 1
        if variable == 0 or variable > variables:
            raise ValueError("binary DRAT literal outside CNF variable range")
        literals.append(-variable if value & 1 else variable)
        value = 0
        shift = 0
    if shift:
        raise ValueError("unterminated binary DRAT literal")
    return clause[0] == ord("a"), literals


def compose(
    target: Any,
    fragments: list[Path],
    protected: set[bytes],
    variables: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    fragment_records: list[dict[str, Any]] = []
    totals = {
        "additions": 0,
        "retained_deletions": 0,
        "dropped_protected_deletions": 0,
        "empty_additions": 0,
        "empty_deletions": 0,
    }
    for fragment in fragments:
        counts = {key: 0 for key in totals}
        source_digest = hashlib.sha256()
        pending = b""
        with fragment.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 23), b""):
                source_digest.update(block)
                clauses = (pending + block).split(b"\0")
                pending = clauses.pop()
                for clause in clauses:
                    addition, literals = decode_binary_clause(clause, variables)
                    if addition:
                        if not literals:
                            raise ValueError(
                                f"fragment contains an empty addition: {fragment}"
                            )
                        counts["additions"] += 1
                        target.write(clause)
                        target.write(b"\0")
                    elif clause_fingerprint(literals) in protected:
                        counts["dropped_protected_deletions"] += 1
                    else:
                        counts["retained_deletions"] += 1
                        counts["empty_deletions"] += not literals
                        target.write(clause)
                        target.write(b"\0")
        if pending:
            raise ValueError(f"unterminated binary DRAT clause in {fragment}")
        for key, value in counts.items():
            totals[key] += value
        fragment_records.append(
            {
                "path": str(fragment),
                "sha256": source_digest.hexdigest(),
                "size": fragment.stat().st_size,
                "composition_counts": counts,
            }
        )
    return fragment_records, totals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("fragments", type=Path, nargs="+")
    parser.add_argument("--append-empty", action="store_true")
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    for path in [arguments.cnf, *arguments.fragments]:
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    if arguments.output.exists() or arguments.manifest.exists():
        parser.error("refusing to overwrite an output")
    output_temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    manifest_temporary = arguments.manifest.with_suffix(
        arguments.manifest.suffix + ".tmp"
    )
    if output_temporary.exists() or manifest_temporary.exists():
        parser.error("refusing to overwrite a temporary output")

    protected, variables, clauses = read_cnf_clause_fingerprints(arguments.cnf)
    try:
        with output_temporary.open("wb") as target:
            fragment_records, totals = compose(
                target, arguments.fragments, protected, variables
            )
            if arguments.append_empty:
                target.write(b"a\0")
                totals["additions"] += 1
                totals["empty_additions"] += 1
        output_temporary.replace(arguments.output)
        document = {
            "schema": SCHEMA,
            "cnf": file_record(arguments.cnf),
            "cnf_variables": variables,
            "cnf_clauses": clauses,
            "unique_protected_clause_fingerprints": len(protected),
            "clause_fingerprint": "blake2b-128(sorted signed int32 literals)",
            "fragments": fragment_records,
            "append_empty": arguments.append_empty,
            "composition_counts": totals,
            "output": file_record(arguments.output),
        }
        manifest_temporary.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_temporary.replace(arguments.manifest)
    finally:
        for path in (output_temporary, manifest_temporary):
            if path.exists():
                path.unlink()
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
