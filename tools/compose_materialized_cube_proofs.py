#!/usr/bin/env python3
"""Compose a full materialized-proof manifest with an UNKNOWN-only retry."""

from __future__ import annotations

import argparse
import copy
import errno
import json
import os
import shutil
from pathlib import Path
from typing import Any

if __package__:
    from tools.prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from solve_external_cubes import read_cubes


def artifact(root: Path, name: object) -> Path:
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError(f"invalid artifact name {name!r}")
    return root / name


def expected_summary(results: list[dict[str, Any]]) -> dict[str, int | bool]:
    statuses = [int(result["status"]) for result in results]
    return {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": statuses.count(10),
        "complete_unsat": all(status == 20 for status in statuses),
    }


def validate_document(document: dict[str, Any]) -> None:
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    results = document.get("results")
    if not isinstance(results, list) or any(not isinstance(row, dict) for row in results):
        raise ValueError("manifest has incomplete results")
    if document.get("summary") != expected_summary(results):
        raise ValueError("manifest summary mismatch")
    if int(document["cubes"]["count"]) != len(results):
        raise ValueError("cube/result count mismatch")
    if any(int(row["status"]) not in (0, 10, 20) for row in results):
        raise ValueError("invalid materialized-proof status")


def bind_effective_solver(
    result: dict[str, Any],
    source_solver: dict[str, Any],
    output_solver: dict[str, Any],
) -> None:
    """Record a per-result override only when it differs from the output default."""

    effective = result.get("solver", source_solver)
    if effective == output_solver:
        result.pop("solver", None)
    else:
        result["solver"] = copy.deepcopy(effective)


def ordered_unknown_replacements(
    primary_results: list[dict[str, Any]], secondary_results: list[dict[str, Any]]
) -> list[int]:
    """Map an ordered secondary subsequence to UNKNOWN primary result rows."""

    if any(int(row["status"]) == 10 for row in primary_results + secondary_results):
        raise ValueError("SAT result requires investigation")
    indices: list[int] = []
    cursor = 0
    for secondary in secondary_results:
        cube = secondary["cube"]
        while cursor < len(primary_results):
            primary = primary_results[cursor]
            if int(primary["status"]) == 0 and primary["cube"] == cube:
                break
            cursor += 1
        if cursor == len(primary_results):
            raise ValueError("secondary cube is not an ordered UNKNOWN subsequence")
        indices.append(cursor)
        cursor += 1
    return indices


def copy_bound_artifact(
    source_root: Path,
    source_name: object,
    destination: Path,
    expected_hash: object,
) -> None:
    source = artifact(source_root, source_name)
    if file_sha256(source) != expected_hash:
        raise ValueError(f"source artifact hash mismatch: {source}")
    if destination.exists():
        raise ValueError(f"refusing to overwrite artifact {destination}")
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno not in (errno.EXDEV, errno.EPERM, errno.EOPNOTSUPP):
            raise
        shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_manifest", type=Path)
    parser.add_argument("secondary_manifest", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = parser.parse_args()

    primary = json.loads(arguments.primary_manifest.read_text(encoding="utf-8"))
    secondary = json.loads(arguments.secondary_manifest.read_text(encoding="utf-8"))
    validate_document(primary)
    validate_document(secondary)
    for key in ("formula", "checker"):
        if primary[key] != secondary[key]:
            raise ValueError(f"primary/secondary {key} mismatch")

    variables = int(primary["formula"]["variables"])
    primary_cubes_path = Path(primary["cubes"]["path"])
    secondary_cubes_path = Path(secondary["cubes"]["path"])
    if file_sha256(primary_cubes_path) != primary["cubes"]["sha256"]:
        raise ValueError("primary cube-file hash mismatch")
    if file_sha256(secondary_cubes_path) != secondary["cubes"]["sha256"]:
        raise ValueError("secondary cube-file hash mismatch")
    primary_cubes = read_cubes(primary_cubes_path, variables)
    secondary_cubes = read_cubes(secondary_cubes_path, variables)
    primary_results: list[dict[str, Any]] = primary["results"]
    secondary_results: list[dict[str, Any]] = secondary["results"]
    if [row["cube"] for row in primary_results] != primary_cubes:
        raise ValueError("primary result/cube mismatch")
    if [row["cube"] for row in secondary_results] != secondary_cubes:
        raise ValueError("secondary result/cube mismatch")
    replacements = ordered_unknown_replacements(primary_results, secondary_results)

    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("output directory is not empty")

    selected = {
        index: row
        for index, row in zip(replacements, secondary_results, strict=True)
    }
    combined_results: list[dict[str, Any]] = []
    for index, primary_result in enumerate(primary_results):
        source_root = arguments.primary_manifest.parent
        result = copy.deepcopy(primary_result)
        if index in selected:
            source_root = arguments.secondary_manifest.parent
            result = copy.deepcopy(selected[index])
            bind_effective_solver(result, secondary["solver"], primary["solver"])
            if (
                result["cube"] != primary_result["cube"]
                or result["cube_sha256"] != primary_result["cube_sha256"]
                or result["augmented_cnf_sha256"]
                != primary_result["augmented_cnf_sha256"]
            ):
                raise ValueError(f"replacement binding mismatch at primary row {index}")
            result["previous_attempt_seconds"] = float(primary_result["seconds"])
            result["seconds"] = round(
                float(primary_result["seconds"]) + float(result["seconds"]), 6
            )
        else:
            bind_effective_solver(result, primary["solver"], primary["solver"])
        result["index"] = index
        if int(result["status"]) == 20:
            stem = f"cube-{index:06d}-{cube_sha256(result['cube'])[:16]}"
            proof_name = stem + ".drat"
            log_name = stem + ".checker.log"
            copy_bound_artifact(
                source_root, result["proof"], output / proof_name, result["proof_sha256"]
            )
            copy_bound_artifact(
                source_root,
                result["checker_log"],
                output / log_name,
                result["checker_log_sha256"],
            )
            result["proof"] = proof_name
            result["checker_log"] = log_name
            if "compaction" in result:
                compact_log_name = stem + ".compact.log"
                copy_bound_artifact(
                    source_root,
                    result["compaction"]["log"],
                    output / compact_log_name,
                    result["compaction"]["log_sha256"],
                )
                result["compaction"]["log"] = compact_log_name
        combined_results.append(result)

    combined = copy.deepcopy(primary)
    combined["per_cube_seconds"] = max(
        float(primary["per_cube_seconds"]), float(secondary["per_cube_seconds"])
    )
    combined["jobs"] = max(int(primary["jobs"]), int(secondary["jobs"]))
    combined["results"] = combined_results
    combined["summary"] = expected_summary(combined_results)
    combined["composition"] = {
        "kind": "ordered UNKNOWN-only retry",
        "primary_manifest": {
            "path": str(arguments.primary_manifest),
            "sha256": file_sha256(arguments.primary_manifest),
        },
        "secondary_manifest": {
            "path": str(arguments.secondary_manifest),
            "sha256": file_sha256(arguments.secondary_manifest),
        },
        "replaced_indices": replacements,
    }
    manifest = output / "manifest.json"
    manifest.write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(combined["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
