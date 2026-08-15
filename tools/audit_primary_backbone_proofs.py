#!/usr/bin/env python3
"""Bind checked false-polarity proofs to primary-variable backbones."""

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


LINEAGE_SCHEMA = "ramsey55.primary-backbone-discovery.v1"
REPORT_SCHEMA = "ramsey55.primary-backbone-proof-audit.v1"


def validate_structure(
    frontier_path: Path,
    frontier_cube_index: int,
    primary_max: int,
    lineage_path: Path,
    proof_manifest_path: Path,
) -> dict[str, Any]:
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    proof_manifest = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    if lineage.get("schema") != LINEAGE_SCHEMA:
        raise ValueError("unexpected backbone-lineage schema")
    if proof_manifest.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    if frontier_cube_index < 0 or primary_max <= 0:
        raise ValueError("invalid frontier index or primary-variable bound")
    if int(lineage.get("frontier_cube_index", -1)) != frontier_cube_index:
        raise ValueError("lineage frontier index mismatch")

    variables = int(proof_manifest["formula"]["variables"])
    frontier = read_cubes(frontier_path, variables)
    if frontier_cube_index >= len(frontier):
        raise ValueError("frontier cube index is out of range")
    parent = frontier[frontier_cube_index]
    if any(abs(literal) <= primary_max for literal in parent):
        raise ValueError("frontier parent already assigns a primary variable")

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

    seen: set[int] = set()
    forced: list[int] = []
    for index, (entry, branch, result) in enumerate(
        zip(backbones, bad_branches, results, strict=True)
    ):
        variable = int(entry["variable"])
        bad_literal = int(entry["bad_literal"])
        survivor_literal = int(entry["survivor_literal"])
        if (
            variable in seen
            or not 1 <= variable <= primary_max
            or abs(bad_literal) != variable
            or survivor_literal != -bad_literal
        ):
            raise ValueError(f"invalid backbone entry {index}")
        seen.add(variable)
        if branch != [*parent, bad_literal]:
            raise ValueError(f"bad branch {index} does not extend the parent")
        if (
            int(result.get("index", -1)) != index
            or int(result.get("status", -1)) != 20
            or result.get("cube") != branch
            or result.get("cube_sha256") != cube_sha256(branch)
        ):
            raise ValueError(f"proof result {index} does not bind the bad branch")
        forced.append(survivor_literal)

    return {
        "schema": REPORT_SCHEMA,
        "case": lineage.get("case"),
        "frontier": {
            "path": str(frontier_path),
            "sha256": file_sha256(frontier_path),
            "cube_index": frontier_cube_index,
            "cube_sha256": cube_sha256(parent),
            "cube_literals": len(parent),
        },
        "primary_max": primary_max,
        "lineage_sha256": file_sha256(lineage_path),
        "proof_manifest_sha256": file_sha256(proof_manifest_path),
        "backbones": forced,
        "backbone_count": len(forced),
        "bad_branches_complete_unsat": True,
        "parent_cube_unsat": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frontier", type=Path)
    parser.add_argument("frontier_cube_index", type=int)
    parser.add_argument("lineage", type=Path)
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("--primary-max", type=int, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")

    report = validate_structure(
        arguments.frontier,
        arguments.frontier_cube_index,
        arguments.primary_max,
        arguments.lineage,
        arguments.proof_manifest,
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
