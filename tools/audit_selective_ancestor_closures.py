#!/usr/bin/env python3
"""Overlay complete ancestor subchains on an audited chain-bundle frontier.

An audited materialized chain proves every terminal cube except the rows still
marked UNKNOWN.  A separate complete chain rooted at an ancestor of one of
those rows proves that entire descendant branch UNSAT.  This tool binds both
layers, replays every selective chain, and removes only terminal UNKNOWN rows
whose ordered cube literally extends a replayed complete ancestor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import (
        absolute_preserving_symlinks,
        audit_chain_segments,
        chain_specs,
        cube_binding,
        load_json,
        required_path,
        validate_proof_binding,
    )
    from tools.audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from tools.audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from tools.prove_materialized_cubes import file_sha256
    from tools.solve_external_cubes import read_cnf, read_cubes
else:
    from audit_fixed_pair_proof_bundle import (
        absolute_preserving_symlinks,
        audit_chain_segments,
        chain_specs,
        cube_binding,
        load_json,
        required_path,
        validate_proof_binding,
    )
    from audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from prove_materialized_cubes import file_sha256
    from solve_external_cubes import read_cnf, read_cubes


BUNDLE_SCHEMA = "ramsey55.materialized-selective-ancestor-closures.v1"
AUDIT_SCHEMA = "ramsey55.materialized-selective-ancestor-closures-audit.v1"


def validated_unknown_indices(
    terminal: dict[str, Any], cubes: list[list[int]]
) -> list[int]:
    """Validate terminal result rows and return their UNKNOWN indices."""
    results = terminal.get("results")
    if not isinstance(results, list) or len(results) != len(cubes):
        raise ValueError("terminal result/cube count mismatch")
    unknown: list[int] = []
    for index, (row, cube) in enumerate(zip(results, cubes, strict=True)):
        if not isinstance(row, dict):
            raise ValueError(f"terminal result {index} is not an object")
        status = int(row.get("status", -1))
        if status not in (0, 20):
            raise ValueError(f"terminal result {index} has non-proof status {status}")
        if int(row.get("index", -1)) != index or row.get("cube") != cube:
            raise ValueError(f"terminal result/cube mismatch at row {index}")
        if status == 0:
            unknown.append(index)
    return unknown


def descendant_unknown_indices(
    terminal: dict[str, Any], cubes: list[list[int]], ancestor: list[int]
) -> list[int]:
    """Return UNKNOWN rows extending ``ancestor`` after strict row validation."""

    if not ancestor:
        raise ValueError("selective ancestor cube is empty")
    return [
        index
        for index in validated_unknown_indices(terminal, cubes)
        if cubes[index][: len(ancestor)] == ancestor
    ]


def base_audit_bundle_hash(audit: dict[str, Any]) -> object:
    schema = audit.get("schema")
    if schema == CHAIN_AUDIT_SCHEMA:
        return audit.get("bundle_sha256")
    if schema == CHAIN_EXTENSION_AUDIT_SCHEMA:
        return audit.get("extended_bundle_sha256")
    raise ValueError("unexpected base chain-audit schema")


def formula_binding(path: Path) -> dict[str, Any]:
    _, _, variables, clauses = read_cnf(path)
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "variables": variables,
        "clauses": clauses,
    }


def normalize_specs(section: dict[str, Any], label: str) -> list[dict[str, Any]]:
    specs = chain_specs(section, label)
    for spec in specs:
        spec["seed_manifest"] = absolute_preserving_symlinks(
            spec["seed_manifest"]
        )
        spec["chain_workdir"] = absolute_preserving_symlinks(
            spec["chain_workdir"]
        )
        if spec["state"] is not None:
            spec["state"] = absolute_preserving_symlinks(spec["state"])
    return specs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--segment-jobs", type=int, default=1)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.jobs <= 0 or arguments.segment_jobs <= 0:
        parser.error("--jobs and --segment-jobs must be positive")
    if not arguments.bundle.is_file() or not arguments.checker.is_file():
        parser.error("bundle or checker does not exist")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    bundle = load_json(arguments.bundle)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected selective-closure bundle schema")
    base_bundle_path = required_path(bundle, "base_chain_bundle")
    base_audit_path = required_path(bundle, "base_chain_audit")
    base_bundle = load_json(base_bundle_path)
    base_audit = load_json(base_audit_path)
    if base_bundle.get("schema") != CHAIN_BUNDLE_SCHEMA:
        raise ValueError("unexpected base chain-bundle schema")
    if base_audit_bundle_hash(base_audit) != file_sha256(base_bundle_path):
        raise ValueError("base audit is not bound to the supplied chain bundle")
    checker_binding = base_audit.get("checker")
    if not isinstance(checker_binding, dict) or checker_binding.get(
        "sha256"
    ) != file_sha256(arguments.checker):
        raise ValueError("base audit used a different checker binary")

    base_cases = base_bundle.get("cases")
    audited_cases = base_audit.get("cases")
    if not isinstance(base_cases, list) or not isinstance(audited_cases, list):
        raise ValueError("base bundle and audit cases must be lists")
    if not base_cases or len(base_cases) != len(audited_cases):
        raise ValueError("base bundle/audit case count mismatch")
    cases_by_label: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for index, (case, audited) in enumerate(
        zip(base_cases, audited_cases, strict=True)
    ):
        if not isinstance(case, dict) or not isinstance(audited, dict):
            raise ValueError(f"base case {index} is not an object")
        label = str(case.get("case", f"case-{index}"))
        if label in cases_by_label or audited.get("case") != case.get("case"):
            raise ValueError(f"duplicate or reordered base case {label}")
        cases_by_label[label] = (case, audited)

    closures = bundle.get("closures")
    if not isinstance(closures, list) or not closures or any(
        not isinstance(item, dict) for item in closures
    ):
        raise ValueError("selective closures must be a nonempty object list")
    closure_specs: dict[str, list[dict[str, Any]]] = {}
    for closure in closures:
        label = str(closure.get("case", ""))
        if label not in cases_by_label:
            raise ValueError(f"selective closure names unknown case {label!r}")
        closure_specs.setdefault(label, []).append(closure)

    root = Path(__file__).resolve().parents[1]
    chain_tool = root / "tools" / "audit_materialized_proof_chain.py"
    output_cases: list[dict[str, Any]] = []
    for label, (case, audited_case) in cases_by_label.items():
        chain = audited_chain_summary(
            audited_case, str(base_audit["schema"]), label
        )
        segments = chain.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"base audit has no terminal segment for {label}")
        terminal_record = segments[-1]
        terminal_path = Path(terminal_record["final_manifest"])
        if file_sha256(terminal_path) != terminal_record.get(
            "final_manifest_sha256"
        ):
            raise ValueError(f"base terminal manifest hash mismatch for {label}")
        terminal = load_json(terminal_path)
        formula_path = required_path(case, "formula")
        formula = formula_binding(formula_path)
        if terminal.get("formula") != formula:
            raise ValueError(f"base terminal formula mismatch for {label}")
        terminal_cubes_path = Path(terminal["cubes"]["path"])
        if file_sha256(terminal_cubes_path) != terminal["cubes"]["sha256"]:
            raise ValueError(f"base terminal cube hash mismatch for {label}")
        terminal_cubes = read_cubes(terminal_cubes_path, int(formula["variables"]))
        if len(terminal_cubes) != int(terminal["cubes"]["count"]):
            raise ValueError(f"base terminal cube count mismatch for {label}")
        unknown_indices = validated_unknown_indices(terminal, terminal_cubes)
        if len(unknown_indices) != int(terminal["summary"]["unknown"]) or len(
            unknown_indices
        ) != int(terminal_record["final_unknown"]):
            raise ValueError(f"base terminal UNKNOWN count mismatch for {label}")

        covered: set[int] = set()
        audited_closures: list[dict[str, Any]] = []
        for closure_index, closure in enumerate(closure_specs.get(label, [])):
            ancestor_path = required_path(closure, "ancestor_cubes")
            ancestors = read_cubes(ancestor_path, int(formula["variables"]))
            if len(ancestors) != 1:
                raise ValueError(
                    f"{label} selective closure {closure_index} must bind one ancestor"
                )
            specs = normalize_specs(
                closure, f"{label} selective closure {closure_index}"
            )
            seed = load_json(specs[0]["seed_manifest"])
            validate_proof_binding(
                seed,
                formula,
                cube_binding(ancestor_path, 1),
                f"{label} selective ancestor seed",
            )
            closure_audit = audit_chain_segments(
                specs,
                f"{label} selective closure {closure_index}",
                arguments.checker,
                arguments.jobs,
                chain_tool,
                arguments.segment_jobs,
            )
            if not closure_audit["complete_unsat"]:
                raise ValueError(f"{label} selective ancestor chain is incomplete")
            descendants = descendant_unknown_indices(
                terminal, terminal_cubes, ancestors[0]
            )
            if not descendants:
                raise ValueError(
                    f"{label} selective ancestor covers no terminal UNKNOWN row"
                )
            overlap = covered.intersection(descendants)
            if overlap:
                raise ValueError(
                    f"{label} selective closures overlap terminal rows {sorted(overlap)}"
                )
            covered.update(descendants)
            audited_closures.append(
                {
                    "ancestor_cubes": str(ancestor_path),
                    "ancestor_cubes_sha256": file_sha256(ancestor_path),
                    "ancestor_literal_count": len(ancestors[0]),
                    "covered_terminal_unknown_indices": descendants,
                    "chain": closure_audit,
                    "complete_unsat": True,
                }
            )

        remaining = len(unknown_indices) - len(covered)
        output_cases.append(
            {
                "case": label,
                "base_terminal_manifest": str(terminal_path),
                "base_terminal_manifest_sha256": file_sha256(terminal_path),
                "base_terminal_unknown": len(unknown_indices),
                "selectively_closed_unknown_indices": sorted(covered),
                "remaining_unknown": remaining,
                "selective_closures": audited_closures,
                "complete_unsat": remaining == 0,
            }
        )

    all_complete = all(case["complete_unsat"] for case in output_cases)
    if not all_complete and not arguments.allow_partial:
        raise ValueError("selective closure overlay is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "base_chain_bundle": str(base_bundle_path),
        "base_chain_bundle_sha256": file_sha256(base_bundle_path),
        "base_chain_audit": str(base_audit_path),
        "base_chain_audit_sha256": file_sha256(base_audit_path),
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "proof_jobs": arguments.jobs,
        "segment_jobs": arguments.segment_jobs,
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
