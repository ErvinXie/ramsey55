#!/usr/bin/env python3
"""Atomically replay and split one clean CaDiCaL DFS checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from replay_cadical_dfs_prefix import HEADER as REPLAY_HEADER
from replay_cadical_dfs_prefix import SCHEMA as REPLAY_SCHEMA
from replay_cadical_dfs_prefix import read_roots, replay_forest
from split_icnf_roots import SCHEMA as SPLIT_SCHEMA


SCHEMA = "ramsey55.cadical-dfs-checkpoint-recovery.v1"
HEADER = REPLAY_HEADER
PRODUCER_KEYS = {
    "conflicts",
    "maximum_conflicts",
    "maximum_lookahead_seconds",
    "maximum_primary_split_variable",
    "maximum_solve_seconds",
    "maximum_wall_seconds",
    "freeze_policy",
    "cadical_seed",
    "cadical_phase",
    "proof_fragment",
    "root_index",
    "initial_frozen_variables",
    "checkpoint",
    "status",
    "attempts",
    "splits",
    "maximum_extra_depth",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path, sha256: str | None = None) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256 or file_sha256(path),
    }


def read_producer_log(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(), 1
    ):
        fields = line.split("\t")
        if len(fields) != 2 or not fields[0] or not fields[1]:
            raise ValueError(f"invalid producer log row {path}:{line_number}")
        if fields[0] in settings:
            raise ValueError(f"duplicate producer log key: {fields[0]}")
        settings[fields[0]] = fields[1]
    if set(settings) != PRODUCER_KEYS:
        raise ValueError("producer log key set is not exact")
    fixed = {
        "freeze_policy": "selective",
        "proof_fragment": "1",
        "root_index": "all",
        "checkpoint": "1",
        "status": "0",
    }
    if any(settings[key] != value for key, value in fixed.items()):
        raise ValueError("producer log is not a clean incomplete checkpoint")
    integer_keys = (
        "conflicts",
        "maximum_conflicts",
        "maximum_primary_split_variable",
        "cadical_seed",
        "cadical_phase",
        "initial_frozen_variables",
        "attempts",
        "splits",
        "maximum_extra_depth",
    )
    for key in integer_keys:
        if re.fullmatch(r"0|[1-9][0-9]*", settings[key]) is None:
            raise ValueError(f"invalid integer producer setting: {key}")
    if int(settings["conflicts"]) <= 0:
        raise ValueError("producer conflict limit is not positive")
    if int(settings["maximum_conflicts"]) < int(settings["conflicts"]):
        raise ValueError("producer maximum conflict limit is too small")
    if int(settings["cadical_phase"]) not in (0, 1):
        raise ValueError("invalid producer phase")
    for key in (
        "maximum_lookahead_seconds",
        "maximum_solve_seconds",
        "maximum_wall_seconds",
    ):
        try:
            value = float(settings[key])
        except ValueError as error:
            raise ValueError(f"invalid floating producer setting: {key}") from error
        if value < 0:
            raise ValueError(f"negative producer setting: {key}")
    return settings


def require_exit_zero(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    statuses = re.findall(
        r"^\s*Exit status:\s*([^\s]+)\s*$", text, flags=re.MULTILINE
    )
    if statuses != ["0"]:
        raise ValueError("expected one GNU-time exit status 0")


def json_bytes(document: dict[str, object]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def prepare(
    source_root: Path,
    snapshot: Path,
    proof_prefix: Path,
    producer_log: Path,
    producer_time_log: Path,
    output_prefix: Path,
) -> dict[str, object]:
    source_root = source_root.resolve()
    snapshot = snapshot.resolve()
    proof_prefix = proof_prefix.resolve()
    producer_log = producer_log.resolve()
    producer_time_log = producer_time_log.resolve()
    output_prefix = output_prefix.resolve()
    for path in (
        source_root,
        snapshot,
        proof_prefix,
        producer_log,
        producer_time_log,
    ):
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing or empty artifact: {path}")
    if not output_prefix.parent.is_dir() or not output_prefix.name:
        raise ValueError("output-prefix parent must exist")
    settings = read_producer_log(producer_log)
    require_exit_zero(producer_time_log)
    with proof_prefix.open("rb") as stream:
        stream.seek(-1, 2)
        if stream.read(1) != b"\0":
            raise ValueError("proof prefix is not at a binary DRAT boundary")

    roots = read_roots(source_root)
    if len(roots) != 1:
        raise ValueError("recovery preparation requires exactly one source root")
    if int(settings.get("cubes", "1")) != 1:
        raise ValueError("producer root count is not one")
    frontier, replay = replay_forest(roots, snapshot)
    if not frontier:
        raise ValueError("checkpoint already closes the source root")
    if int(settings["attempts"]) != replay["attempts"]:
        raise ValueError("producer/replay attempt count mismatch")
    if int(settings["splits"]) != replay["splits"]:
        raise ValueError("producer/replay split count mismatch")
    deepest_frontier = max(len(cube) - len(roots[0]) for cube in frontier)
    producer_depth = int(settings["maximum_extra_depth"])
    allowed_depths = {int(replay["maximum_depth"]), deepest_frontier}
    if producer_depth not in allowed_depths:
        raise ValueError("producer maximum depth is inconsistent with replay")

    frontier_path = output_prefix.with_suffix(".frontier.icnf")
    replay_path = output_prefix.with_suffix(".replay.json")
    split_path = output_prefix.with_suffix(".split.json")
    manifest_path = output_prefix.with_suffix(".manifest.json")
    root_paths = tuple(
        output_prefix.with_name(f"{output_prefix.name}-root{index:03d}.icnf")
        for index in range(len(frontier))
    )
    outputs = (frontier_path, replay_path, split_path, manifest_path) + root_paths
    temporaries = tuple(path.with_suffix(path.suffix + ".tmp") for path in outputs)
    if any(path.exists() for path in outputs + temporaries):
        raise ValueError("refusing to overwrite recovery output")

    frontier_payload = b"".join(
        ("a " + " ".join(map(str, cube)) + " 0\n").encode("ascii")
        for cube in frontier
    )
    root_payloads = tuple(
        ("a " + " ".join(map(str, cube)) + " 0\n").encode("ascii")
        for cube in frontier
    )
    proof_sha256 = file_sha256(proof_prefix)
    replay_document: dict[str, object] = {
        "schema": REPLAY_SCHEMA,
        "source_root": str(source_root),
        "source_root_sha256": file_sha256(source_root),
        "snapshot": str(snapshot),
        "snapshot_sha256": file_sha256(snapshot),
        "snapshot_rows": replay["attempts"],
        "processed_attempts": replay["attempts"],
        "processed_splits": replay["splits"],
        "maximum_processed_depth": replay["maximum_depth"],
        "source_root_count": 1,
        "root_frontier_counts": replay["root_frontier_counts"],
        "output": str(frontier_path),
        "output_sha256": hashlib.sha256(frontier_payload).hexdigest(),
        "output_count": len(frontier),
        "proof_prefix": str(proof_prefix),
        "proof_prefix_sha256": proof_sha256,
    }
    split_records = [
        {
            "index": index,
            "path": str(path),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }
        for index, (path, payload) in enumerate(zip(root_paths, root_payloads))
    ]
    split_document: dict[str, object] = {
        "schema": SPLIT_SCHEMA,
        "source_frontier": {
            "path": str(frontier_path),
            "sha256": hashlib.sha256(frontier_payload).hexdigest(),
            "count": len(frontier),
        },
        "output_prefix": str(output_prefix),
        "outputs": split_records,
    }
    replay_payload = json_bytes(replay_document)
    split_payload = json_bytes(split_document)
    manifest_document: dict[str, object] = {
        "schema": SCHEMA,
        "verified": True,
        "preparer": artifact(Path(__file__).resolve()),
        "source_root": artifact(source_root),
        "snapshot": artifact(snapshot),
        "proof_prefix": artifact(proof_prefix, proof_sha256),
        "producer_log": artifact(producer_log),
        "producer_time_log": artifact(producer_time_log),
        "producer_settings": settings,
        "frontier": {
            "path": str(frontier_path),
            "bytes": len(frontier_payload),
            "sha256": hashlib.sha256(frontier_payload).hexdigest(),
        },
        "replay_manifest": {
            "path": str(replay_path),
            "bytes": len(replay_payload),
            "sha256": hashlib.sha256(replay_payload).hexdigest(),
        },
        "split_manifest": {
            "path": str(split_path),
            "bytes": len(split_payload),
            "sha256": hashlib.sha256(split_payload).hexdigest(),
        },
        "roots": split_records,
        "summary": {
            "source_roots": 1,
            "processed_attempts": replay["attempts"],
            "processed_splits": replay["splits"],
            "frontier_roots": len(frontier),
            "proof_prefix_framed": True,
            "producer_checkpoint": True,
            "producer_exit_zero": True,
        },
    }
    payloads = (
        frontier_payload,
        replay_payload,
        split_payload,
        json_bytes(manifest_document),
    ) + root_payloads
    try:
        for temporary, payload in zip(temporaries, payloads, strict=True):
            temporary.write_bytes(payload)
        for temporary, output in zip(temporaries, outputs, strict=True):
            temporary.replace(output)
    finally:
        for temporary in temporaries:
            if temporary.exists():
                temporary.unlink()
    return manifest_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("proof_prefix", type=Path)
    parser.add_argument("producer_log", type=Path)
    parser.add_argument("producer_time_log", type=Path)
    parser.add_argument("output_prefix", type=Path)
    arguments = parser.parse_args()
    try:
        document = prepare(**vars(arguments))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(document["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
