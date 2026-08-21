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


def unordered_unknown_replacements(
    primary_results: list[dict[str, Any]], secondary_results: list[dict[str, Any]]
) -> list[int]:
    """Map a uniquely keyed secondary subset to UNKNOWN primary result rows."""

    if any(int(row["status"]) == 10 for row in primary_results + secondary_results):
        raise ValueError("SAT result requires investigation")
    unknown: dict[tuple[int, ...], int] = {}
    for index, row in enumerate(primary_results):
        if int(row["status"]) != 0:
            continue
        cube = tuple(int(literal) for literal in row["cube"])
        if cube in unknown:
            raise ValueError("primary UNKNOWN cubes are not unique")
        unknown[cube] = index
    replacements: list[int] = []
    seen: set[tuple[int, ...]] = set()
    for row in secondary_results:
        cube = tuple(int(literal) for literal in row["cube"])
        if cube in seen:
            raise ValueError("secondary cubes are not unique")
        seen.add(cube)
        if cube not in unknown:
            raise ValueError("secondary cube is not an UNKNOWN primary cube")
        replacements.append(unknown[cube])
    return replacements


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


def copy_deferred_search_log(
    source_root: Path,
    destination_root: Path,
    stem: str,
    result: dict[str, Any],
) -> None:
    deferred = result.get("deferred_proof")
    if deferred is None:
        return
    if not isinstance(deferred, dict):
        raise ValueError("invalid deferred-proof record")
    search_log_name = stem + ".search.log"
    copy_bound_artifact(
        source_root,
        deferred["search_log"],
        destination_root / search_log_name,
        deferred["search_log_sha256"],
    )
    deferred["search_log"] = search_log_name


def rebound_cubes_binding(
    binding: dict[str, Any],
    cubes: list[list[int]],
    variables: int,
    path: Path,
) -> dict[str, Any]:
    """Bind an identical cube family at a chain-local path."""

    if file_sha256(path) != binding["sha256"]:
        raise ValueError("rebound cube-file hash mismatch")
    if read_cubes(path, variables) != cubes:
        raise ValueError("rebound cube family mismatch")
    rebound = copy.deepcopy(binding)
    rebound["path"] = str(path)
    return rebound


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_manifest", type=Path)
    parser.add_argument("secondary_manifest", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument(
        "--allow-unordered-secondary",
        action="store_true",
        help=(
            "match a uniquely keyed UNKNOWN subset regardless of secondary "
            "row order; the strict default requires an ordered subsequence"
        ),
    )
    parser.add_argument(
        "--cubes",
        type=Path,
        help=(
            "bind the output manifest to an identical cube file at this path; "
            "its SHA-256 and ordered cube family must match the primary"
        ),
    )
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
    replacements = (
        unordered_unknown_replacements(primary_results, secondary_results)
        if arguments.allow_unordered_secondary
        else ordered_unknown_replacements(primary_results, secondary_results)
    )

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
        stem = f"cube-{index:06d}-{cube_sha256(result['cube'])[:16]}"
        copy_deferred_search_log(source_root, output, stem, result)
        if int(result["status"]) == 20:
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
    if arguments.cubes is not None:
        combined["cubes"] = rebound_cubes_binding(
            primary["cubes"], primary_cubes, variables, arguments.cubes
        )
    combined["composition"] = {
        "kind": (
            "exact unordered UNKNOWN-subset retry"
            if arguments.allow_unordered_secondary
            else "ordered UNKNOWN-only retry"
        ),
        "primary_manifest": {
            "path": str(arguments.primary_manifest),
            "sha256": file_sha256(arguments.primary_manifest),
        },
        "secondary_manifest": {
            "path": str(arguments.secondary_manifest),
            "sha256": file_sha256(arguments.secondary_manifest),
        },
        "replaced_indices": sorted(replacements),
    }
    if arguments.allow_unordered_secondary:
        combined["composition"]["secondary_to_primary_indices"] = replacements
    manifest = output / "manifest.json"
    manifest.write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(combined["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
