#!/usr/bin/env python3
"""Remove exactly one final empty addition from a framed binary DRAT proof.

This is a format conversion only.  The output fragment must still be composed
with its assumptions and checked before it receives any proof credit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import BinaryIO


SCHEMA = "ramsey55.binary-drat-final-empty-strip.v1"
BLOCK_SIZE = 1 << 23


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def scan_binary_drat(path: Path) -> dict[str, int]:
    counts = {
        "additions": 0,
        "deletions": 0,
        "empty_additions": 0,
        "empty_deletions": 0,
    }
    pending = b""
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK_SIZE), b""):
            clauses = (pending + block).split(b"\0")
            pending = clauses.pop()
            for clause in clauses:
                if not clause or clause[0] not in (ord("a"), ord("d")):
                    raise ValueError(f"invalid binary DRAT framing in {path}")
                if clause[0] == ord("a"):
                    counts["additions"] += 1
                    counts["empty_additions"] += len(clause) == 1
                else:
                    counts["deletions"] += 1
                    counts["empty_deletions"] += len(clause) == 1
    if pending:
        raise ValueError(f"unterminated binary DRAT clause in {path}")
    return counts


def copy_prefix(source: BinaryIO, target: BinaryIO, size: int) -> str:
    remaining = size
    digest = hashlib.sha256()
    while remaining:
        block = source.read(min(BLOCK_SIZE, remaining))
        if not block:
            raise ValueError("source proof ended while copying its exact prefix")
        target.write(block)
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def atomic_json(path: Path, document: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("standalone_proof", type=Path)
    parser.add_argument("output_fragment", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    if not arguments.standalone_proof.is_file():
        parser.error(f"input does not exist: {arguments.standalone_proof}")
    if arguments.standalone_proof.stat().st_size < 2:
        parser.error("input is too short to contain a final empty addition")
    outputs = (arguments.output_fragment, arguments.manifest)
    temporaries = tuple(path.with_suffix(path.suffix + ".tmp") for path in outputs)
    if any(path.exists() for path in outputs + temporaries):
        parser.error("refusing to overwrite an output or temporary")

    source_counts = scan_binary_drat(arguments.standalone_proof)
    if source_counts["empty_additions"] != 1:
        raise ValueError("source proof must contain exactly one empty addition")
    with arguments.standalone_proof.open("rb") as source:
        source.seek(-2, 2)
        if source.read(2) != b"a\0":
            raise ValueError("the unique empty addition is not the final record")

    source_record = file_record(arguments.standalone_proof)
    fragment_size = int(source_record["size"]) - 2
    fragment_temporary = temporaries[0]
    try:
        with (
            arguments.standalone_proof.open("rb") as source,
            fragment_temporary.open("wb") as target,
        ):
            fragment_sha256 = copy_prefix(source, target, fragment_size)
        if fragment_temporary.stat().st_size != fragment_size:
            raise ValueError("fragment size changed while publishing")
        fragment_temporary.replace(arguments.output_fragment)
    finally:
        fragment_temporary.unlink(missing_ok=True)

    fragment_counts = dict(source_counts)
    fragment_counts["additions"] -= 1
    fragment_counts["empty_additions"] = 0
    document: dict[str, object] = {
        "schema": SCHEMA,
        "tool": file_record(Path(__file__).resolve()),
        "standalone_proof": {
            **source_record,
            "binary_drat": source_counts,
            "ends_with_empty_addition": True,
        },
        "output_fragment": {
            "path": str(arguments.output_fragment),
            "sha256": fragment_sha256,
            "size": fragment_size,
            "binary_drat": fragment_counts,
            "contains_empty_addition": False,
        },
        "derivation": "exact standalone byte prefix excluding final a\\0",
        "proof_credit": False,
    }
    atomic_json(arguments.manifest, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
