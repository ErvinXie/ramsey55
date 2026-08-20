#!/usr/bin/env python3
"""Select indexed ICNF assumption rows with a hash-bound manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ramsey55.selected-cube-rows.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[list[int]]:
    rows: list[list[int]] = []
    for line_number, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        fields = raw.split()
        if not fields:
            continue
        if fields[0] != "a" or fields[-1] != "0":
            raise ValueError(f"invalid ICNF row {line_number}: {path}")
        literals = [int(value) for value in fields[1:-1]]
        if not literals or any(value == 0 for value in literals):
            raise ValueError(f"invalid ICNF literals on row {line_number}: {path}")
        rows.append(literals)
    if not rows:
        raise ValueError(f"ICNF contains no assumption rows: {path}")
    return rows


def atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("indices", type=int, nargs="+")
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.input.is_file():
        parser.error("input ICNF does not exist")
    if arguments.output.exists() or arguments.manifest.exists():
        parser.error("refusing to overwrite output or manifest")
    if arguments.indices != sorted(set(arguments.indices)):
        parser.error("indices must be unique and sorted")
    rows = read_rows(arguments.input)
    if any(index < 0 or index >= len(rows) for index in arguments.indices):
        parser.error("cube index is out of range")
    selected = [rows[index] for index in arguments.indices]
    output_bytes = "".join(
        "a " + " ".join(map(str, row)) + " 0\n" for row in selected
    ).encode("ascii")
    atomic_write(arguments.output, output_bytes)
    manifest = {
        "schema": SCHEMA,
        "input": str(arguments.input),
        "input_sha256": file_sha256(arguments.input),
        "input_count": len(rows),
        "indices": arguments.indices,
        "output": str(arguments.output),
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "output_count": len(selected),
    }
    atomic_write(
        arguments.manifest,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
