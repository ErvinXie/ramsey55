#!/usr/bin/env python3
"""Compose a checked chain-bundle suffix with an audited parent baseline.

This incremental layer reuses, by hash, the base audit of the strengthening
and false-polarity backbone proofs.  It accepts only an unchanged parent
bundle whose chain-bundle pointer advances to a separately checked exact
prefix extension.
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
    )
    from tools.audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
    )
    from tools.audit_strengthened_parent_chain_bundle import (
        AUDIT_SCHEMA as PARENT_AUDIT_SCHEMA,
        BUNDLE_SCHEMA,
    )
    from tools.prove_materialized_cubes import file_sha256
else:
    from audit_fixed_pair_proof_bundle import load_json, required_path
    from audit_materialized_proof_chain_bundle import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
    )
    from audit_materialized_proof_chain_bundle_extension import (
        AUDIT_SCHEMA as CHAIN_EXTENSION_AUDIT_SCHEMA,
    )
    from audit_strengthened_parent_chain_bundle import (
        AUDIT_SCHEMA as PARENT_AUDIT_SCHEMA,
        BUNDLE_SCHEMA,
    )
    from prove_materialized_cubes import file_sha256


AUDIT_SCHEMA = "ramsey55.strengthened-parent-chain-bundle-extension-audit.v1"


def without_keys(document: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in keys}


def validate_parent_extension_layout(
    base_bundle: dict[str, Any],
    base_parent_audit: dict[str, Any],
    extended_bundle: dict[str, Any],
    chain_extension_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    if base_bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected base strengthened-parent bundle schema")
    if extended_bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected extended strengthened-parent bundle schema")
    parent_audit_schema = str(base_parent_audit.get("schema"))
    if parent_audit_schema not in (PARENT_AUDIT_SCHEMA, AUDIT_SCHEMA):
        raise ValueError("unexpected base strengthened-parent audit schema")
    if chain_extension_audit.get("schema") != CHAIN_EXTENSION_AUDIT_SCHEMA:
        raise ValueError("unexpected chain extension-audit schema")
    if without_keys(base_bundle, "claim", "chain_bundle") != without_keys(
        extended_bundle, "claim", "chain_bundle"
    ):
        raise ValueError("extended parent bundle changed audited base metadata")

    base_cases = base_parent_audit.get("cases")
    extension_cases = chain_extension_audit.get("cases")
    if not isinstance(base_cases, list) or not isinstance(extension_cases, list):
        raise ValueError("parent and chain-extension cases must be lists")
    if not base_cases or len(base_cases) != len(extension_cases):
        raise ValueError("parent and chain-extension case counts differ")

    joined: list[dict[str, Any]] = []
    for index, (base_case, extension_case) in enumerate(
        zip(base_cases, extension_cases)
    ):
        if not isinstance(base_case, dict) or not isinstance(extension_case, dict):
            raise ValueError(f"case {index} is not an object")
        label = str(base_case.get("case", f"case-{index}"))
        if extension_case.get("case") != base_case.get("case"):
            raise ValueError(f"parent and chain-extension labels differ for {label}")
        extension = extension_case.get("extension")
        if not isinstance(extension, dict):
            raise ValueError(f"extension audit is incomplete for {label}")
        if parent_audit_schema == PARENT_AUDIT_SCHEMA:
            strengthening = base_case.get("strengthening")
            backbone_audit = base_case.get("backbone_proof_audit")
            base_chain = base_case.get("chain")
            if not all(
                isinstance(value, dict)
                for value in (strengthening, backbone_audit, base_chain)
            ):
                raise ValueError(f"base audit is incomplete for {label}")
            if (
                strengthening.get("bad_branches_complete_unsat") is not True
                or backbone_audit.get("complete_unsat") is not True
            ):
                raise ValueError(f"base backbone audit is incomplete for {label}")
            base_segments = base_chain.get("segments")
            if not isinstance(base_segments, list) or not base_segments:
                raise ValueError(f"base chain has no terminal segment for {label}")
            base_segment_count = int(base_chain.get("segment_count", -1))
            base_unsat = bool(base_chain.get("complete_unsat", False))
            base_remaining = int(base_case.get("remaining_unknown_cubes", -1))
            if bool(
                base_case.get("parent_unsat", False)
            ) != base_unsat or base_remaining != int(
                base_segments[-1].get("final_unknown", -2)
            ):
                raise ValueError(f"base parent terminal summary differs for {label}")
        else:
            base_segment_count = int(base_case.get("total_segment_count", -1))
            base_unsat = bool(base_case.get("parent_unsat", False))
            base_remaining = int(base_case.get("remaining_unknown_cubes", -1))
            if base_segment_count <= 0 or base_remaining < 0:
                raise ValueError(f"recursive parent baseline is invalid for {label}")
        new_segments = extension.get("segments")
        terminal = extension_case.get("terminal")
        if terminal is None and isinstance(new_segments, list) and new_segments:
            terminal = new_segments[-1]
        if not isinstance(new_segments, list) or not isinstance(terminal, dict):
            raise ValueError(f"extension has no terminal binding for {label}")
        if int(extension_case.get("base_segment_count", -1)) != base_segment_count:
            raise ValueError(f"chain base segment count differs for {label}")
        if int(extension_case.get("total_segment_count", -1)) != int(
            base_segment_count
        ) + int(extension.get("segment_count", -1)):
            raise ValueError(f"chain total segment count differs for {label}")
        parent_unsat = bool(extension_case.get("complete_unsat", False))
        if parent_unsat != bool(extension.get("complete_unsat", False)):
            raise ValueError(f"extension completion differs for {label}")
        joined.append(
            {
                "case": label,
                "base_parent_unsat": base_unsat,
                "base_remaining_unknown_cubes": base_remaining,
                "base_segment_count": base_segment_count,
                "extension_segment_count": int(extension["segment_count"]),
                "total_segment_count": int(extension_case["total_segment_count"]),
                "remaining_unknown_cubes": int(terminal["final_unknown"]),
                "parent_unsat": parent_unsat,
            }
        )
    if bool(base_parent_audit.get("all_parents_unsat", False)) != all(
        bool(case.get("parent_unsat", False)) for case in base_cases
    ):
        raise ValueError("base parent aggregate completion mismatch")
    return joined


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_bundle", type=Path)
    parser.add_argument("base_parent_audit", type=Path)
    parser.add_argument("base_chain_audit", type=Path)
    parser.add_argument("extended_bundle", type=Path)
    parser.add_argument("chain_extension_audit", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    for path in (
        arguments.base_bundle,
        arguments.base_parent_audit,
        arguments.base_chain_audit,
        arguments.extended_bundle,
        arguments.chain_extension_audit,
    ):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")

    base_bundle = load_json(arguments.base_bundle)
    base_parent_audit = load_json(arguments.base_parent_audit)
    base_chain_audit = load_json(arguments.base_chain_audit)
    extended_bundle = load_json(arguments.extended_bundle)
    chain_extension_audit = load_json(arguments.chain_extension_audit)
    base_parent_schema = base_parent_audit.get("schema")
    if base_parent_schema == PARENT_AUDIT_SCHEMA:
        if base_chain_audit.get("schema") != CHAIN_AUDIT_SCHEMA:
            raise ValueError("unexpected standalone base chain-audit schema")
        parent_bundle_hash = base_parent_audit.get("bundle_sha256")
        if base_parent_audit.get("chain_audit") != base_chain_audit:
            raise ValueError("base parent and standalone chain audits differ")
    elif base_parent_schema == AUDIT_SCHEMA:
        if base_chain_audit.get("schema") != CHAIN_EXTENSION_AUDIT_SCHEMA:
            raise ValueError("unexpected recursive base chain-audit schema")
        parent_bundle_hash = base_parent_audit.get("extended_bundle_sha256")
        if base_parent_audit.get("chain_extension_audit_sha256") != file_sha256(
            arguments.base_chain_audit
        ):
            raise ValueError("recursive parent and chain audits differ")
    else:
        raise ValueError("unexpected base strengthened-parent audit schema")
    if parent_bundle_hash != file_sha256(arguments.base_bundle):
        raise ValueError("base parent audit is not bound to its bundle")
    base_chain_bundle = required_path(base_bundle, "chain_bundle")
    extended_chain_bundle = required_path(extended_bundle, "chain_bundle")
    audited_chain_bundle_hash = (
        base_parent_audit.get("chain_bundle_sha256")
        if base_parent_schema == PARENT_AUDIT_SCHEMA
        else base_parent_audit.get("extended_chain_bundle_sha256")
    )
    if (
        audited_chain_bundle_hash != file_sha256(base_chain_bundle)
        or chain_extension_audit.get("base_bundle_sha256")
        != file_sha256(base_chain_bundle)
        or chain_extension_audit.get("base_audit_sha256")
        != file_sha256(arguments.base_chain_audit)
    ):
        raise ValueError("chain extension is not bound to the parent baseline")
    if chain_extension_audit.get("extended_bundle_sha256") != file_sha256(
        extended_chain_bundle
    ):
        raise ValueError("chain extension is not bound to the extended chain bundle")

    cases = validate_parent_extension_layout(
        base_bundle,
        base_parent_audit,
        extended_bundle,
        chain_extension_audit,
    )
    all_unsat = all(case["parent_unsat"] for case in cases)
    if not all_unsat and not arguments.allow_partial:
        raise ValueError("extended parent bundle is incomplete; pass --allow-partial")
    result = {
        "schema": AUDIT_SCHEMA,
        "base_bundle": str(arguments.base_bundle),
        "base_bundle_sha256": file_sha256(arguments.base_bundle),
        "base_parent_audit": str(arguments.base_parent_audit),
        "base_parent_audit_sha256": file_sha256(arguments.base_parent_audit),
        "base_chain_audit": str(arguments.base_chain_audit),
        "base_chain_audit_sha256": file_sha256(arguments.base_chain_audit),
        "extended_bundle": str(arguments.extended_bundle),
        "extended_bundle_sha256": file_sha256(arguments.extended_bundle),
        "chain_extension_audit": str(arguments.chain_extension_audit),
        "chain_extension_audit_sha256": file_sha256(arguments.chain_extension_audit),
        "base_chain_bundle": str(base_chain_bundle),
        "base_chain_bundle_sha256": file_sha256(base_chain_bundle),
        "extended_chain_bundle": str(extended_chain_bundle),
        "extended_chain_bundle_sha256": file_sha256(extended_chain_bundle),
        "cases": cases,
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
