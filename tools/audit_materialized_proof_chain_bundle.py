#!/usr/bin/env python3
"""Audit one or more adjacent materialized-proof-chain segments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import (
        audit_chain_segments,
        chain_specs,
        cube_binding,
        load_json,
        required_path,
        validate_proof_binding,
    )
    from tools.prove_materialized_cubes import file_sha256
    from tools.solve_external_cubes import read_cnf, read_cubes
else:
    from audit_fixed_pair_proof_bundle import (
        audit_chain_segments,
        chain_specs,
        cube_binding,
        load_json,
        required_path,
        validate_proof_binding,
    )
    from prove_materialized_cubes import file_sha256
    from solve_external_cubes import read_cnf, read_cubes


BUNDLE_SCHEMA = "ramsey55.materialized-proof-chain-bundle.v1"
AUDIT_SCHEMA = "ramsey55.materialized-proof-chain-bundle-audit.v1"


def root_binding(
    case: dict[str, Any], formula: dict[str, Any], first_seed: Path
) -> dict[str, Any]:
    source = required_path(case, "source_cubes")
    lineage_path = required_path(case, "source_lineage")
    root = required_path(case, "root_cubes")
    index = int(case["source_cube_index"])
    parent_index = int(case["fixed_pair_parent_index"])
    variables = int(formula["variables"])
    source_cubes = read_cubes(source, variables)
    roots = read_cubes(root, variables)
    if index < 0 or index >= len(source_cubes):
        raise ValueError("source cube index is out of range")
    if roots != [source_cubes[index]]:
        raise ValueError("root cube is not the selected source cube")
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if not isinstance(lineage, list) or len(lineage) != len(source_cubes):
        raise ValueError("source lineage count mismatch")
    selected_lineage = lineage[index]
    if (
        not isinstance(selected_lineage, dict)
        or int(selected_lineage.get("index", -1)) != index
        or int(selected_lineage.get("parent_index", -1)) != parent_index
    ):
        raise ValueError("source lineage does not select the claimed parent")
    backbones = selected_lineage.get("backbones")
    if (
        not isinstance(backbones, list)
        or len(roots[0])
        != int(selected_lineage.get("parent_literals", -1)) + len(backbones)
        or any(int(literal) not in roots[0] for literal in backbones)
    ):
        raise ValueError("source lineage literal count mismatch")
    seed = load_json(first_seed)
    validate_proof_binding(seed, formula, cube_binding(root, 1), "initial seed")
    return {
        "source_cubes": str(source),
        "source_cubes_sha256": file_sha256(source),
        "source_cube_count": len(source_cubes),
        "source_cube_index": index,
        "source_lineage": str(lineage_path),
        "source_lineage_sha256": file_sha256(lineage_path),
        "fixed_pair_parent_index": parent_index,
        "certified_backbone_count": len(backbones),
        "root_cubes": str(root),
        "root_cubes_sha256": file_sha256(root),
        "root_is_exact_selected_source_cube": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")
    if not arguments.bundle.is_file() or not arguments.checker.is_file():
        parser.error("bundle or checker does not exist")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    bundle = load_json(arguments.bundle)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected materialized-proof-chain bundle schema")
    cases = bundle.get("cases")
    if not isinstance(cases, list) or not cases or any(
        not isinstance(case, dict) for case in cases
    ):
        raise ValueError("bundle cases must be a nonempty object list")
    root = Path(__file__).resolve().parents[1]
    chain_tool = root / "tools" / "audit_materialized_proof_chain.py"
    audited = []
    for index, case in enumerate(cases):
        label = str(case.get("case", f"case-{index}"))
        formula_path = required_path(case, "formula")
        _, _, variables, clauses = read_cnf(formula_path)
        formula = {
            "path": str(formula_path),
            "sha256": file_sha256(formula_path),
            "variables": variables,
            "clauses": clauses,
        }
        specs = chain_specs(case, label)
        for spec in specs:
            spec["seed_manifest"] = spec["seed_manifest"].resolve()
            spec["chain_workdir"] = spec["chain_workdir"].resolve()
            if spec["state"] is not None:
                spec["state"] = spec["state"].resolve()
        selected_root = root_binding(case, formula, specs[0]["seed_manifest"])
        chain = audit_chain_segments(
            specs, label, arguments.checker, arguments.jobs, chain_tool
        )
        expected_complete = bool(case.get("complete_unsat", False))
        if chain["complete_unsat"] != expected_complete:
            raise ValueError(f"{label} completion claim mismatch")
        audited.append(
            {
                "case": label,
                "formula": formula,
                "root": selected_root,
                "chain": chain,
                "complete_unsat": chain["complete_unsat"],
            }
        )
    all_complete = all(case["complete_unsat"] for case in audited)
    if not all_complete and not arguments.allow_partial:
        raise ValueError("bundle is incomplete; pass --allow-partial to audit it")
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "cases": audited,
        "all_cases_complete_unsat": all_complete,
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
