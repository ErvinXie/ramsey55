#!/usr/bin/env python3
"""Compose certified backbone implications with strengthened proof chains."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import load_json, required_path
    from tools.audit_frontier_primary_backbone_proofs import (
        validate_frontier_structure,
    )
    from tools.audit_materialized_proof_chain import audit_proof_manifest
    from tools.prove_materialized_cubes import file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from audit_fixed_pair_proof_bundle import load_json, required_path
    from audit_frontier_primary_backbone_proofs import validate_frontier_structure
    from audit_materialized_proof_chain import audit_proof_manifest
    from prove_materialized_cubes import file_sha256
    from solve_external_cubes import read_cubes


BUNDLE_SCHEMA = "ramsey55.strengthened-parent-chain-bundle.v1"
AUDIT_SCHEMA = "ramsey55.strengthened-parent-chain-bundle-audit.v1"
CHAIN_AUDIT_SCHEMA = "ramsey55.materialized-proof-chain-bundle-audit.v1"


def run_chain_bundle(
    bundle: Path, checker: Path, jobs: int, tool: Path
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(tool),
            str(bundle),
            "--checker",
            str(checker),
            "--jobs",
            str(jobs),
            "--allow-partial",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"chain-bundle audit failed:\n{completed.stdout[-4000:]}")
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError("chain-bundle auditor emitted no JSON summary")
    result = json.loads(lines[-1])
    if result.get("schema") != CHAIN_AUDIT_SCHEMA:
        raise ValueError("unexpected chain-bundle audit schema")
    return result


def validate_strengthening(
    case: dict[str, Any], chain_case: dict[str, Any]
) -> dict[str, Any]:
    parent_index = int(case["parent_index"])
    strengthened_index = int(case["strengthened_index"])
    lineage_path = required_path(case, "backbone_lineage")
    proof_manifest_path = required_path(case, "backbone_proof_manifest")
    strengthened_path = required_path(case, "strengthened_cubes")
    strengthened_lineage_path = required_path(case, "strengthened_lineage")
    primary_max = int(case["primary_max"])

    report = validate_frontier_structure(
        lineage_path, proof_manifest_path, primary_max
    )
    if report.get("case") != case.get("case"):
        raise ValueError("backbone report case mismatch")
    parent_reports = [
        row for row in report["per_parent"] if int(row["parent_index"]) == parent_index
    ]
    if len(parent_reports) != 1:
        raise ValueError("backbone report does not uniquely select the parent")
    backbones = parent_reports[0]["backbones"]
    proof_manifest = load_json(proof_manifest_path)
    if proof_manifest.get("formula") != chain_case.get("formula"):
        raise ValueError("backbone and chain formula bindings differ")
    variables = int(proof_manifest["formula"]["variables"])
    frontier_path = Path(report["frontier"]["path"])
    frontier = read_cubes(frontier_path, variables)
    strengthened = read_cubes(strengthened_path, variables)
    lineage = json.loads(strengthened_lineage_path.read_text(encoding="utf-8"))
    if (
        strengthened_index < 0
        or strengthened_index >= len(strengthened)
        or not isinstance(lineage, list)
        or len(lineage) != len(strengthened)
    ):
        raise ValueError("invalid strengthened cube or lineage index")
    selected = lineage[strengthened_index]
    if (
        not isinstance(selected, dict)
        or int(selected.get("index", -1)) != strengthened_index
        or int(selected.get("parent_index", -1)) != parent_index
        or selected.get("backbones") != backbones
        or strengthened[strengthened_index] != [*frontier[parent_index], *backbones]
    ):
        raise ValueError("strengthened cube is not parent plus certified backbones")

    chain_root = chain_case["root"]
    if (
        int(chain_root["source_cube_index"]) != strengthened_index
        or int(chain_root["fixed_pair_parent_index"]) != parent_index
        or chain_root["source_cubes_sha256"] != file_sha256(strengthened_path)
        or chain_root["source_lineage_sha256"]
        != file_sha256(strengthened_lineage_path)
        or int(chain_root["certified_backbone_count"]) != len(backbones)
    ):
        raise ValueError("chain root does not bind the certified strengthening")
    return {
        "parent_index": parent_index,
        "frontier": report["frontier"],
        "backbone_lineage": str(lineage_path),
        "backbone_lineage_sha256": file_sha256(lineage_path),
        "backbone_proof_manifest": str(proof_manifest_path),
        "backbone_proof_manifest_sha256": file_sha256(proof_manifest_path),
        "backbones": backbones,
        "backbone_count": len(backbones),
        "bad_branches_complete_unsat": True,
        "strengthened_cubes": str(strengthened_path),
        "strengthened_cubes_sha256": file_sha256(strengthened_path),
        "strengthened_index": strengthened_index,
        "strengthened_is_parent_plus_certified_backbones": True,
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
        raise ValueError("unexpected strengthened-parent bundle schema")
    cases = bundle.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("bundle cases must be a nonempty list")
    chain_bundle = required_path(bundle, "chain_bundle")
    root = Path(__file__).resolve().parents[1]
    chain_audit = run_chain_bundle(
        chain_bundle,
        arguments.checker,
        arguments.jobs,
        root / "tools" / "audit_materialized_proof_chain_bundle.py",
    )
    chain_cases = {case["case"]: case for case in chain_audit["cases"]}
    proof_auditor = root / "tools" / "audit_materialized_cube_proofs.py"
    audited = []
    for case in cases:
        label = str(case["case"])
        if label not in chain_cases:
            raise ValueError(f"chain audit is missing case {label}")
        strengthening = validate_strengthening(case, chain_cases[label])
        proof_audit = audit_proof_manifest(
            Path(strengthening["backbone_proof_manifest"]),
            arguments.checker,
            arguments.jobs,
            proof_auditor,
        )
        if not proof_audit.get("complete_unsat"):
            raise ValueError(f"{label} backbone proof audit is incomplete")
        chain = chain_cases[label]["chain"]
        final_segment = chain["segments"][-1]
        parent_unsat = bool(chain["complete_unsat"])
        audited.append(
            {
                "case": label,
                "strengthening": strengthening,
                "backbone_proof_audit": proof_audit,
                "chain": chain,
                "remaining_unknown_cubes": int(final_segment["final_unknown"]),
                "parent_unsat": parent_unsat,
            }
        )
    all_unsat = all(case["parent_unsat"] for case in audited)
    if not all_unsat and not arguments.allow_partial:
        raise ValueError("parent bundle is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "chain_bundle": str(chain_bundle),
        "chain_bundle_sha256": file_sha256(chain_bundle),
        "chain_audit": chain_audit,
        "cases": audited,
        "all_parents_unsat": all_unsat,
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
