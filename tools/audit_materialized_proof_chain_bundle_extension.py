#!/usr/bin/env python3
"""Audit only the suffix appended to an already audited chain bundle.

The output is intentionally not a replacement for the base audit.  It binds
that immutable audit by SHA-256, verifies that the new bundle is an exact
prefix extension, replays every newly appended proof-chain segment, and
checks the old-terminal/new-seed boundary.  A verifier can therefore replay
the base audit once and use small extension audits for later checkpoints.
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
        load_json,
        validate_chain_adjacency,
        validate_rescued_refinement_adjacency,
    )
    from tools.audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as BASE_AUDIT_SCHEMA,
        BUNDLE_SCHEMA,
    )
    from tools.prove_materialized_cubes import file_sha256
else:
    from audit_fixed_pair_proof_bundle import (
        absolute_preserving_symlinks,
        audit_chain_segments,
        chain_specs,
        load_json,
        validate_chain_adjacency,
        validate_rescued_refinement_adjacency,
    )
    from audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as BASE_AUDIT_SCHEMA,
        BUNDLE_SCHEMA,
    )
    from prove_materialized_cubes import file_sha256


AUDIT_SCHEMA = "ramsey55.materialized-proof-chain-bundle-extension-audit.v1"


def without_keys(document: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in keys}


def audited_chain_summary(
    audited_case: dict[str, Any], audit_schema: str, label: str
) -> dict[str, Any]:
    if audit_schema == BASE_AUDIT_SCHEMA:
        chain = audited_case.get("chain")
    elif audit_schema == AUDIT_SCHEMA:
        extension = audited_case.get("extension")
        terminal = audited_case.get("terminal")
        if not isinstance(extension, dict) or not isinstance(terminal, dict):
            raise ValueError(f"base extension audit has no {label} chain")
        chain = {
            "segment_count": audited_case.get("total_segment_count"),
            "segments": [terminal],
            "complete_unsat": audited_case.get("complete_unsat"),
        }
    else:
        raise ValueError("unexpected base chain-audit schema")
    if not isinstance(chain, dict):
        raise ValueError(f"base audit has no {label} chain")
    return chain


def validate_extension_layout(
    base_bundle: dict[str, Any],
    base_audit: dict[str, Any],
    extended_bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return per-case suffixes after rejecting any mutation of the prefix."""

    if base_bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected base chain-bundle schema")
    if extended_bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected extended chain-bundle schema")
    audit_schema = str(base_audit.get("schema"))
    if audit_schema not in (BASE_AUDIT_SCHEMA, AUDIT_SCHEMA):
        raise ValueError("unexpected base chain-audit schema")
    if without_keys(base_bundle, "claim", "cases") != without_keys(
        extended_bundle, "claim", "cases"
    ):
        raise ValueError("extended bundle changed non-case base metadata")

    base_cases = base_bundle.get("cases")
    extended_cases = extended_bundle.get("cases")
    audited_cases = base_audit.get("cases")
    if not all(
        isinstance(value, list) for value in (base_cases, extended_cases, audited_cases)
    ):
        raise ValueError("bundle and audit cases must be lists")
    if (
        not base_cases
        or len(base_cases) != len(extended_cases)
        or len(base_cases) != len(audited_cases)
    ):
        raise ValueError("base, extended, and audited case counts differ")

    extensions: list[dict[str, Any]] = []
    labels: set[str] = set()
    base_completion: list[bool] = []
    for index, (base_case, extended_case, audited_case) in enumerate(
        zip(base_cases, extended_cases, audited_cases)
    ):
        if not all(
            isinstance(value, dict)
            for value in (base_case, extended_case, audited_case)
        ):
            raise ValueError(f"case {index} is not an object")
        label = str(base_case.get("case", f"case-{index}"))
        if label in labels:
            raise ValueError(f"duplicate case label: {label}")
        labels.add(label)
        if extended_case.get("case") != base_case.get("case") or audited_case.get(
            "case"
        ) != base_case.get("case"):
            raise ValueError(f"case order or label changed for {label}")
        if without_keys(base_case, "segments", "complete_unsat") != without_keys(
            extended_case, "segments", "complete_unsat"
        ):
            raise ValueError(f"extended bundle changed metadata for {label}")
        if bool(base_case.get("complete_unsat", False)) and not bool(
            extended_case.get("complete_unsat", False)
        ):
            raise ValueError(f"extended bundle weakened completion for {label}")
        base_complete = bool(base_case.get("complete_unsat", False))
        base_completion.append(base_complete)

        base_segments = base_case.get("segments")
        extended_segments = extended_case.get("segments")
        if not isinstance(base_segments, list) or not base_segments:
            raise ValueError(f"base bundle {label} has no explicit segments")
        if not isinstance(extended_segments, list):
            raise ValueError(f"extended bundle {label} segments are not a list")
        if extended_segments[: len(base_segments)] != base_segments:
            raise ValueError(f"extended bundle changed the {label} segment prefix")
        suffix = extended_segments[len(base_segments) :]

        chain = audited_chain_summary(audited_case, audit_schema, label)
        audited_segments = chain.get("segments")
        if not isinstance(audited_segments, list) or int(
            chain.get("segment_count", -1)
        ) != len(base_segments):
            raise ValueError(f"base audit {label} segment count mismatch")
        if audit_schema == BASE_AUDIT_SCHEMA and len(audited_segments) != len(
            base_segments
        ):
            raise ValueError(f"base audit {label} replay count mismatch")
        if not audited_segments or not isinstance(audited_segments[-1], dict):
            raise ValueError(f"base audit {label} has no terminal segment")
        if (
            bool(chain.get("complete_unsat", False)) != base_complete
            or bool(audited_case.get("complete_unsat", False)) != base_complete
        ):
            raise ValueError(f"base audit {label} completion mismatch")
        if base_complete:
            raise ValueError(f"cannot append after complete {label} chain")
        extensions.append(
            {
                "label": label,
                "base_case": base_case,
                "extended_case": extended_case,
                "base_chain": chain,
                "base_terminal": audited_segments[-1],
                "suffix": suffix,
            }
        )
    if bool(base_audit.get("all_cases_complete_unsat", False)) != all(base_completion):
        raise ValueError("base audit aggregate completion mismatch")
    if not any(extension["suffix"] for extension in extensions):
        raise ValueError("extended bundle appended no segment")
    return extensions


