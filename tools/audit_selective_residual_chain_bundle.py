#!/usr/bin/env python3
"""Join an audited selective overlay to a one-root continuation bundle.

An accepted selective audit can remove some UNKNOWN rows from an ordinary
terminal frontier.  This tool verifies an exact, hash-bound projection of the
remaining row and joins it to a separately replayed materialized chain bundle.
It therefore permits future search to continue from only the effective
residual without weakening the already checked cover.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_fixed_pair_proof_bundle import load_json, required_path
    from tools.audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from tools.audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from tools.audit_selective_ancestor_closures import (
        AUDIT_SCHEMA as SELECTIVE_AUDIT_SCHEMA,
        formula_binding,
        validated_unknown_indices,
    )
    from tools.audit_selective_ancestor_closures_extension import (
        AUDIT_SCHEMA as SELECTIVE_EXTENSION_AUDIT_SCHEMA,
    )
    from tools.prove_materialized_cubes import file_sha256
    from tools.select_cube_rows import SCHEMA as SELECTION_SCHEMA
    from tools.solve_external_cubes import read_cubes
else:
    from audit_fixed_pair_proof_bundle import load_json, required_path
    from audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        BUNDLE_SCHEMA as CHAIN_BUNDLE_SCHEMA,
    )
    from audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
        audited_chain_summary,
    )
    from audit_selective_ancestor_closures import (
        AUDIT_SCHEMA as SELECTIVE_AUDIT_SCHEMA,
        formula_binding,
        validated_unknown_indices,
    )
    from audit_selective_ancestor_closures_extension import (
        AUDIT_SCHEMA as SELECTIVE_EXTENSION_AUDIT_SCHEMA,
    )
    from prove_materialized_cubes import file_sha256
    from select_cube_rows import SCHEMA as SELECTION_SCHEMA
    from solve_external_cubes import read_cubes


BUNDLE_SCHEMA = "ramsey55.materialized-selective-residual-chain-bundle.v1"
AUDIT_SCHEMA = "ramsey55.materialized-selective-residual-chain-bundle-audit.v1"


def chain_audit_bundle_hash(audit: dict[str, Any]) -> object:
    schema = audit.get("schema")
    if schema == CHAIN_AUDIT_SCHEMA:
        return audit.get("bundle_sha256")
    if schema == CHAIN_EXTENSION_AUDIT_SCHEMA:
        return audit.get("extended_bundle_sha256")
    raise ValueError("unexpected residual chain-audit schema")


def selective_terminal(case: dict[str, Any], schema: str) -> tuple[Path, int]:
    if schema == SELECTIVE_AUDIT_SCHEMA:
        path = case.get("base_terminal_manifest")
        unknown = case.get("base_terminal_unknown")
    elif schema == SELECTIVE_EXTENSION_AUDIT_SCHEMA:
        path = case.get("extended_terminal_manifest")
        unknown = case.get("extended_terminal_unknown")
    else:
        raise ValueError("unexpected selective-audit schema")
    if not isinstance(path, str) or not path:
        raise ValueError("selective audit has no terminal manifest")
    return Path(path), int(unknown)


def remaining_unknown_indices(
    case: dict[str, Any], terminal: dict[str, Any], cubes: list[list[int]]
) -> list[int]:
    unknown = validated_unknown_indices(terminal, cubes)
    closed = case.get("selectively_closed_unknown_indices")
    if not isinstance(closed, list) or any(
        not isinstance(index, int) for index in closed
    ):
        raise ValueError("selectively closed indices must be an integer list")
    if closed != sorted(set(closed)) or any(index not in unknown for index in closed):
        raise ValueError("selectively closed indices are not terminal UNKNOWN rows")
    remaining = [index for index in unknown if index not in set(closed)]
    if len(remaining) != int(case.get("remaining_unknown", -1)):
        raise ValueError("selective remaining-UNKNOWN count mismatch")
    return remaining


def validate_selection(
    selection: dict[str, Any],
    terminal_cubes_path: Path,
    terminal_cubes: list[list[int]],
    remaining: list[int],
    variables: int,
) -> tuple[Path, list[list[int]]]:
    if selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError("unexpected residual selection schema")
    if (
        selection.get("input_sha256") != file_sha256(terminal_cubes_path)
        or int(selection.get("input_count", -1)) != len(terminal_cubes)
        or selection.get("indices") != remaining
    ):
        raise ValueError("residual selection is not the exact effective frontier")
    output = Path(str(selection.get("output", "")))
    if (
        not output.is_file()
        or selection.get("output_sha256") != file_sha256(output)
        or int(selection.get("output_count", -1)) != len(remaining)
    ):
        raise ValueError("residual selection output binding mismatch")
    cubes = read_cubes(output, variables)
    if cubes != [terminal_cubes[index] for index in remaining]:
        raise ValueError("residual selection output rows mismatch")
    return output, cubes


def validate_selective_bindings(audit: dict[str, Any]) -> None:
    schema = audit.get("schema")
    if schema == SELECTIVE_AUDIT_SCHEMA:
        bundle = required_path(audit, "bundle")
        if audit.get("bundle_sha256") != file_sha256(bundle):
            raise ValueError("selective audit bundle hash mismatch")
        base_bundle = required_path(audit, "base_chain_bundle")
        if audit.get("base_chain_bundle_sha256") != file_sha256(base_bundle):
            raise ValueError("selective audit base-chain hash mismatch")
    elif schema == SELECTIVE_EXTENSION_AUDIT_SCHEMA:
        base = required_path(audit, "base_selective_audit")
        extension = required_path(audit, "chain_extension_audit")
        bundle = required_path(audit, "extended_chain_bundle")
        if (
            audit.get("base_selective_audit_sha256") != file_sha256(base)
            or audit.get("chain_extension_audit_sha256") != file_sha256(extension)
            or audit.get("extended_chain_bundle_sha256") != file_sha256(bundle)
        ):
            raise ValueError("selective extension binding mismatch")
    else:
        raise ValueError("unexpected selective-audit schema")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if not arguments.bundle.is_file() or not arguments.checker.is_file():
        parser.error("bundle or checker does not exist")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    bundle = load_json(arguments.bundle)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected selective residual bundle schema")
    selective_path = required_path(bundle, "selective_audit")
    chain_bundle_path = required_path(bundle, "chain_bundle")
    chain_audit_path = required_path(bundle, "chain_audit")
    selective = load_json(selective_path)
    chain_bundle = load_json(chain_bundle_path)
    chain_audit = load_json(chain_audit_path)
    validate_selective_bindings(selective)
    if chain_bundle.get("schema") != CHAIN_BUNDLE_SCHEMA:
        raise ValueError("unexpected residual chain-bundle schema")
    if chain_audit_bundle_hash(chain_audit) != file_sha256(chain_bundle_path):
        raise ValueError("residual chain audit is not bound to its bundle")
    checker_hash = file_sha256(arguments.checker)
    for label, audit in (("selective", selective), ("chain", chain_audit)):
        checker = audit.get("checker")
        if not isinstance(checker, dict) or checker.get("sha256") != checker_hash:
            raise ValueError(f"{label} audit used a different checker binary")

    selective_cases = selective.get("cases")
    chain_cases = chain_bundle.get("cases")
    audited_chain_cases = chain_audit.get("cases")
    continuations = bundle.get("continuations")
    if not all(
        isinstance(value, list)
        for value in (
            selective_cases,
            chain_cases,
            audited_chain_cases,
            continuations,
        )
    ):
        raise ValueError("selective residual cases must be lists")
    if not selective_cases or not chain_cases or len(chain_cases) != len(
        audited_chain_cases
    ):
        raise ValueError("residual chain case count mismatch")
    if len(continuations) != len(chain_cases):
        raise ValueError("every residual chain case needs one continuation join")

    selective_by_label: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(selective_cases):
        if not isinstance(case, dict):
            raise ValueError(f"selective case {index} is not an object")
        label = str(case.get("case", f"case-{index}"))
        if label in selective_by_label:
            raise ValueError(f"duplicate selective case {label}")
        selective_by_label[label] = case
    chain_by_label: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for index, (case, audited) in enumerate(
        zip(chain_cases, audited_chain_cases, strict=True)
    ):
        if not isinstance(case, dict) or not isinstance(audited, dict):
            raise ValueError(f"residual chain case {index} is not an object")
        label = str(case.get("case", f"case-{index}"))
        if (
            label in chain_by_label
            or label not in selective_by_label
            or audited.get("case") != case.get("case")
        ):
            raise ValueError(f"duplicate, unknown, or reordered chain case {label}")
        chain_by_label[label] = (case, audited)

    continuation_by_label: dict[str, dict[str, Any]] = {}
    for index, continuation in enumerate(continuations):
        if not isinstance(continuation, dict):
            raise ValueError(f"continuation {index} is not an object")
        label = str(continuation.get("case", ""))
        if label in continuation_by_label or label not in chain_by_label:
            raise ValueError(f"duplicate or unknown continuation case {label!r}")
        continuation_by_label[label] = continuation

    output_cases: list[dict[str, Any]] = []
    selective_schema = str(selective.get("schema"))
    chain_schema = str(chain_audit.get("schema"))
    for label, selective_case in selective_by_label.items():
        terminal_path, recorded_unknown = selective_terminal(
            selective_case, selective_schema
        )
        if not terminal_path.is_file():
            raise ValueError(f"selective terminal does not exist for {label}")
        terminal = load_json(terminal_path)
        cubes_binding = terminal.get("cubes")
        formula = terminal.get("formula")
        if not isinstance(cubes_binding, dict) or not isinstance(formula, dict):
            raise ValueError(f"selective terminal binding missing for {label}")
        cubes_path = Path(str(cubes_binding.get("path", "")))
        if (
            not cubes_path.is_file()
            or cubes_binding.get("sha256") != file_sha256(cubes_path)
        ):
            raise ValueError(f"selective terminal cube hash mismatch for {label}")
        cubes = read_cubes(cubes_path, int(formula["variables"]))
        if len(cubes) != int(cubes_binding.get("count", -1)):
            raise ValueError(f"selective terminal cube count mismatch for {label}")
        unknown = validated_unknown_indices(terminal, cubes)
        if len(unknown) != recorded_unknown:
            raise ValueError(f"selective terminal UNKNOWN mismatch for {label}")
        remaining = remaining_unknown_indices(selective_case, terminal, cubes)

        if label not in chain_by_label:
            output_cases.append(
                {
                    "case": label,
                    "selective_terminal_manifest": str(terminal_path),
                    "selective_terminal_manifest_sha256": file_sha256(terminal_path),
                    "projected_residual_count": len(remaining),
                    "continuation_segment_count": 0,
                    "remaining_unknown": len(remaining),
                    "complete_unsat": len(remaining) == 0,
                }
            )
            continue

        chain_case, audited_chain_case = chain_by_label[label]
        continuation = continuation_by_label[label]
        selection_path = required_path(continuation, "selection_manifest")
        selection = load_json(selection_path)
        output_path, residual_cubes = validate_selection(
            selection,
            cubes_path,
            cubes,
            remaining,
            int(formula["variables"]),
        )
        if len(residual_cubes) != 1:
            raise ValueError("residual chain bundle currently requires one root")
        if (
            file_sha256(required_path(chain_case, "source_cubes"))
            != file_sha256(output_path)
            or file_sha256(required_path(chain_case, "root_cubes"))
            != file_sha256(output_path)
            or int(chain_case.get("source_cube_index", -1)) != 0
        ):
            raise ValueError(f"residual chain root mismatch for {label}")
        formula_path = required_path(chain_case, "formula")
        if formula_binding(formula_path) != formula:
            raise ValueError(f"residual chain formula mismatch for {label}")
        chain = audited_chain_summary(audited_chain_case, chain_schema, label)
        segments = chain.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"residual chain has no audited terminal for {label}")
        chain_terminal = segments[-1]
        chain_remaining = int(chain_terminal.get("final_unknown", -1))
        complete = bool(chain.get("complete_unsat", False))
        if complete != (chain_remaining == 0):
            raise ValueError(f"residual chain completion mismatch for {label}")
        output_cases.append(
            {
                "case": label,
                "selective_terminal_manifest": str(terminal_path),
                "selective_terminal_manifest_sha256": file_sha256(terminal_path),
                "selection_manifest": str(selection_path),
                "selection_manifest_sha256": file_sha256(selection_path),
                "projected_residual_count": len(remaining),
                "residual_root_cubes": str(output_path),
                "residual_root_cubes_sha256": file_sha256(output_path),
                "continuation_segment_count": int(chain.get("segment_count", -1)),
                "continuation_terminal": chain_terminal,
                "remaining_unknown": chain_remaining,
                "complete_unsat": complete,
            }
        )

    all_complete = all(case["complete_unsat"] for case in output_cases)
    if not all_complete and not arguments.allow_partial:
        raise ValueError("selective residual chain is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "selective_audit": str(selective_path),
        "selective_audit_sha256": file_sha256(selective_path),
        "chain_bundle": str(chain_bundle_path),
        "chain_bundle_sha256": file_sha256(chain_bundle_path),
        "chain_audit": str(chain_audit_path),
        "chain_audit_sha256": file_sha256(chain_audit_path),
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
