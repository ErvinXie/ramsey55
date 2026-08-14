#!/usr/bin/env python3
"""Independently replay a materialized binary-refinement proof chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_binary_cube_refinement import (
        SCHEMA as REFINEMENT_SCHEMA,
        audit as audit_refinement,
        read_cubes as read_refinement_cubes,
        read_splits,
    )
    from tools.export_materialized_proof_frontier import (
        FRONTIER_SCHEMA,
        export_unknown,
    )
    from tools.prove_materialized_cubes import file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from audit_binary_cube_refinement import (
        SCHEMA as REFINEMENT_SCHEMA,
        audit as audit_refinement,
        read_cubes as read_refinement_cubes,
        read_splits,
    )
    from export_materialized_proof_frontier import FRONTIER_SCHEMA, export_unknown
    from prove_materialized_cubes import file_sha256
    from solve_external_cubes import read_cubes


STATE_SCHEMA = "ramsey55.materialized-proof-chain.v1"
AUDIT_SCHEMA = "ramsey55.materialized-proof-chain-audit.v1"


def load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"expected JSON object: {path}")
    return document


def audit_proof_manifest(
    manifest: Path, checker: Path, jobs: int, audit_tool: Path
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(audit_tool),
            str(manifest),
            "--checker",
            str(checker),
            "--allow-partial",
            "--jobs",
            str(jobs),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"materialized proof audit failed for {manifest}:\n{completed.stdout[-4000:]}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError(f"materialized proof audit emitted no summary: {manifest}")
    return json.loads(lines[-1])


def verify_frontier(
    source_manifest: Path,
    source: dict[str, Any],
    parents: Path,
    lineage_path: Path,
) -> tuple[list[int], list[list[int]]]:
    variables = int(source["formula"]["variables"])
    source_cubes_path = Path(source["cubes"]["path"])
    source_cubes = read_cubes(source_cubes_path, variables)
    indices, unknown = export_unknown(source, source_cubes)
    if read_cubes(parents, variables) != unknown:
        raise ValueError(f"UNKNOWN frontier mismatch: {parents}")
    expected = {
        "schema": FRONTIER_SCHEMA,
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": file_sha256(source_manifest),
        "source_cubes_sha256": source["cubes"]["sha256"],
        "source_cube_count": len(source_cubes),
        "verified_unsat_count": len(source_cubes) - len(unknown),
        "unknown_indices": indices,
        "output": str(parents),
        "output_sha256": file_sha256(parents),
        "output_cube_count": len(unknown),
    }
    if load_json(lineage_path) != expected:
        raise ValueError(f"frontier lineage mismatch: {lineage_path}")
    return indices, unknown


def verify_refinement(
    parents_path: Path,
    children_path: Path,
    results_path: Path,
    manifest_path: Path,
) -> int:
    parents = read_refinement_cubes(parents_path)
    children = read_refinement_cubes(children_path)
    splits = read_splits(results_path, len(parents))
    audit_refinement(parents, children, splits)
    expected = {
        "schema": REFINEMENT_SCHEMA,
        "parents": {
            "path": str(parents_path),
            "sha256": file_sha256(parents_path),
            "count": len(parents),
        },
        "children": {
            "path": str(children_path),
            "sha256": file_sha256(children_path),
            "count": len(children),
        },
        "results": {
            "path": str(results_path),
            "sha256": file_sha256(results_path),
        },
        "splits": list(splits),
        "complete_binary_refinement": True,
    }
    if load_json(manifest_path) != expected:
        raise ValueError(f"binary-refinement manifest mismatch: {manifest_path}")
    return len(parents)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("seed_manifest", type=Path)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--first-round", type=int, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.first_round < 0 or arguments.jobs <= 0:
        parser.error("--first-round must be nonnegative and --jobs must be positive")
    if not arguments.seed_manifest.is_file() or not arguments.checker.is_file():
        parser.error("seed manifest or checker does not exist")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite audit manifest {arguments.manifest}")

    state_path = arguments.workdir / "state.json"
    state_bytes = state_path.read_bytes()
    state = json.loads(state_bytes)
    if not isinstance(state, dict):
        raise ValueError("expected chain state JSON object")
    if state.get("schema") != STATE_SCHEMA:
        raise ValueError("unexpected materialized-proof-chain schema")
    final_round = int(state["round"])
    if final_round < arguments.first_round:
        raise ValueError("chain state precedes --first-round")
    final_manifest = Path(state["current_manifest"])
    root = Path(__file__).resolve().parents[1]
    audit_tool = root / "tools" / "audit_materialized_cube_proofs.py"

    current_manifest = arguments.seed_manifest
    current = load_json(current_manifest)
    seed_formula = current["formula"]
    audited_manifests = 0
    refined_parents = 0
    for round_number in range(arguments.first_round, final_round):
        audit_proof_manifest(
            current_manifest, arguments.checker, arguments.jobs, audit_tool
        )
        audited_manifests += 1
        prefix = arguments.workdir / f"r{round_number:04d}"
        parents = prefix.with_name(prefix.name + "-parents.icnf")
        frontier = prefix.with_name(prefix.name + "-parents.json")
        children = prefix.with_name(prefix.name + "-children.icnf")
        refine_results = prefix.with_name(prefix.name + "-refine.tsv")
        refinement = prefix.with_name(prefix.name + "-refinement.json")
        _, unknown = verify_frontier(current_manifest, current, parents, frontier)
        if not unknown:
            raise ValueError(f"round {round_number} refines an empty frontier")
        if verify_refinement(parents, children, refine_results, refinement) != len(
            unknown
        ):
            raise ValueError(f"round {round_number} refinement count mismatch")
        next_manifest = prefix.with_name(prefix.name + "-proofs") / "manifest.json"
        next_document = load_json(next_manifest)
        if next_document["formula"] != seed_formula:
            raise ValueError(f"formula binding changed at round {round_number}")
        if (
            next_document["cubes"]["path"] != str(children)
            or next_document["cubes"]["sha256"] != file_sha256(children)
            or int(next_document["cubes"]["count"]) != 2 * len(unknown)
        ):
            raise ValueError(f"child proof binding mismatch at round {round_number}")
        refined_parents += len(unknown)
        current_manifest = next_manifest
        current = next_document

    if current_manifest != final_manifest:
        raise ValueError("state current_manifest does not match reconstructed chain")
    final_audit = audit_proof_manifest(
        current_manifest, arguments.checker, arguments.jobs, audit_tool
    )
    audited_manifests += 1
    complete = bool(current["summary"]["complete_unsat"])
    if bool(state["complete"]) != complete:
        raise ValueError("state completion flag disagrees with final manifest")
    result = {
        "schema": AUDIT_SCHEMA,
        "seed_manifest": str(arguments.seed_manifest),
        "seed_manifest_sha256": file_sha256(arguments.seed_manifest),
        "workdir": str(arguments.workdir),
        "state_snapshot": state,
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "first_round": arguments.first_round,
        "final_round": final_round,
        "rounds": final_round - arguments.first_round,
        "audited_manifests": audited_manifests,
        "refined_parents": refined_parents,
        "final_manifest": str(final_manifest),
        "final_manifest_sha256": file_sha256(final_manifest),
        "final_verified": int(final_audit["verified"]),
        "final_unknown": int(final_audit["unknown"]),
        "complete_unsat": complete,
    }
    if arguments.manifest is not None:
        temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(arguments.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