def bind_first_extension_boundary(
    previous: dict[str, Any],
    first_round: int,
    first_seed: Path,
    label: str,
) -> str:
    previous_round = int(previous["final_round"])
    if first_round == previous_round:
        return validate_chain_adjacency(previous, first_seed, label)
    if first_round == previous_round + 1:
        return validate_rescued_refinement_adjacency(previous, first_seed, label)
    raise ValueError(f"{label} proof-chain extension round mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_bundle", type=Path)
    parser.add_argument("base_audit", type=Path)
    parser.add_argument("extended_bundle", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--segment-jobs", type=int, default=1)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.jobs <= 0 or arguments.segment_jobs <= 0:
        parser.error("--jobs and --segment-jobs must be positive")
    for path in (
        arguments.base_bundle,
        arguments.base_audit,
        arguments.extended_bundle,
        arguments.checker,
    ):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    base_bundle = load_json(arguments.base_bundle)
    base_audit = load_json(arguments.base_audit)
    extended_bundle = load_json(arguments.extended_bundle)
    audit_bundle_hash = (
        base_audit.get("bundle_sha256")
        if base_audit.get("schema") == BASE_AUDIT_SCHEMA
        else base_audit.get("extended_bundle_sha256")
    )
    if audit_bundle_hash != file_sha256(arguments.base_bundle):
        raise ValueError("base audit is not bound to the supplied base bundle")
    checker = base_audit.get("checker")
    if not isinstance(checker, dict) or checker.get("sha256") != file_sha256(
        arguments.checker
    ):
        raise ValueError("base audit used a different checker binary")
    extensions = validate_extension_layout(base_bundle, base_audit, extended_bundle)

    root = Path(__file__).resolve().parents[1]
    chain_tool = root / "tools" / "audit_materialized_proof_chain.py"
    audited: list[dict[str, Any]] = []
    for extension in extensions:
        label = extension["label"]
        if extension["suffix"]:
            specs = chain_specs({"segments": extension["suffix"]}, f"{label} extension")
            for spec in specs:
                spec["seed_manifest"] = absolute_preserving_symlinks(
                    spec["seed_manifest"]
                )
                spec["chain_workdir"] = absolute_preserving_symlinks(
                    spec["chain_workdir"]
                )
                if spec["state"] is not None:
                    spec["state"] = absolute_preserving_symlinks(spec["state"])
            suffix_audit = audit_chain_segments(
                specs,
                label,
                arguments.checker,
                arguments.jobs,
                chain_tool,
                arguments.segment_jobs,
            )
            first_boundary = bind_first_extension_boundary(
                extension["base_terminal"],
                int(specs[0]["first_round"]),
                specs[0]["seed_manifest"],
                label,
            )
            suffix_audit["segments"][0]["boundary_from_previous"] = first_boundary
            terminal = suffix_audit["segments"][-1]
        else:
            suffix_audit = {
                "segment_count": 0,
                "segments": [],
                "complete_unsat": bool(
                    extension["base_chain"].get("complete_unsat", False)
                ),
            }
            terminal = extension["base_terminal"]
        complete = bool(suffix_audit["complete_unsat"])
        if complete != bool(extension["extended_case"].get("complete_unsat", False)):
            raise ValueError(f"{label} completion claim mismatch")
        audited.append(
            {
                "case": label,
                "base_segment_count": int(extension["base_chain"]["segment_count"]),
                "extension": suffix_audit,
                "terminal": terminal,
                "total_segment_count": int(extension["base_chain"]["segment_count"])
                + int(suffix_audit["segment_count"]),
                "complete_unsat": complete,
            }
        )

    all_complete = all(case["complete_unsat"] for case in audited)
    if not all_complete and not arguments.allow_partial:
        raise ValueError("extended bundle is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "base_bundle": str(arguments.base_bundle),
        "base_bundle_sha256": file_sha256(arguments.base_bundle),
        "base_audit": str(arguments.base_audit),
        "base_audit_sha256": file_sha256(arguments.base_audit),
        "extended_bundle": str(arguments.extended_bundle),
        "extended_bundle_sha256": file_sha256(arguments.extended_bundle),
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "proof_jobs": arguments.jobs,
        "segment_jobs": arguments.segment_jobs,
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
