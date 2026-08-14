#!/usr/bin/env python3
"""Export exactly the UNKNOWN cubes from a materialized-proof manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from tools.prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cnf, read_cubes
else:
    from prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from solve_external_cubes import read_cnf, read_cubes


FRONTIER_SCHEMA = "ramsey55.materialized-proof-frontier.v1"


def export_unknown(document: dict, cubes: list[list[int]]) -> tuple[list[int], list[list[int]]]:
    results = document["results"]
    if len(results) != len(cubes):
        raise ValueError("cube/result count mismatch")
    indices: list[int] = []
    unknown: list[list[int]] = []
    for index, (cube, result) in enumerate(zip(cubes, results, strict=True)):
        if result is None or int(result["index"]) != index:
            raise ValueError(f"missing or misindexed result {index}")
        if result["cube"] != cube or result["cube_sha256"] != cube_sha256(cube):
            raise ValueError(f"cube binding mismatch at index {index}")
        status = int(result["status"])
        if status == 10:
            raise ValueError(f"SAT result at cube {index} requires investigation")
        if status == 0:
            indices.append(index)
            unknown.append(cube)
        elif status != 20:
            raise ValueError(f"invalid status {status} at cube {index}")
    return indices, unknown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.proof_manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    cubes_path = Path(document["cubes"]["path"])
    if file_sha256(cubes_path) != document["cubes"]["sha256"]:
        raise ValueError("cube-file hash mismatch")
    formula_path = Path(document["formula"]["path"])
    if file_sha256(formula_path) != document["formula"]["sha256"]:
        raise ValueError("formula hash mismatch")
    variables = read_cnf(formula_path)[2]
    cubes = read_cubes(cubes_path, variables)
    indices, unknown = export_unknown(document, cubes)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as output:
        for cube in unknown:
            output.write("a " + " ".join(map(str, cube)) + " 0\n")
    temporary.replace(arguments.output)
    output_hash = hashlib.sha256(arguments.output.read_bytes()).hexdigest()
    manifest_path = arguments.manifest or arguments.output.with_suffix(".json")
    lineage = {
        "schema": FRONTIER_SCHEMA,
        "source_manifest": str(arguments.proof_manifest),
        "source_manifest_sha256": file_sha256(arguments.proof_manifest),
        "source_cubes_sha256": document["cubes"]["sha256"],
        "source_cube_count": len(cubes),
        "verified_unsat_count": len(cubes) - len(unknown),
        "unknown_indices": indices,
        "output": str(arguments.output),
        "output_sha256": output_hash,
        "output_cube_count": len(unknown),
    }
    temporary_manifest = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary_manifest.write_text(
        json.dumps(lineage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_manifest.replace(manifest_path)
    print(json.dumps(lineage, sort_keys=True))


if __name__ == "__main__":
    main()
