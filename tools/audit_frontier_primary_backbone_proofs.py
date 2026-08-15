#!/usr/bin/env python3
"""Bind checked false-polarity proofs to backbones across a cube frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

if __package__:
    from tools.prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from solve_external_cubes import read_cubes


LINEAGE_SCHEMA = "ramsey55.frontier-primary-backbone-discovery.v1"
REPORT_SCHEMA = "ramsey55.frontier-primary-backbone-proof-audit.v1"


def validate_frontier_structure(
    lineage_path: Path,
    proof_manifest_path: Path,
    primary_max: int,
) -> dict[str, Any]:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    proof_manifest = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    if lineage.get("schema") != LINEAGE_SCHEMA:
        raise ValueError("unexpected frontier-backbone lineage schema")
    if proof_manifest.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    if primary_max <= 0:
        raise ValueError("invalid primary-variable bound")

    variables = int(proof_manifest["formula"]["variables"])
    frontier_path = Path(lineage["frontier_path"])
    frontier = read_cubes(frontier_path, variables)
    if len(frontier) != int(lineage["frontier_parent_count"]):
        raise ValueError("frontier parent count mismatch")
    if any(
        abs(literal) <= primary_max for parent in frontier for literal in parent
    ):
        raise ValueError("a frontier parent already assigns a primary variable")

    cubes_entry = proof_manifest["cubes"]
    bad_branches_path = Path(cubes_entry["path"])
    if file_sha256(bad_branches_path) != cubes_entry["sha256"]:
        raise ValueError("bad-branch cube hash mismatch")
    bad_branches = read_cubes(bad_branches_path, variables)
    backbones = lineage.get("backbones")
    results = proof_manifest.get("results")
    if not isinstance(backbones, list) or not isinstance(results, list):
        raise ValueError("missing backbone or proof result list")
    if not (
        len(backbones)
        == len(bad_branches)
        == len(results)
        == int(cubes_entry["count"])
    ):
        raise ValueError("backbone, cube, and result counts differ")
    if proof_manifest.get("summary") != {
        "complete_unsat": True,
        "sat": 0,
        "unknown": 0,
        "unsat_verified": len(backbones),
    }:
        raise ValueError("proof manifest is not complete UNSAT")

    seen: set[tuple[int, int]] = set()
    per_parent: list[list[int]] = [[] for _ in frontier]
    for index, (entry, branch, result) in enumerate(
        zip(backbones, bad_branches, results, strict=True)
    ):
        parent_index = int(entry["parent_index"])
        variable = int(entry["variable"])
        bad_literal = int(entry["bad_literal"])
        survivor_literal = int(entry["survivor_literal"])
        key = (parent_index, variable)
        if (
            not 0 <= parent_index < len(frontier)
            or key in seen
            or not 1 <= variable <= primary_max
            or abs(bad_literal) != variable
            or survivor_literal != -bad_literal
        ):
            raise ValueError(f"invalid frontier-backbone entry {index}")
        seen.add(key)
        if branch != [*frontier[parent_index], bad_literal]:
            raise ValueError(f"bad branch {index} does not extend its parent")
        if (
            int(result.get("index", -1)) != index
            or int(result.get("status", -1)) != 20
            or result.get("cube") != branch
            or result.get("cube_sha256") != cube_sha256(branch)
        ):
            raise ValueError(f"proof result {index} does not bind the bad branch")
        per_parent[parent_index].append(survivor_literal)

    parent_reports = [
        {"parent_index": index, "backbones": forced}
        for index, forced in enumerate(per_parent)
        if forced
    ]
    return {
        "schema": REPORT_SCHEMA,
        "case": lineage.get("case"),
        "frontier": {
            "path": str(frontier_path),
            "sha256": file_sha256(frontier_path),
            "parents": len(frontier),
        },
        "primary_max": primary_max,
        "lineage_sha256": file_sha256(lineage_path),
        "proof_manifest_sha256": file_sha256(proof_manifest_path),
        "backbone_facts": len(backbones),
        "parents_with_backbones": len(parent_reports),
        "per_parent": parent_reports,
        "bad_branches_complete_unsat": True,
        "frontier_unsat": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lineage", type=Path)
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("--primary-max", type=int, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")
    report = validate_frontier_structure(
        arguments.lineage, arguments.proof_manifest, arguments.primary_max
    )

    auditor = Path(__file__).with_name("audit_materialized_cube_proofs.py")
    checked = subprocess.run(
        [
            sys.executable,
            str(auditor),
            str(arguments.proof_manifest),
            "--checker",
            str(arguments.checker),
            "--jobs",
            str(arguments.jobs),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if checked.returncode:
        raise RuntimeError(f"materialized-proof audit failed:\n{checked.stdout}")
    lines = [line for line in checked.stdout.splitlines() if line.startswith("{")]
    if len(lines) != 1:
        raise RuntimeError("materialized-proof auditor emitted no unique JSON result")
    proof_audit = json.loads(lines[0])
    if not proof_audit.get("complete_unsat"):
        raise RuntimeError("materialized-proof audit is incomplete")
    report["proof_audit"] = proof_audit
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
