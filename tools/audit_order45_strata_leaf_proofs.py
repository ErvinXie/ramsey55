#!/usr/bin/env python3
"""Verify a complete independently checkable leaf-proof collection."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
from typing import Any

if __package__:
    from tools.audit_order45_fixed_pair_proofs import dimacs_shape, file_sha256
    from tools.materialize_cnf_cube import materialize_cnf_cube
else:
    from audit_order45_fixed_pair_proofs import dimacs_shape, file_sha256
    from materialize_cnf_cube import materialize_cnf_cube


SCHEMA = "ramsey55.order45-strata-leaf-proofs.v1"
FORMULA_SCHEMA = "ramsey55.order45-edge-strata.v1"
RESULT_HEADER = (
    "root",
    "attempt",
    "depth",
    "limit",
    "status",
    "core",
    "split",
    "seconds",
)


def read_bound_cubes(path: Path) -> tuple[dict[str, str], tuple[tuple[int, ...], ...]]:
    metadata: dict[str, str] = {}
    cubes: list[tuple[int, ...]] = []
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if not line.strip():
                continue
            fields = line.split()
            if fields[0] == "c":
                if len(fields) != 3 or fields[1] in metadata:
                    raise ValueError(f"invalid cube metadata in {path}")
                metadata[fields[1]] = fields[2]
                continue
            if int(fields[0]) != len(cubes) or len(fields) < 3 or fields[-1] != "0":
                raise ValueError(f"invalid cube row in {path}")
            cube = tuple(map(int, fields[1:-1]))
            if not cube or 0 in cube:
                raise ValueError(f"invalid cube literals in {path}")
            cubes.append(cube)
    if not cubes:
        raise ValueError(f"empty cube file {path}")
    return metadata, tuple(cubes)


def audit_root_results(path: Path, root: int) -> dict[str, int | float]:
    attempts = splits = closed = 0
    maximum_depth = maximum_limit = 0
    minimum_limit: int | None = None
    total_seconds = 0.0
    with path.open(newline="", encoding="ascii") as stream:
        rows = csv.reader(stream, delimiter="\t")
        try:
            header = tuple(next(rows))
        except StopIteration as error:
            raise ValueError(f"empty result file {path}") from error
        if header != RESULT_HEADER:
            raise ValueError(f"unexpected result header in {path}: {header}")
        for fields in rows:
            if len(fields) != len(RESULT_HEADER):
                raise ValueError(f"truncated result row in {path}")
            row_root, attempt, depth, limit, status, core, split = map(
                int, fields[:7]
            )
            seconds = float(fields[7])
            if row_root != root or attempt != attempts:
                raise ValueError(f"invalid root or attempt in {path}")
            if depth < 0 or limit <= 0 or seconds < 0:
                raise ValueError(f"invalid numeric field in {path}")
            if status == 0:
                if core or not split:
                    raise ValueError(f"invalid split row in {path}")
                splits += 1
            elif status == 20:
                if core < 0 or split:
                    raise ValueError(f"invalid UNSAT row in {path}")
                closed += 1
            else:
                raise ValueError(f"non-UNSAT terminal status {status} in {path}")
            attempts += 1
            maximum_depth = max(maximum_depth, depth)
            minimum_limit = (
                limit if minimum_limit is None else min(minimum_limit, limit)
            )
            maximum_limit = max(maximum_limit, limit)
            total_seconds += seconds
    if not attempts or closed != splits + 1:
        raise ValueError(f"unbalanced root tree in {path}")
    return {
        "attempts": attempts,
        "splits": splits,
        "unsat_leaves": closed,
        "maximum_extra_depth": maximum_depth,
        "minimum_conflict_limit": minimum_limit,
        "maximum_conflict_limit": maximum_limit,
        "reported_solve_seconds": round(total_seconds, 6),
    }


def check_leaf_proof(
    checker: Path,
    cnf: Path,
    cube: tuple[int, ...],
    proof: Path,
    checker_log: Path,
) -> str:
    with tempfile.TemporaryDirectory(prefix="ramsey55-leaf-audit-") as directory:
        augmented = Path(directory) / "augmented.cnf"
        materialize_cnf_cube(cnf, cube, augmented)
        augmented_sha256 = file_sha256(augmented)
        completed = subprocess.run(
            [str(checker), str(augmented), str(proof)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    checker_log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode or "s VERIFIED" not in completed.stdout:
        raise RuntimeError(
            f"checker rejected {proof}; see {checker_log} "
            f"(exit {completed.returncode})"
        )
    return augmented_sha256


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
    parser.add_argument("--proof-dir", type=Path, required=True)
    parser.add_argument(
        "--checker", type=Path, default=Path(".tools/src/drat-trim/drat-trim")
    )
    parser.add_argument(
        "--runner", type=Path, default=Path("build/prove_cadical_cubes")
    )
    parser.add_argument("--conflicts", type=int)
    parser.add_argument("--maximum-conflicts", type=int)
    parser.add_argument("--maximum-lookahead-seconds", type=float)
    parser.add_argument("--maximum-primary-split-variable", type=int, default=0)
    parser.add_argument("--maximum-solve-seconds", type=float, default=0.0)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--degree", type=int, action="append")
    parser.add_argument(
        "--output", type=Path, default=Path("build/order45-strata-leaf-proofs.json")
    )
    arguments = parser.parse_args()

    proof_parameters = (
        arguments.conflicts,
        arguments.maximum_conflicts,
        arguments.maximum_lookahead_seconds,
    )
    if any(value is not None for value in proof_parameters):
        if any(value is None for value in proof_parameters):
            parser.error("all three proof-runner parameters must be specified together")
        if (
            arguments.conflicts <= 0
            or arguments.maximum_conflicts < arguments.conflicts
            or not math.isfinite(arguments.maximum_lookahead_seconds)
            or arguments.maximum_lookahead_seconds < 0
        ):
            parser.error("invalid proof-runner parameters")
    if arguments.maximum_primary_split_variable < 0:
        parser.error("invalid maximum primary split variable")
    if (
        not math.isfinite(arguments.maximum_solve_seconds)
        or arguments.maximum_solve_seconds < 0
    ):
        parser.error("invalid maximum solve time")

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
        variables, clauses = dimacs_shape(cnf)
        if (variables, clauses) != (record["variables"], record["clauses"]):
            raise ValueError(f"formula shape mismatch for d{degree}")
        if file_sha256(cnf) != record["sha256"]:
            raise ValueError(f"formula hash mismatch for d{degree}")
        cube_path = arguments.cube_dir / f"cubes-d{degree}.txt"
        metadata, cubes = read_bound_cubes(cube_path)
        expected_cubes = tuple(tuple(cube["literals"]) for cube in record["cubes"])
        if cubes != expected_cubes:
            raise ValueError(f"cube file differs from manifest for d{degree}")
        if metadata != {
            "manifest_sha256": manifest_sha256,
            "cnf_sha256": record["sha256"],
            "degree": str(degree),
        }:
            raise ValueError(f"cube metadata mismatch for d{degree}")

        for index, cube in enumerate(cubes):
            stem = arguments.proof_dir / f"d{degree}-c{index}"
            proof = stem.with_suffix(".drat")
            results = stem.with_suffix(".tsv")
            runner_log = stem.with_suffix(".log")
            checker_log = stem.with_suffix(".drat-trim.log")
            required = (proof, results, runner_log)
            if not all(path.is_file() for path in required):
                missing.append(f"d{degree}/c{index}")
                continue
            if "status\t20" not in runner_log.read_text(encoding="utf-8"):
                if arguments.allow_partial:
                    missing.append(f"d{degree}/c{index}")
                    continue
                raise ValueError(f"runner did not report status 20 for d{degree}/c{index}")
            statistics = audit_root_results(results, index)
            if arguments.conflicts is not None:
                if statistics["minimum_conflict_limit"] != arguments.conflicts:
                    raise ValueError(f"base conflict limit mismatch for d{degree}/c{index}")
                if statistics["maximum_conflict_limit"] > arguments.maximum_conflicts:
                    raise ValueError(
                        f"maximum conflict limit exceeded for d{degree}/c{index}"
                    )
            augmented_sha256 = check_leaf_proof(
                arguments.checker, cnf, cube, proof, checker_log
            )
            proofs.append(
                {
                    "degree": degree,
                    "cube_index": index,
                    "edges_h": record["cubes"][index]["edges_h"],
                    "edges_j": record["cubes"][index]["edges_j"],
                    "cube": list(cube),
                    "augmented_formula_sha256": augmented_sha256,
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
            print(f"verified d{degree}/c{index}: {proof}")

    if missing and not arguments.allow_partial:
        raise FileNotFoundError(f"missing {len(missing)} leaf proofs: {missing[:5]}")
    document = {
        "schema": SCHEMA,
        "complete": not missing,
        "claim": (
            "all exact-edge cube augmentations are UNSAT"
            if not missing
            else "partial exact-edge cube proof inventory"
        ),
        "formula_manifest": {
            "path": str(arguments.formula_manifest),
            "sha256": manifest_sha256,
        },
        "runner": {
            "path": str(arguments.runner),
            "sha256": file_sha256(arguments.runner),
            "parameters": (
                {
                    "conflicts": arguments.conflicts,
                    "maximum_conflicts": arguments.maximum_conflicts,
                    "maximum_lookahead_seconds": (
                        arguments.maximum_lookahead_seconds
                    ),
                    "maximum_primary_split_variable": (
                        arguments.maximum_primary_split_variable
                    ),
                    "maximum_solve_seconds": arguments.maximum_solve_seconds,
                    "root_index": "per proof",
                }
                if arguments.conflicts is not None
                else None
            ),
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
    print(
        f"wrote {arguments.output}: {len(proofs)} verified, {len(missing)} missing"
    )


if __name__ == "__main__":
    main()
