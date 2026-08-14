#!/usr/bin/env python3
"""Verify unified DRAT proofs for the three order-45 edge strata."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_order45_fixed_pair_proofs import (
        audit_results,
        check_proof,
        dimacs_shape,
        file_sha256,
    )
    from tools.audit_order45_strata_leaf_proofs import (
        audit_runner_log,
        read_bound_cubes,
    )
else:
    from audit_order45_fixed_pair_proofs import (
        audit_results,
        check_proof,
        dimacs_shape,
        file_sha256,
    )
    from audit_order45_strata_leaf_proofs import (
        audit_runner_log,
        read_bound_cubes,
    )


SCHEMA = "ramsey55.order45-strata-proofs.v1"
FORMULA_SCHEMA = "ramsey55.order45-edge-strata.v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--formula-manifest",
        type=Path,
        default=Path("build/order45-strata/manifest.json"),
    )
    parser.add_argument(
        "--cnf-dir", type=Path, default=Path("build/order45-strata")
    )
    parser.add_argument(
        "--cube-dir", type=Path, default=Path("build/order45-strata")
    )
    parser.add_argument(
        "--proof-dir",
        type=Path,
        default=Path("build/order45-strata/unified-b30000-solve10-v2"),
    )
    parser.add_argument(
        "--checker", type=Path, default=Path(".tools/src/drat-trim/drat-trim")
    )
    parser.add_argument(
        "--runner", type=Path, default=Path("build/prove_cadical_cubes")
    )
    parser.add_argument("--conflicts", type=int, required=True)
    parser.add_argument("--maximum-conflicts", type=int, required=True)
    parser.add_argument(
        "--maximum-lookahead-seconds", type=float, required=True
    )
    parser.add_argument("--maximum-primary-split-variable", type=int, default=0)
    parser.add_argument("--maximum-solve-seconds", type=float, default=0.0)
    parser.add_argument(
        "--freeze-policy",
        choices=("legacy-all", "selective"),
        default="legacy-all",
    )
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--degree", type=int, action="append")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/order45-strata-proof-manifest.json"),
    )
    arguments = parser.parse_args()

    if (
        arguments.conflicts <= 0
        or arguments.maximum_conflicts < arguments.conflicts
        or not math.isfinite(arguments.maximum_lookahead_seconds)
        or arguments.maximum_lookahead_seconds < 0
        or arguments.maximum_primary_split_variable < 0
        or not math.isfinite(arguments.maximum_solve_seconds)
        or arguments.maximum_solve_seconds < 0
    ):
        parser.error("invalid proof-runner parameters")

    raw_manifest = arguments.formula_manifest.read_bytes()
    formula_manifest = json.loads(raw_manifest)
    if formula_manifest.get("schema") != FORMULA_SCHEMA:
        raise ValueError("unexpected formula manifest schema")
    manifest_sha256 = hashlib.sha256(raw_manifest).hexdigest()
    requested_degrees = set(arguments.degree or ())
    records = [
        record
        for record in formula_manifest["files"]
        if not requested_degrees or int(record["degree"]) in requested_degrees
    ]
    if requested_degrees and requested_degrees != {
        int(record["degree"]) for record in records
    }:
        raise ValueError("requested degree is absent from the formula manifest")
    for executable in (arguments.checker, arguments.runner):
        if not executable.is_file():
            raise FileNotFoundError(executable)

    proofs: list[dict[str, Any]] = []
    missing: list[str] = []
    for record in records:
        degree = int(record["degree"])
        cnf = arguments.cnf_dir / record["path"]
        cubes_path = arguments.cube_dir / f"cubes-d{degree}.txt"
        stem = arguments.proof_dir / f"d{degree}"
        proof = stem.with_suffix(".drat")
        results = stem.with_suffix(".tsv")
        runner_log = stem.with_suffix(".log")
        checker_log = stem.with_suffix(".drat-trim.log")
        required = (proof, results, runner_log)
        if not all(path.is_file() for path in required):
            missing.append(f"d{degree}")
            continue
        if "status\t20" not in runner_log.read_text(encoding="utf-8"):
            if arguments.allow_partial:
                missing.append(f"d{degree}")
                continue
            raise ValueError(f"runner did not report status 20 for d{degree}")

        variables, clauses = dimacs_shape(cnf)
        if (variables, clauses) != (record["variables"], record["clauses"]):
            raise ValueError(f"formula shape mismatch for d{degree}")
        if file_sha256(cnf) != record["sha256"]:
            raise ValueError(f"formula hash mismatch for d{degree}")
        metadata, cubes = read_bound_cubes(cubes_path)
        expected_cubes = tuple(tuple(cube["literals"]) for cube in record["cubes"])
        if cubes != expected_cubes:
            raise ValueError(f"cube file differs from manifest for d{degree}")
        if metadata != {
            "manifest_sha256": manifest_sha256,
            "cnf_sha256": record["sha256"],
            "degree": str(degree),
        }:
            raise ValueError(f"cube metadata mismatch for d{degree}")
        initially_frozen = {
            abs(literal) for cube in cubes for literal in cube
        } | set(range(1, arguments.maximum_primary_split_variable + 1))

        audit_runner_log(
            runner_log,
            "all",
            arguments.conflicts,
            arguments.maximum_conflicts,
            arguments.maximum_lookahead_seconds,
            arguments.maximum_primary_split_variable,
            arguments.maximum_solve_seconds,
            arguments.freeze_policy,
            len(initially_frozen),
        )
        statistics = audit_results(results, len(cubes))
        if statistics["minimum_conflict_limit"] != arguments.conflicts:
            raise ValueError(f"base conflict limit mismatch for d{degree}")
        if statistics["maximum_conflict_limit"] > arguments.maximum_conflicts:
            raise ValueError(f"maximum conflict limit exceeded for d{degree}")
        check_proof(arguments.checker, cnf, proof, checker_log)
        proofs.append(
            {
                "degree": degree,
                "formula": {
                    "path": str(cnf),
                    "sha256": record["sha256"],
                    "variables": variables,
                    "clauses": clauses,
                },
                "cubes": {
                    "path": str(cubes_path),
                    "sha256": file_sha256(cubes_path),
                    "count": len(cubes),
                },
                "proof": {
                    "path": str(proof),
                    "sha256": file_sha256(proof),
                    "bytes": proof.stat().st_size,
                    "format": "binary DRAT",
                },
                "results": {
                    "path": str(results),
                    "sha256": file_sha256(results),
                    **statistics,
                },
                "runner_log": {
                    "path": str(runner_log),
                    "sha256": file_sha256(runner_log),
                },
                "checker_log": {
                    "path": str(checker_log),
                    "sha256": file_sha256(checker_log),
                },
            }
        )
        print(f"verified d{degree}: {proof}")

    if missing and not arguments.allow_partial:
        raise FileNotFoundError(f"missing unified proofs: {missing}")
    document = {
        "schema": SCHEMA,
        "complete": not missing,
        "claim": (
            "all three order-45 exact-edge mother CNFs are UNSAT"
            if not missing
            else "partial unified order-45 stratum proof inventory"
        ),
        "formula_manifest": {
            "path": str(arguments.formula_manifest),
            "sha256": manifest_sha256,
        },
        "runner": {
            "path": str(arguments.runner),
            "sha256": file_sha256(arguments.runner),
            "parameters": {
                "conflicts": arguments.conflicts,
                "maximum_conflicts": arguments.maximum_conflicts,
                "maximum_lookahead_seconds": arguments.maximum_lookahead_seconds,
                "maximum_primary_split_variable": (
                    arguments.maximum_primary_split_variable
                ),
                "maximum_solve_seconds": arguments.maximum_solve_seconds,
                "freeze_policy": arguments.freeze_policy,
                "root_index": "all",
            },
        },
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "auditor": {
            "path": str(Path(__file__)),
            "sha256": file_sha256(Path(__file__)),
        },
        "proofs": proofs,
        "missing": missing,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {arguments.output}: {len(proofs)} verified, {len(missing)} missing")


if __name__ == "__main__":
    main()
