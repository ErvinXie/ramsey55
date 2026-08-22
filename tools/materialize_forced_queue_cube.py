#!/usr/bin/env python3
"""Materialize the predicted surviving literals from forced-queue manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.export_screened_forced_queue import SCHEMA as QUEUE_SCHEMA
    from tools.prove_materialized_cubes import file_sha256
    from tools.select_cube_rows import read_rows
else:
    from export_screened_forced_queue import SCHEMA as QUEUE_SCHEMA
    from prove_materialized_cubes import file_sha256
    from select_cube_rows import read_rows


SCHEMA = "ramsey55.forced-queue-cube.v1"


def extend_cube(parent: list[int], documents: list[dict[str, Any]]) -> list[int]:
    if not parent or not documents:
        raise ValueError("parent and queue documents must be nonempty")
    assigned: dict[int, int] = {}
    for literal in parent:
        variable = abs(literal)
        if not variable or variable in assigned:
            raise ValueError("parent cube repeats a variable")
        assigned[variable] = literal

    output = list(parent)
    for source, document in enumerate(documents):
        if document.get("schema") != QUEUE_SCHEMA:
            raise ValueError(f"queue source {source} has the wrong schema")
        ranked = document.get("parents_ranked")
        if not isinstance(ranked, list) or len(ranked) != 1:
            raise ValueError(f"queue source {source} must contain exactly one parent")
        group = ranked[0]
        queue = group.get("queue")
        candidates = group.get("candidates")
        if group.get("parent_index") != 0:
            raise ValueError(f"queue source {source} has the wrong parent index")
        if not isinstance(queue, list) or not isinstance(candidates, list):
            raise ValueError(f"queue source {source} has invalid candidate arrays")
        if len(queue) != len(candidates) or group.get("candidate_count") != len(queue):
            raise ValueError(f"queue source {source} candidate count mismatch")
        if document.get("candidate_count") != len(queue):
            raise ValueError(f"queue source {source} total count mismatch")
        for variable, candidate in zip(queue, candidates, strict=True):
            if not isinstance(variable, int) or variable <= 0:
                raise ValueError(f"queue source {source} has an invalid variable")
            surviving = candidate.get("surviving_literal")
            contradictory = candidate.get("contradictory_literal")
            if (
                candidate.get("parent_index") != 0
                or candidate.get("variable") != variable
                or not isinstance(surviving, int)
                or abs(surviving) != variable
                or contradictory != -surviving
            ):
                raise ValueError(f"queue source {source} has inconsistent literals")
            if variable in assigned:
                raise ValueError(f"variable {variable} is assigned more than once")
            assigned[variable] = surviving
            output.append(surviving)
    return output


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parent", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("queues", type=Path, nargs="+")
    arguments = parser.parse_args()
    if arguments.output.exists() or arguments.manifest.exists():
        parser.error("refusing to overwrite output or manifest")

    parents = read_rows(arguments.parent)
    if len(parents) != 1:
        parser.error("parent ICNF must contain exactly one row")
    parent_sha256 = file_sha256(arguments.parent)
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in arguments.queues]
    for source, document in enumerate(documents):
        binding = document.get("parents")
        if not isinstance(binding, dict):
            parser.error(f"queue source {source} has no parent binding")
        if binding.get("sha256") != parent_sha256 or binding.get("count") != 1:
            parser.error(f"queue source {source} does not bind the exact parent")

    cube = extend_cube(parents[0], documents)
    output_bytes = ("a " + " ".join(map(str, cube)) + " 0\n").encode("ascii")
    atomic_write(arguments.output, output_bytes)
    manifest = {
        "schema": SCHEMA,
        "parent": {
            "path": str(arguments.parent),
            "sha256": parent_sha256,
            "literal_count": len(parents[0]),
        },
        "queues": [
            {
                "path": str(path),
                "sha256": file_sha256(path),
                "mode": document["mode"],
                "candidate_count": document["candidate_count"],
            }
            for path, document in zip(arguments.queues, documents, strict=True)
        ],
        "output": {
            "path": str(arguments.output),
            "sha256": hashlib.sha256(output_bytes).hexdigest(),
            "literal_count": len(cube),
            "added_literal_count": len(cube) - len(parents[0]),
        },
    }
    atomic_write(
        arguments.manifest,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
