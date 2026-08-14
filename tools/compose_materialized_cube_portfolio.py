#!/usr/bin/env python3
"""Select and bind the best independently checked proof from each solver run."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.compose_materialized_cube_proofs import (
        bind_effective_solver,
        copy_bound_artifact,
        expected_summary,
        validate_document,
    )
    from tools.prove_materialized_cubes import cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from compose_materialized_cube_proofs import (
        bind_effective_solver,
        copy_bound_artifact,
        expected_summary,
        validate_document,
    )
    from prove_materialized_cubes import cube_sha256, file_sha256
    from solve_external_cubes import read_cubes


def selected_sources(documents: list[dict[str, Any]]) -> list[int]:
    count = len(documents[0]["results"])
    selected: list[int] = []
    for index in range(count):
        candidates = [document["results"][index] for document in documents]
        statuses = [int(result["status"]) for result in candidates]
        if 10 in statuses:
            raise ValueError(f"SAT result at cube {index} requires investigation")
        if any(status not in (0, 20) for status in statuses):
            raise ValueError(f"invalid portfolio status at cube {index}")
        verified = [
            source for source, status in enumerate(statuses) if status == 20
        ]
        selected.append(
            min(
                verified,
                key=lambda source: (int(candidates[source]["proof_bytes"]), source),
            )
            if verified
            else 0
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("manifests", type=Path, nargs="+")
    arguments = parser.parse_args()
    if len(arguments.manifests) < 2:
        parser.error("a portfolio needs at least two proof manifests")

    documents = [
        json.loads(manifest.read_text(encoding="utf-8"))
        for manifest in arguments.manifests
    ]
    for document in documents:
        validate_document(document)
    base = documents[0]
    for source, document in enumerate(documents[1:], start=1):
        for key in ("formula", "cubes", "checker"):
            if document[key] != base[key]:
                raise ValueError(f"portfolio source {source} {key} mismatch")

    variables = int(base["formula"]["variables"])
    cubes_path = Path(base["cubes"]["path"])
    if file_sha256(cubes_path) != base["cubes"]["sha256"]:
        raise ValueError("portfolio cube-file hash mismatch")
    cubes = read_cubes(cubes_path, variables)
    if len(cubes) != int(base["cubes"]["count"]):
        raise ValueError("portfolio cube count mismatch")
    for source, document in enumerate(documents):
        results = document["results"]
        if len(results) != len(cubes):
            raise ValueError(f"portfolio source {source} result count mismatch")
        for index, (cube, result) in enumerate(zip(cubes, results, strict=True)):
            if (
                int(result["index"]) != index
                or result["cube"] != cube
                or result["cube_sha256"] != cube_sha256(cube)
            ):
                raise ValueError(
                    f"portfolio source {source} cube binding mismatch at {index}"
                )

    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("output directory is not empty")
    sources = selected_sources(documents)
    combined_results: list[dict[str, Any]] = []
    for index, (cube, source) in enumerate(zip(cubes, sources, strict=True)):
        chosen = copy.deepcopy(documents[source]["results"][index])
        attempts = [
            float(document["results"][index]["seconds"])
            for document in documents
        ]
        chosen["seconds"] = round(sum(attempts), 6)
        chosen["portfolio_attempt_seconds"] = attempts
        bind_effective_solver(
            chosen, documents[source]["solver"], base["solver"]
        )
        if int(chosen["status"]) == 20:
            stem = f"cube-{index:06d}-{cube_sha256(cube)[:16]}"
            proof_name = stem + ".drat"
            log_name = stem + ".checker.log"
            source_root = arguments.manifests[source].parent
            copy_bound_artifact(
                source_root,
                chosen["proof"],
                output / proof_name,
                chosen["proof_sha256"],
            )
            copy_bound_artifact(
                source_root,
                chosen["checker_log"],
                output / log_name,
                chosen["checker_log_sha256"],
            )
            chosen["proof"] = proof_name
            chosen["checker_log"] = log_name
            if "compaction" in chosen:
                compact_log_name = stem + ".compact.log"
                copy_bound_artifact(
                    source_root,
                    chosen["compaction"]["log"],
                    output / compact_log_name,
                    chosen["compaction"]["log_sha256"],
                )
                chosen["compaction"]["log"] = compact_log_name
        combined_results.append(chosen)

    combined = copy.deepcopy(base)
    combined["per_cube_seconds"] = max(
        float(document["per_cube_seconds"]) for document in documents
    )
    combined["jobs"] = max(int(document["jobs"]) for document in documents)
    combined["results"] = combined_results
    combined["summary"] = expected_summary(combined_results)
    combined["portfolio"] = {
        "kind": "smallest verified proof per identical materialized cube",
        "sources": [
            {
                "path": str(manifest),
                "sha256": file_sha256(manifest),
                "solver": document["solver"],
            }
            for manifest, document in zip(arguments.manifests, documents, strict=True)
        ],
        "selected_source": sources,
    }
    manifest = output / "manifest.json"
    manifest.write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(combined["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
