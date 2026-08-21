#!/usr/bin/env python3
"""Propagate an audited selective closure through a checked chain extension.

The expensive ancestor proof is replayed by ``audit_selective_ancestor_closures``
once.  This tool binds that immutable audit to a separately replayed ordinary
chain-bundle extension, reconstructs every certified ancestor, and checks which
UNKNOWN rows in the extended terminal frontier still descend from it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import load_json, required_path
    from tools.audit_materialized_proof_chain_bundle import (
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from tools.audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from tools.audit_selective_ancestor_closures import (
        AUDIT_SCHEMA as SELECTIVE_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as SELECTIVE_BUNDLE_SCHEMA,
        descendant_unknown_indices,
        formula_binding,
        validated_unknown_indices,
        verified_ancestor,
    )
    from tools.prove_materialized_cubes import cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cubes
else:
    from audit_fixed_pair_proof_bundle import load_json, required_path
    from audit_materialized_proof_chain_bundle import (
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from audit_selective_ancestor_closures import (
        AUDIT_SCHEMA as SELECTIVE_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as SELECTIVE_BUNDLE_SCHEMA,
        descendant_unknown_indices,
        formula_binding,
        validated_unknown_indices,
        verified_ancestor,
    )
    from prove_materialized_cubes import cube_sha256, file_sha256
    from solve_external_cubes import read_cubes


AUDIT_SCHEMA = "ramsey55.materialized-selective-ancestor-closures-extension-audit.v1"


def certificate_ancestor(
    closure: dict[str, Any], formula: dict[str, Any]
) -> list[int]:
    """Reconstruct and validate the exact ancestor bound by a base audit row."""

    if closure.get("complete_unsat") is not True:
        raise ValueError("base selective closure is not complete UNSAT")
    certificate = closure.get("certificate")
    if not isinstance(certificate, dict):
        raise ValueError("base selective closure has no certificate")
    kind = certificate.get("kind")
    if kind == "complete materialized proof chain":
        path = Path(str(certificate.get("ancestor_cubes", "")))
        if not path.is_file() or certificate.get(
            "ancestor_cubes_sha256"
        ) != file_sha256(path):
            raise ValueError("selective chain ancestor cube hash mismatch")
        ancestors = read_cubes(path, int(formula["variables"]))
        chain = certificate.get("chain")
        if (
            len(ancestors) != 1
            or not isinstance(chain, dict)
            or chain.get("complete_unsat") is not True
        ):
            raise ValueError("selective chain certificate is incomplete")
        ancestor = ancestors[0]
    elif kind == "direct verified materialized proof row":
        path = Path(str(certificate.get("proof_manifest", "")))
        if not path.is_file() or certificate.get(
            "proof_manifest_sha256"
        ) != file_sha256(path):
            raise ValueError("direct selective proof manifest hash mismatch")
        proof = load_json(path)
        if proof.get("formula") != formula:
            raise ValueError("direct selective proof formula mismatch")
        cubes_binding = proof.get("cubes")
        if not isinstance(cubes_binding, dict):
            raise ValueError("direct selective proof has no cube binding")
        cubes_path = Path(str(cubes_binding.get("path", "")))
        if not cubes_path.is_file() or cubes_binding.get("sha256") != file_sha256(
            cubes_path
        ):
            raise ValueError("direct selective proof cube hash mismatch")
        cubes = read_cubes(cubes_path, int(formula["variables"]))
        if len(cubes) != int(cubes_binding.get("count", -1)):
            raise ValueError("direct selective proof cube count mismatch")
        ancestor = verified_ancestor(
            proof, cubes, int(certificate.get("proof_result_index", -1))
        )
    else:
        raise ValueError("unknown selective certificate kind")

    if len(ancestor) != int(closure.get("ancestor_literal_count", -1)):
        raise ValueError("selective ancestor literal count mismatch")
    if cube_sha256(ancestor) != closure.get("ancestor_cube_sha256"):
        raise ValueError("selective ancestor cube hash mismatch")
    return ancestor


def propagate_closures(
    closures: list[dict[str, Any]],
    terminal: dict[str, Any],
    cubes: list[list[int]],
    formula: dict[str, Any],
) -> tuple[list[dict[str, Any]], set[int]]:
    """Map already audited ancestors onto an extended terminal frontier."""

    covered: set[int] = set()
    propagated: list[dict[str, Any]] = []
    for index, closure in enumerate(closures):
        if not isinstance(closure, dict):
            raise ValueError(f"base selective closure {index} is not an object")
        ancestor = certificate_ancestor(closure, formula)
        descendants = descendant_unknown_indices(terminal, cubes, ancestor)
        overlap = covered.intersection(descendants)
        if overlap:
            raise ValueError(
                f"propagated selective closures overlap terminal rows {sorted(overlap)}"
            )
        covered.update(descendants)
        propagated.append(
            {
                "base_selective_closure_index": index,
                "ancestor_literal_count": len(ancestor),
                "ancestor_cube_sha256": cube_sha256(ancestor),
                "covered_extended_terminal_unknown_indices": descendants,
                "complete_unsat": True,
            }
        )
    return propagated, covered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_selective_audit", type=Path)
    parser.add_argument("chain_extension_audit", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    for path in (
        arguments.base_selective_audit,
        arguments.chain_extension_audit,
        arguments.checker,
    ):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    selective = load_json(arguments.base_selective_audit)
    extension = load_json(arguments.chain_extension_audit)
    if selective.get("schema") != SELECTIVE_AUDIT_SCHEMA:
        raise ValueError("unexpected base selective-audit schema")
    if extension.get("schema") != CHAIN_EXTENSION_AUDIT_SCHEMA:
        raise ValueError("unexpected chain-extension-audit schema")

    selective_bundle_path = required_path(selective, "bundle")
    selective_bundle = load_json(selective_bundle_path)
    if (
        selective_bundle.get("schema") != SELECTIVE_BUNDLE_SCHEMA
        or selective.get("bundle_sha256") != file_sha256(selective_bundle_path)
    ):
        raise ValueError("base selective audit is not bound to its bundle")
    base_chain_bundle_path = required_path(selective, "base_chain_bundle")
    base_chain_audit_path = required_path(selective, "base_chain_audit")
    if (
        selective.get("base_chain_bundle_sha256")
        != file_sha256(base_chain_bundle_path)
        or selective.get("base_chain_audit_sha256")
        != file_sha256(base_chain_audit_path)
    ):
        raise ValueError("base selective chain binding mismatch")
    if extension.get("base_bundle_sha256") != file_sha256(base_chain_bundle_path):
        raise ValueError("chain extension does not continue the selective base")
    if extension.get("base_audit_sha256") != file_sha256(base_chain_audit_path):
        raise ValueError("chain extension and selective audit use different base audits")

    checker_hash = file_sha256(arguments.checker)
    for label, document in (("selective", selective), ("extension", extension)):
        checker = document.get("checker")
        if not isinstance(checker, dict) or checker.get("sha256") != checker_hash:
            raise ValueError(f"{label} audit used a different checker binary")

    extended_bundle_path = required_path(extension, "extended_bundle")
    extended_bundle = load_json(extended_bundle_path)
    if (
        extended_bundle.get("schema") != CHAIN_BUNDLE_SCHEMA
        or extension.get("extended_bundle_sha256")
        != file_sha256(extended_bundle_path)
    ):
        raise ValueError("chain extension is not bound to its extended bundle")
    recursive_base_audit_path = required_path(extension, "base_audit")
    if extension.get("base_audit_sha256") != file_sha256(recursive_base_audit_path):
        raise ValueError("chain extension base-audit hash mismatch")
    recursive_base_audit = load_json(recursive_base_audit_path)

    selective_cases = selective.get("cases")
    extension_cases = extension.get("cases")
    bundle_cases = extended_bundle.get("cases")
    base_audited_cases = recursive_base_audit.get("cases")
    if not all(
        isinstance(value, list)
        for value in (
            selective_cases,
            extension_cases,
            bundle_cases,
            base_audited_cases,
        )
    ):
        raise ValueError("audit and bundle cases must be lists")
    if not selective_cases or not (
        len(selective_cases)
        == len(extension_cases)
        == len(bundle_cases)
        == len(base_audited_cases)
    ):
        raise ValueError("selective/extension case count mismatch")

    output_cases: list[dict[str, Any]] = []
    labels: set[str] = set()
    for index, (base_case, extended_case, bundle_case, base_audited_case) in enumerate(
        zip(
            selective_cases,
            extension_cases,
            bundle_cases,
            base_audited_cases,
            strict=True,
        )
    ):
        if not all(
            isinstance(value, dict)
            for value in (base_case, extended_case, bundle_case, base_audited_case)
        ):
            raise ValueError(f"case {index} is not an object")
        label = str(bundle_case.get("case", f"case-{index}"))
        if label in labels or any(
            case.get("case") != bundle_case.get("case")
            for case in (base_case, extended_case, base_audited_case)
        ):
            raise ValueError(f"duplicate or reordered case {label}")
        labels.add(label)

        base_chain = audited_chain_summary(
            base_audited_case, str(recursive_base_audit.get("schema")), label
        )
        base_segments = base_chain.get("segments")
        if not isinstance(base_segments, list) or not base_segments:
            raise ValueError(f"base audit has no terminal segment for {label}")
        base_terminal = base_segments[-1]
        if (
            base_case.get("base_terminal_manifest_sha256")
            != base_terminal.get("final_manifest_sha256")
            or int(base_case.get("base_terminal_unknown", -1))
            != int(base_terminal.get("final_unknown", -2))
        ):
            raise ValueError(f"selective/base extension boundary mismatch for {label}")

        terminal_record = extended_case.get("terminal")
        if not isinstance(terminal_record, dict):
            raise ValueError(f"chain extension has no terminal for {label}")
        terminal_path = Path(str(terminal_record.get("final_manifest", "")))
        if not terminal_path.is_file() or terminal_record.get(
            "final_manifest_sha256"
        ) != file_sha256(terminal_path):
            raise ValueError(f"extended terminal manifest hash mismatch for {label}")
        terminal = load_json(terminal_path)
        formula_path = required_path(bundle_case, "formula")
        formula = formula_binding(formula_path)
        if terminal.get("formula") != formula:
            raise ValueError(f"extended terminal formula mismatch for {label}")
        cubes_binding = terminal.get("cubes")
        if not isinstance(cubes_binding, dict):
            raise ValueError(f"extended terminal has no cube binding for {label}")
        cubes_path = Path(str(cubes_binding.get("path", "")))
        if not cubes_path.is_file() or cubes_binding.get("sha256") != file_sha256(
            cubes_path
        ):
            raise ValueError(f"extended terminal cube hash mismatch for {label}")
        cubes = read_cubes(cubes_path, int(formula["variables"]))
        if len(cubes) != int(cubes_binding.get("count", -1)):
            raise ValueError(f"extended terminal cube count mismatch for {label}")
        unknown = validated_unknown_indices(terminal, cubes)
        if (
            len(unknown) != int(terminal["summary"]["unknown"])
            or len(unknown) != int(terminal_record.get("final_unknown", -1))
        ):
            raise ValueError(f"extended terminal UNKNOWN count mismatch for {label}")

        closures = base_case.get("selective_closures")
        if not isinstance(closures, list):
            raise ValueError(f"base selective closures are not a list for {label}")
        propagated, covered = propagate_closures(closures, terminal, cubes, formula)
        remaining = len(unknown) - len(covered)
        output_cases.append(
            {
                "case": label,
                "base_terminal_manifest": base_case.get("base_terminal_manifest"),
                "base_terminal_manifest_sha256": base_case.get(
                    "base_terminal_manifest_sha256"
                ),
                "extended_terminal_manifest": str(terminal_path),
                "extended_terminal_manifest_sha256": file_sha256(terminal_path),
                "extended_terminal_unknown": len(unknown),
                "selectively_closed_unknown_indices": sorted(covered),
                "remaining_unknown": remaining,
                "selective_closures": propagated,
                "complete_unsat": remaining == 0,
            }
        )

    all_complete = all(case["complete_unsat"] for case in output_cases)
    if not all_complete and not arguments.allow_partial:
        raise ValueError("propagated selective overlay is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "base_selective_audit": str(arguments.base_selective_audit),
        "base_selective_audit_sha256": file_sha256(arguments.base_selective_audit),
        "selective_bundle": str(selective_bundle_path),
        "selective_bundle_sha256": file_sha256(selective_bundle_path),
        "chain_extension_audit": str(arguments.chain_extension_audit),
        "chain_extension_audit_sha256": file_sha256(arguments.chain_extension_audit),
        "base_chain_bundle": str(base_chain_bundle_path),
        "base_chain_bundle_sha256": file_sha256(base_chain_bundle_path),
        "extended_chain_bundle": str(extended_bundle_path),
        "extended_chain_bundle_sha256": file_sha256(extended_bundle_path),
        "checker": {"path": str(arguments.checker), "sha256": checker_hash},
        "cases": output_cases,
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
