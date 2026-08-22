#!/usr/bin/env python3
"""Import one externally generated DRAT into a materialized-proof manifest."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

if __package__:
    from tools.prove_materialized_cubes import (
        SCHEMA,
        atomic_json,
        cube_sha256,
        file_sha256,
    )
    from tools.solve_external_cubes import read_cnf, read_cubes, render_cnf
else:
    from prove_materialized_cubes import SCHEMA, atomic_json, cube_sha256, file_sha256
    from solve_external_cubes import read_cnf, read_cubes, render_cnf


def copy_bound(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError(f"refusing to overwrite {destination}")
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno not in (errno.EXDEV, errno.EPERM, errno.EOPNOTSUPP):
            raise
        shutil.copy2(source, destination)


def summary(results: list[dict[str, Any]]) -> dict[str, int | bool]:
    statuses = [int(result["status"]) for result in results]
    return {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": statuses.count(10),
        "complete_unsat": all(status == 20 for status in statuses),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("cube_index", type=int)
    parser.add_argument("proof", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--producer-argument", action="append", default=[])
    parser.add_argument("--producer-log", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=0.0)
    arguments = parser.parse_args()
    if arguments.cube_index < 0 or arguments.seconds < 0:
        parser.error("cube_index and --seconds must be nonnegative")
    for path, label in (
        (arguments.cnf, "CNF"),
        (arguments.cubes, "cube file"),
        (arguments.proof, "proof"),
        (arguments.producer, "producer"),
        (arguments.checker, "checker"),
    ):
        if not path.is_file():
            parser.error(f"{label} does not exist: {path}")
    if arguments.proof.stat().st_size <= 0:
        parser.error("proof is empty")
    if arguments.producer_log is not None and not arguments.producer_log.is_file():
        parser.error(f"producer log does not exist: {arguments.producer_log}")
    output = arguments.output_directory
    if output.exists() and any(output.iterdir()):
        parser.error("output directory is not empty")

    before, after, variables, clauses = read_cnf(arguments.cnf)
    cubes = read_cubes(arguments.cubes, variables)
    if arguments.cube_index >= len(cubes):
        parser.error("cube_index is outside the cube file")
    augmented_texts = [
        render_cnf(before, after, variables, clauses, cube) for cube in cubes
    ]
    target = cubes[arguments.cube_index]
    target_digest = cube_sha256(target)
    stem = f"cube-{arguments.cube_index:06d}-{target_digest[:16]}"
    with tempfile.TemporaryDirectory(prefix="import-materialized-proof-") as raw:
        augmented = Path(raw) / "augmented.cnf"
        augmented.write_text(
            augmented_texts[arguments.cube_index], encoding="ascii"
        )
        checked = subprocess.run(
            [str(arguments.checker), str(augmented), str(arguments.proof)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if checked.returncode or "s VERIFIED" not in checked.stdout:
        raise RuntimeError("checker rejected imported proof")

    output.mkdir(parents=True, exist_ok=True)
    proof_name = stem + ".drat"
    checker_log_name = stem + ".checker.log"
    copy_bound(arguments.proof, output / proof_name)
    (output / checker_log_name).write_text(checked.stdout, encoding="utf-8")
    proof_hash = file_sha256(output / proof_name)
    checker_log_hash = file_sha256(output / checker_log_name)
    results: list[dict[str, Any]] = []
    for index, (cube, augmented_text) in enumerate(
        zip(cubes, augmented_texts, strict=True)
    ):
        result: dict[str, Any] = {
            "index": index,
            "cube": cube,
            "cube_sha256": cube_sha256(cube),
            "augmented_cnf_sha256": hashlib.sha256(
                augmented_text.encode("ascii")
            ).hexdigest(),
            "status": 0,
            "seconds": 0.0,
        }
        if index == arguments.cube_index:
            result.update(
                {
                    "status": 20,
                    "seconds": arguments.seconds,
                    "proof": proof_name,
                    "proof_bytes": (output / proof_name).stat().st_size,
                    "proof_sha256": proof_hash,
                    "checker_log": checker_log_name,
                    "checker_log_sha256": checker_log_hash,
                    "imported_external_proof": {
                        "source_path": str(arguments.proof),
                        "source_sha256": file_sha256(arguments.proof),
                    },
                }
            )
        results.append(result)
    if arguments.producer_log is not None:
        results[arguments.cube_index]["imported_external_proof"].update(
            {
                "producer_log": str(arguments.producer_log),
                "producer_log_sha256": file_sha256(arguments.producer_log),
            }
        )

    document = {
        "schema": SCHEMA,
        "formula": {
            "path": str(arguments.cnf),
            "sha256": file_sha256(arguments.cnf),
            "variables": variables,
            "clauses": clauses,
        },
        "cubes": {
            "path": str(arguments.cubes),
            "sha256": file_sha256(arguments.cubes),
            "count": len(cubes),
        },
        "solver": {
            "path": str(arguments.producer),
            "sha256": file_sha256(arguments.producer),
            "arguments": arguments.producer_argument,
        },
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "per_cube_seconds": arguments.seconds,
        "compact_proof": False,
        "deferred_proof": False,
        "scratch_directory": None,
        "jobs": 1,
        "results": results,
        "summary": summary(results),
    }
    atomic_json(output / "manifest.json", document)
    print(json.dumps(document["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
