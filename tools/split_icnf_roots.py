#!/usr/bin/env python3
"""Split an ICNF frontier into hash-bound one-root ICNF files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from tools.replay_cadical_dfs_prefix import read_roots
else:
    from replay_cadical_dfs_prefix import read_roots


SCHEMA = "ramsey55.icnf-root-split.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, document: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frontier", type=Path)
    parser.add_argument("output_prefix", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    if not arguments.frontier.is_file():
        parser.error(f"frontier does not exist: {arguments.frontier}")
    if not arguments.output_prefix.name:
        parser.error("output prefix must have a basename")

    roots = read_roots(arguments.frontier)
    outputs = tuple(
        arguments.output_prefix.with_name(
            f"{arguments.output_prefix.name}-root{index:03d}.icnf"
        )
        for index in range(len(roots))
    )
    temporaries = tuple(path.with_suffix(path.suffix + ".tmp") for path in outputs)
    manifest_temporary = arguments.manifest.with_suffix(
        arguments.manifest.suffix + ".tmp"
    )
    if arguments.manifest.exists() or manifest_temporary.exists():
        parser.error("refusing to overwrite manifest output")
    if any(path.exists() for path in outputs + temporaries):
        parser.error("refusing to overwrite root output")
    if any(path.parent != arguments.output_prefix.parent for path in outputs):
        raise ValueError("root outputs escaped the output-prefix directory")

    records: list[dict[str, object]] = []
    try:
        for index, (cube, temporary, output) in enumerate(
            zip(roots, temporaries, outputs, strict=True)
        ):
            payload = ("a " + " ".join(map(str, cube)) + " 0\n").encode("ascii")
            temporary.write_bytes(payload)
            records.append(
                {
                    "index": index,
                    "path": str(output),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                }
            )
        for temporary, output in zip(temporaries, outputs, strict=True):
            temporary.replace(output)

        document: dict[str, object] = {
            "schema": SCHEMA,
            "source_frontier": {
                "path": str(arguments.frontier),
                "sha256": file_sha256(arguments.frontier),
                "count": len(roots),
            },
            "output_prefix": str(arguments.output_prefix),
            "outputs": records,
        }
        atomic_json(arguments.manifest, document)
    finally:
        for temporary in temporaries + (manifest_temporary,):
            if temporary.exists():
                temporary.unlink()

    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
