#!/usr/bin/env python3
"""Audit a proof-forest/materialized-proof bundle for one order-45 stratum.

The resulting claim is deliberately formula-relative: every exact-edge cube
augmentation in the committed stratum manifest is UNSAT.  The separate Lean
counter bridge turns that statement into mother-formula UNSAT.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import (
        audit_chain_segments,
        chain_specs,
        load_json,
        required_path,
        run_json_tool,
        validate_cube_binding,
        validate_proof_binding,
    )
    from tools.audit_order45_strata_leaf_proofs import (
        FORMULA_SCHEMA,
        read_bound_cubes,
    )
    from tools.prove_materialized_cubes import file_sha256
    from tools.solve_external_cubes import read_cnf
else:
    from audit_fixed_pair_proof_bundle import (
        audit_chain_segments,
        chain_specs,
        load_json,
        required_path,
        run_json_tool,
        validate_cube_binding,
        validate_proof_binding,
    )
    from audit_order45_strata_leaf_proofs import (
        FORMULA_SCHEMA,
        read_bound_cubes,
    )
    from prove_materialized_cubes import file_sha256
    from solve_external_cubes import read_cnf


BUNDLE_SCHEMA = "ramsey55.order45-strata-proof-bundle.v1"
AUDIT_SCHEMA = "ramsey55.order45-strata-proof-bundle-audit.v1"
FOREST_SCHEMA = "ramsey55.proof-forest-snapshot.v1"


def formula_and_forest_bindings(
    formula_manifest: Path,
    formula_path: Path,
    degree: int,
    forest_manifest: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw_manifest = formula_manifest.read_bytes()
    formula_document = json.loads(raw_manifest)
    if formula_document.get("schema") != FORMULA_SCHEMA:
        raise ValueError("unexpected edge-strata formula manifest schema")
    records = [
        record
        for record in formula_document.get("files", [])
        if int(record.get("degree", -1)) == degree
    ]
    if len(records) != 1:
        raise ValueError(f"expected one formula-manifest record for degree {degree}")
    record = records[0]

    _, _, variables, clauses = read_cnf(formula_path)
    if (variables, clauses) != (
        int(record["variables"]),
        int(record["clauses"]),
    ):
        raise ValueError("stratum formula shape mismatch")
    formula_sha256 = file_sha256(formula_path)
    if formula_sha256 != record["sha256"]:
        raise ValueError("stratum formula hash mismatch")
    formula = {
        "path": str(formula_path),
        "sha256": formula_sha256,
        "variables": variables,
        "clauses": clauses,
    }

    forest = load_json(forest_manifest)
    if forest.get("schema") != FOREST_SCHEMA:
        raise ValueError("unexpected proof-forest schema")
    source = forest["source_cubes"]
    source_path = Path(source["path"])
    if file_sha256(source_path) != source["sha256"]:
        raise ValueError("proof-forest source cube hash mismatch")
    metadata, cubes = read_bound_cubes(source_path)
    if len(cubes) != int(source["count"]):
        raise ValueError("proof-forest source cube count mismatch")
    expected_cubes = tuple(tuple(cube["literals"]) for cube in record["cubes"])
    if cubes != expected_cubes:
        raise ValueError("proof-forest roots differ from formula-manifest cubes")
    expected_metadata = {
        "manifest_sha256": file_sha256(formula_manifest),
        "cnf_sha256": formula_sha256,
        "degree": str(degree),
    }
    if metadata != expected_metadata:
        raise ValueError("proof-forest root metadata mismatch")
    record_binding = {
        "degree": degree,
        "formula_manifest": str(formula_manifest),
        "formula_manifest_sha256": file_sha256(formula_manifest),
        "source_cube_count": len(cubes),
        "source_cubes_sha256": source["sha256"],
    }
    return formula, forest, record_binding


def forest_leaf_binding(
    forest_manifest: Path, forest: dict[str, Any], kind: str
) -> dict[str, Any]:
    entry = forest[kind]
    path = forest_manifest.parent / entry["path"]
    binding = {
        "path": str(path),
        "sha256": file_sha256(path),
        "count": int(entry["count"]),
    }
    validate_cube_binding(binding, entry, f"proof forest {kind}")
    return binding


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
        parser.error(f"refusing to overwrite audit manifest {arguments.manifest}")

    bundle = load_json(arguments.bundle)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected order-45 stratum proof-bundle schema")
    degree = int(bundle["degree"])
    formula_manifest = required_path(bundle, "formula_manifest")
    formula_path = required_path(bundle, "formula")
    forest_manifest = required_path(bundle, "forest_manifest")
    closed_section = bundle.get("closed")
    open_section = bundle.get("open")
    if not isinstance(closed_section, dict) or not isinstance(open_section, dict):
        raise ValueError("bundle closed/open sections must be objects")

    formula, forest, stratum = formula_and_forest_bindings(
        formula_manifest, formula_path, degree, forest_manifest
    )
    closed_cubes = forest_leaf_binding(forest_manifest, forest, "closed")
    open_cubes = forest_leaf_binding(forest_manifest, forest, "open")
    closed_segments = chain_specs(closed_section, "closed")
    open_segments = chain_specs(open_section, "open")
    closed_seed = closed_segments[0]["seed_manifest"]
    open_seed = open_segments[0]["seed_manifest"]
    validate_proof_binding(
        load_json(closed_seed), formula, closed_cubes, "closed seed"
    )
    validate_proof_binding(load_json(open_seed), formula, open_cubes, "open seed")

    root = Path(__file__).resolve().parents[1]
    forest_audit = run_json_tool(
        [str(root / "tools" / "audit_proof_forest.py"), str(forest_manifest)],
        "proof-forest audit",
    )
    if forest_audit.get("all_root_refinements_cover") is not True:
        raise ValueError("proof forest does not cover every stratum root")
    chain_tool = root / "tools" / "audit_materialized_proof_chain.py"
    closed_chain = audit_chain_segments(
        closed_segments, "closed", arguments.checker, arguments.jobs, chain_tool
    )
    open_chain = audit_chain_segments(
        open_segments, "open", arguments.checker, arguments.jobs, chain_tool
    )
    exact_edge_cubes_unsat = bool(
        closed_chain["complete_unsat"] and open_chain["complete_unsat"]
    )
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "stratum": stratum,
        "formula": formula,
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "proof_forest": {
            "manifest": str(forest_manifest),
            "manifest_sha256": file_sha256(forest_manifest),
            "audit": forest_audit,
        },
        "closed": {
            "leaf_count": int(forest["closed"]["count"]),
            "chain": closed_chain,
        },
        "open": {
            "leaf_count": int(forest["open"]["count"]),
            "chain": open_chain,
        },
        "exact_edge_cube_augmentations_unsat": exact_edge_cubes_unsat,
        "mother_formula_unsat": False,
        "mother_formula_note": (
            "requires the separately kernel-checked formula-relative cube bridge"
        ),
    }
    if not exact_edge_cubes_unsat and not arguments.allow_partial:
        raise ValueError("order-45 stratum proof bundle remains incomplete")
    if arguments.manifest is not None:
        arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
        temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(arguments.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
