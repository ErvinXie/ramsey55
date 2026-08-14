#!/usr/bin/env python3
"""Concatenate binary DRAT fragments and optionally append an empty clause."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("fragments", type=Path, nargs="+")
    parser.add_argument("--append-empty", action="store_true")
    arguments = parser.parse_args()
    resolved_output = arguments.output.resolve()
    if any(fragment.resolve() == resolved_output for fragment in arguments.fragments):
        parser.error("output must differ from every fragment")
    for fragment in arguments.fragments:
        if not fragment.is_file():
            raise FileNotFoundError(fragment)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("wb") as output:
        for fragment in arguments.fragments:
            with fragment.open("rb") as source:
                shutil.copyfileobj(source, output, length=1 << 20)
        if arguments.append_empty:
            output.write(b"a\0")
    temporary.replace(arguments.output)
    print(
        f"wrote {arguments.output}: {arguments.output.stat().st_size} bytes, "
        f"sha256 {sha256(arguments.output)}"
    )


if __name__ == "__main__":
    main()
