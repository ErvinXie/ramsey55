#!/usr/bin/env python3
"""Verify that ordered ICNF parts are an exact partition of a cube family."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from tools.export_proof_frontier import read_cubes
else:
    from export_proof_frontier import read_cubes


SCHEMA = "ramsey55.icnf-partition.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_partition(whole_path: Path, part_paths: list[Path]) -> dict[str, object]:
    whole = read_cubes(whole_path)
    joined: list[tuple[int, ...]] = []
    records: list[dict[str, object]] = []
    for part_path in part_paths:
        part = read_cubes(part_path)
        start = len(joined)
        joined.extend(part)
        records.append(
            {
                "path": str(part_path),
                "sha256": sha256(part_path),
                "cubes": len(part),
                "start": start,
                "stop": len(joined),
            }
        )
    if tuple(joined) != whole:
        raise ValueError("ordered ICNF parts do not exactly equal the whole family")
    return {
        "schema": SCHEMA,
        "whole": {
            "path": str(whole_path),
            "sha256": sha256(whole_path),
            "cubes": len(whole),
        },
        "parts": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("whole", type=Path)
    parser.add_argument("parts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    manifest = audit_partition(arguments.whole, arguments.parts)
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(encoded, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(arguments.output)
        print(
            f"verified {manifest['whole']['cubes']} cubes across "
            f"{len(arguments.parts)} ordered parts; wrote {arguments.output}"
        )


if __name__ == "__main__":
    main()
