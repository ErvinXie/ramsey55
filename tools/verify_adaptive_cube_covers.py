#!/usr/bin/env python3
"""Verify every local cube cover emitted by an adaptive search directory."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path

from verify_cube_cover import cover_by_dpll, read_cubes, reduce_cover


NAME = re.compile(r"r([0-9]{3})-[0-9a-f]{20}\.cubes")


def verify(path: Path, root: Path) -> dict:
    match = NAME.fullmatch(path.name)
    if match is None:
        raise ValueError(f"unexpected adaptive cube filename: {path.name}")
    if path.stat().st_size == 0:
        log_path = path.with_suffix(".log")
        results_path = path.with_suffix(".tsv")
        if not log_path.is_file() or not results_path.is_file():
            raise ValueError(f"empty cube file lacks companion status files: {path}")
        log_lines = log_path.read_text(encoding="ascii").splitlines()
        valid_log_prefix = (
            len(log_lines) >= 3
            and log_lines[0] == "status\t20"
            and log_lines[1].startswith("variables\t")
            and log_lines[1].split("\t", 1)[1].isdigit()
            and int(log_lines[1].split("\t", 1)[1]) > 0
            and log_lines[2] == "cubes\t0"
        )
        if not valid_log_prefix:
            raise ValueError(f"empty cube file is not a recorded cuber UNSAT: {path}")
        if results_path.read_text(encoding="ascii") != "cube\tstatus\tseconds\tmodel\n":
            raise ValueError(f"empty cube result table is not header-only: {path}")
        return {
            "cube_count": 0,
            "depth_histogram": {},
            "dpll_nodes": 0,
            "kind": "trusted-cuber-unsat",
            "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
            "path": str(path.relative_to(root)),
            "reduction_completed": False,
            "reduction_steps": 0,
            "residual_count": 0,
            "results_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
            "round": int(match.group(1)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    cubes = read_cubes(path)
    reduced, steps, residual = reduce_cover(cubes)
    covered, dpll_nodes, witness = cover_by_dpll(cubes)
    if not covered:
        raise ValueError(
            f"cube set does not cover its parent: {path}; witness={witness}"
        )
    return {
        "cube_count": len(cubes),
        "depth_histogram": dict(sorted(Counter(map(len, cubes)).items())),
        "dpll_nodes": dpll_nodes,
        "kind": "checked-cover",
        "path": str(path.relative_to(root)),
        "reduction_completed": reduced,
        "reduction_steps": len(steps),
        "residual_count": len(residual),
        "round": int(match.group(1)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        raise ValueError("--jobs must be positive")
    paths = sorted(arguments.directory.glob("r[0-9][0-9][0-9]-*.cubes"))
    if not paths:
        raise ValueError("no adaptive cube files found")
    entries: list[dict] = []
    if arguments.jobs == 1:
        verified = map(verify, paths, itertools.repeat(arguments.directory))
        for count, entry in enumerate(verified, start=1):
            entries.append(entry)
            if count % 100 == 0:
                print(f"verified {count}/{len(paths)}", flush=True)
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=arguments.jobs
        ) as executor:
            verified = executor.map(
                verify,
                paths,
                itertools.repeat(arguments.directory),
                chunksize=4,
            )
            for count, entry in enumerate(verified, start=1):
                entries.append(entry)
                if count % 100 == 0:
                    print(f"verified {count}/{len(paths)}", flush=True)
    aggregate = hashlib.sha256()
    for entry in entries:
        aggregate.update(entry["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(entry["sha256"].encode("ascii"))
        aggregate.update(b"\0")
        for companion in ("log_sha256", "results_sha256"):
            if companion in entry:
                aggregate.update(companion.encode("ascii"))
                aggregate.update(b"\0")
                aggregate.update(entry[companion].encode("ascii"))
                aggregate.update(b"\0")
    summary = {
        "aggregate_sha256": aggregate.hexdigest(),
        "directory": str(arguments.directory),
        "file_count": len(entries),
        "checked_cover_count": sum(
            entry["kind"] == "checked-cover" for entry in entries
        ),
        "trusted_cuber_unsat_count": sum(
            entry["kind"] == "trusted-cuber-unsat" for entry in entries
        ),
        "round_file_counts": dict(
            sorted(Counter(entry["round"] for entry in entries).items())
        ),
        "total_cubes": sum(entry["cube_count"] for entry in entries),
        "total_dpll_nodes": sum(entry["dpll_nodes"] for entry in entries),
        "total_reduction_steps": sum(entry["reduction_steps"] for entry in entries),
    }
    if arguments.manifest is not None:
        manifest = dict(summary)
        manifest["files"] = entries
        temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
        temporary.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(arguments.manifest)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
