#!/usr/bin/env python3
"""Freeze completed rows from a live materialized-proof progress document."""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

if __package__:
    from tools.prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cnf, read_cubes, render_cnf
else:
    from prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from solve_external_cubes import read_cnf, read_cubes, render_cnf


def artifact(root: Path, name: object) -> Path:
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError(f"invalid artifact name {name!r}")
    return root / name


def copy_bound_artifact(
    source_root: Path,
    destination_root: Path,
    name: object,
    expected_hash: object,
) -> None:
    source = artifact(source_root, name)
    destination = artifact(destination_root, name)
    if not isinstance(expected_hash, str) or file_sha256(source) != expected_hash:
        raise ValueError(f"source artifact hash mismatch: {source}")
    if destination.exists():
        raise ValueError(f"refusing to overwrite artifact {destination}")
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno not in (errno.EXDEV, errno.EPERM, errno.EOPNOTSUPP):
            raise
        shutil.copy2(source, destination)


def copy_result_artifacts(
    source_root: Path, destination_root: Path, result: dict[str, Any]
) -> None:
    status = int(result["status"])
    if status == 10:
        raise ValueError("SAT result requires investigation")
    if status == 0:
        return
    if status != 20:
        raise ValueError(f"invalid materialized-proof status {status}")
    copy_bound_artifact(
        source_root, destination_root, result["proof"], result["proof_sha256"]
    )
    copy_bound_artifact(
        source_root,
        destination_root,
        result["checker_log"],
        result["checker_log_sha256"],
    )
    compaction = result.get("compaction")
    if compaction is not None:
        if not isinstance(compaction, dict):
            raise ValueError("invalid proof compaction record")
        copy_bound_artifact(
            source_root,
            destination_root,
            compaction["log"],
            compaction["log_sha256"],
        )


def expected_summary(results: list[dict[str, Any]]) -> dict[str, int | bool]:
    statuses = [int(result["status"]) for result in results]
    return {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": statuses.count(10),
        "complete_unsat": all(status == 20 for status in statuses),
    }


def discover_published_unsat(
    source_root: Path,
    index: int,
    cube: list[int],
    augmented_hash: str,
) -> dict[str, Any] | None:
    """Recover an atomically published proof not yet flushed to progress.json."""

    digest = cube_sha256(cube)
    stem = f"cube-{index:06d}-{digest[:16]}"
    proof = source_root / f"{stem}.drat"
    checker_log = source_root / f"{stem}.checker.log"
    if not proof.exists() and not checker_log.exists():
        return None
    if not proof.is_file() or not checker_log.is_file():
        raise ValueError(f"partially published proof artifacts at index {index}")
    if proof.stat().st_size <= 0 or "s VERIFIED" not in checker_log.read_text(
        encoding="utf-8", errors="replace"
    ):
        raise ValueError(f"invalid published proof artifacts at index {index}")
    return {
        "index": index,
        "cube": cube,
        "cube_sha256": digest,
        "augmented_cnf_sha256": augmented_hash,
        "status": 20,
        # Timing telemetry is not certificate-bearing and was not flushed by
        # the still-live worker.  Record the conservative neutral value.
        "seconds": 0.0,
        "proof": proof.name,
        "proof_bytes": proof.stat().st_size,
        "proof_sha256": file_sha256(proof),
        "checker_log": checker_log.name,
        "checker_log_sha256": file_sha256(checker_log),
    }


def finalize(progress_path: Path, output: Path) -> dict[str, Any]:
    progress_bytes = progress_path.read_bytes()
    document = json.loads(progress_bytes)
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof progress schema")
    if output.exists():
        raise ValueError(f"refusing to overwrite output directory {output}")

    formula = document["formula"]
    cubes_entry = document["cubes"]
    cnf_path = Path(formula["path"])
    cubes_path = Path(cubes_entry["path"])
    if file_sha256(cnf_path) != formula["sha256"]:
        raise ValueError("formula hash mismatch")
    if file_sha256(cubes_path) != cubes_entry["sha256"]:
        raise ValueError("cube-file hash mismatch")
    before, after, variables, clauses = read_cnf(cnf_path)
    if (variables, clauses) != (
        int(formula["variables"]),
        int(formula["clauses"]),
    ):
        raise ValueError("formula shape mismatch")
    cubes = read_cubes(cubes_path, variables)
    source_results = document.get("results")
    if (
        not isinstance(source_results, list)
        or len(source_results) != len(cubes)
        or len(cubes) != int(cubes_entry["count"])
    ):
        raise ValueError("cube/result count mismatch")

    results: list[dict[str, Any]] = []
    placeholders: list[int] = []
    discovered: list[int] = []
    source_root = progress_path.parent
    for index, (cube, source) in enumerate(zip(cubes, source_results, strict=True)):
        augmented = render_cnf(before, after, variables, clauses, cube)
        augmented_hash = hashlib.sha256(augmented.encode("ascii")).hexdigest()
        if source is None:
            published = discover_published_unsat(
                source_root, index, cube, augmented_hash
            )
            if published is not None:
                discovered.append(index)
                results.append(published)
                continue
            placeholders.append(index)
            results.append(
                {
                    "index": index,
                    "cube": cube,
                    "cube_sha256": cube_sha256(cube),
                    "augmented_cnf_sha256": augmented_hash,
                    "status": 0,
                    "seconds": 0.0,
                }
            )
            continue
        if not isinstance(source, dict) or int(source.get("index", -1)) != index:
            raise ValueError(f"missing or misindexed result {index}")
        result = copy.deepcopy(source)
        if (
            result.get("cube") != cube
            or result.get("cube_sha256") != cube_sha256(cube)
            or result.get("augmented_cnf_sha256") != augmented_hash
        ):
            raise ValueError(f"cube binding mismatch at index {index}")
        if float(result.get("seconds", -1)) < 0:
            raise ValueError(f"negative solve time at index {index}")
        results.append(result)

    if not placeholders:
        raise ValueError("progress document is already complete")
    if not any(int(result["status"]) == 20 for result in results):
        raise ValueError("progress document has no completed UNSAT proof")

    output.mkdir(parents=True)
    for result in results:
        copy_result_artifacts(source_root, output, result)
    snapshot = output / "source-progress.json"
    snapshot.write_bytes(progress_bytes)

    finalized = copy.deepcopy(document)
    finalized["results"] = results
    finalized["summary"] = expected_summary(results)
    finalized["scratch_directory"] = None
    finalized["progress_snapshot"] = {
        "path": str(snapshot),
        "sha256": hashlib.sha256(progress_bytes).hexdigest(),
        "discovered_unsat_indices": discovered,
        "placeholder_unknown_indices": placeholders,
    }
    manifest = output / "manifest.json"
    temporary = manifest.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(finalized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(manifest)
    return finalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("progress", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()
    finalized = finalize(arguments.progress, arguments.output_directory)
    print(json.dumps(finalized["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
