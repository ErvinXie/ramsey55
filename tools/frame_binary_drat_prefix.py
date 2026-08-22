#!/usr/bin/env python3
"""Frame a stopped binary DRAT snapshot at its last complete clause."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, BinaryIO


SCHEMA = "ramsey55.binary-drat-prefix-framing.v1"
REPLAY_SCHEMA = "ramsey55.cadical-dfs-prefix-replay.v1"
BLOCK_SIZE = 1 << 23


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def last_clause_boundary(stream: BinaryIO, size: int) -> int:
    """Return the byte offset immediately after the final NUL terminator."""
    end = size
    while end:
        start = max(0, end - BLOCK_SIZE)
        stream.seek(start)
        block = stream.read(end - start)
        position = block.rfind(b"\0")
        if position >= 0:
            return start + position + 1
        end = start
    raise ValueError("binary DRAT prefix has no complete clause terminator")


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_prefix", type=Path)
    parser.add_argument("replay_manifest", type=Path)
    parser.add_argument("framed_prefix", type=Path)
    parser.add_argument("framed_replay_manifest", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    for path in (arguments.source_prefix, arguments.replay_manifest):
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    outputs = (
        arguments.framed_prefix,
        arguments.framed_replay_manifest,
        arguments.manifest,
    )
    if any(path.exists() for path in outputs):
        parser.error("refusing to overwrite an output")
    temporaries = tuple(path.with_suffix(path.suffix + ".tmp") for path in outputs)
    if any(path.exists() for path in temporaries):
        parser.error("refusing to overwrite a temporary output")

    replay = json.loads(arguments.replay_manifest.read_text(encoding="utf-8"))
    if not isinstance(replay, dict) or replay.get("schema") != REPLAY_SCHEMA:
        raise ValueError("unexpected DFS replay manifest schema")

    source_size = arguments.source_prefix.stat().st_size
    with arguments.source_prefix.open("rb") as source:
        framed_size = last_clause_boundary(source, source_size)
    truncated_size = source_size - framed_size

    source_digest = hashlib.sha256()
    framed_digest = hashlib.sha256()
    tail_digest = hashlib.sha256()
    prefix_temporary = temporaries[0]
    try:
        position = 0
        with arguments.source_prefix.open("rb") as source, prefix_temporary.open(
            "wb"
        ) as target:
            for block in iter(lambda: source.read(BLOCK_SIZE), b""):
                source_digest.update(block)
                boundary = max(0, min(len(block), framed_size - position))
                if boundary:
                    kept = block[:boundary]
                    target.write(kept)
                    framed_digest.update(kept)
                tail_digest.update(block[boundary:])
                position += len(block)

        source_hash = source_digest.hexdigest()
        replay_source_hash = replay.get("proof_prefix_sha256")
        if replay_source_hash is not None and replay_source_hash != source_hash:
            raise ValueError("source prefix hash does not match replay manifest")

        framed_hash = framed_digest.hexdigest()
        derived_replay = dict(replay)
        derived_replay["proof_prefix"] = str(arguments.framed_prefix)
        derived_replay["proof_prefix_sha256"] = framed_hash
        derived_replay["proof_prefix_source_sha256"] = source_hash
        derived_replay["proof_prefix_truncated_bytes"] = truncated_size
        atomic_json(arguments.framed_replay_manifest, derived_replay)

        prefix_temporary.replace(arguments.framed_prefix)
        document = {
            "schema": SCHEMA,
            "source_prefix": {
                "path": str(arguments.source_prefix),
                "sha256": source_hash,
                "size": source_size,
            },
            "source_replay_manifest": file_record(arguments.replay_manifest),
            "source_replay_bound_prefix": replay_source_hash is not None,
            "framed_prefix": {
                "path": str(arguments.framed_prefix),
                "sha256": framed_hash,
                "size": framed_size,
                "ends_at_clause_boundary": True,
            },
            "truncated_tail": {
                "sha256": tail_digest.hexdigest(),
                "size": truncated_size,
            },
            "framed_replay_manifest": file_record(
                arguments.framed_replay_manifest
            ),
        }
        atomic_json(arguments.manifest, document)
    finally:
        for temporary in temporaries:
            if temporary.exists():
                temporary.unlink()

    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
