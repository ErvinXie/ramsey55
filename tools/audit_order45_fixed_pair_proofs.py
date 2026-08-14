#!/usr/bin/env python3
"""Check and inventory proof artifacts for the order-45 H100/J132 layer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


SCHEMA = "ramsey55.order45-fixed-pair-proofs.v1"
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dimacs_shape(path: Path) -> tuple[int, int]:
    variables = clauses = None
    actual_clauses = 0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if not line.strip() or line.startswith("c"):
                continue
            fields = line.split()
            if fields[0] == "p":
                if variables is not None or len(fields) != 4 or fields[1] != "cnf":
                    raise ValueError(f"invalid DIMACS header in {path}")
                variables, clauses = map(int, fields[2:])
                continue
            if variables is None or not fields or fields[-1] != "0":
                raise ValueError(f"invalid DIMACS clause in {path}")
            actual_clauses += 1
    if variables is None or clauses is None or actual_clauses != clauses:
        raise ValueError(f"DIMACS clause count mismatch in {path}")
    return variables, clauses


def cube_count(path: Path) -> int:
    count = 0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            if not line.strip() or line.startswith("c"):
                continue
            fields = line.split()
            if fields[0] != "a":
                if int(fields[0]) != count:
                    raise ValueError(f"nonconsecutive cube id in {path}")
                fields = fields[1:]
            if len(fields) < 2 or fields[-1] != "0" or "0" in fields[:-1]:
                raise ValueError(f"invalid cube in {path}")
            count += 1
    if not count:
        raise ValueError(f"empty cube file {path}")
    return count


def audit_results(path: Path, roots: int) -> dict[str, int | float]:
    attempts = splits = closed = 0
    global_unsat_cores = 0
    minimum_limit: int | None = None
    maximum_depth = maximum_limit = 0
    total_seconds = 0.0
    per_root: dict[int, list[int]] = {}
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
            root, attempt, depth, limit, status, core, split = map(int, fields[:7])
            seconds = float(fields[7])
            if attempt != attempts or not 0 <= root < roots:
                raise ValueError(f"invalid attempt or root in {path}")
            if depth < 0 or limit <= 0 or seconds < 0:
                raise ValueError(f"invalid numeric field in {path}")
            if status == 0:
                if core != 0 or split == 0:
                    raise ValueError(f"invalid split row in {path}")
                splits += 1
            elif status == 20:
                if core < 0 or split != 0:
                    raise ValueError(f"invalid UNSAT row in {path}")
                closed += 1
                global_unsat_cores += core == 0
            else:
                raise ValueError(f"non-UNSAT terminal status {status} in {path}")
            counts = per_root.setdefault(root, [0, 0])
            counts[status == 20] += 1
            attempts += 1
            maximum_depth = max(maximum_depth, depth)
            minimum_limit = (
                limit if minimum_limit is None else min(minimum_limit, limit)
            )
            maximum_limit = max(maximum_limit, limit)
            total_seconds += seconds
    covered_roots = len(per_root)
    if set(per_root) != set(range(covered_roots)):
        raise ValueError(f"result file {path} does not cover a root prefix")
    if covered_roots != roots and not global_unsat_cores:
        raise ValueError(f"result file {path} does not cover all {roots} roots")
    for root, (root_splits, root_closed) in per_root.items():
        if root_closed != root_splits + 1:
            raise ValueError(f"unbalanced binary tree for root {root} in {path}")
    if closed != covered_roots + splits:
        raise ValueError(f"global binary tree balance failed in {path}")
    return {
        "attempts": attempts,
        "covered_roots": covered_roots,
        "global_unsat_cores": global_unsat_cores,
        "splits": splits,
        "unsat_leaves": closed,
        "maximum_extra_depth": maximum_depth,
        "minimum_conflict_limit": minimum_limit,
        "maximum_conflict_limit": maximum_limit,
        "reported_solve_seconds": round(total_seconds, 6),
    }


def check_proof(checker: Path, cnf: Path, proof: Path, log: Path) -> None:
    completed = subprocess.run(
        [str(checker), str(cnf), str(proof)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode or "s VERIFIED" not in completed.stdout:
        raise RuntimeError(
            f"proof checker rejected {proof}; see {log} (exit {completed.returncode})"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--formula-manifest",
        type=Path,
        default=Path("data/order45-fixed-pair-manifest.json"),
    )
    parser.add_argument(
        "--cnf-dir", type=Path, default=Path("build/order45-fixed-pairs")
    )
    parser.add_argument(
        "--cube-dir",
        type=Path,
        default=Path("build/order45-fixed-pairs/cadical-cubes"),
    )
    parser.add_argument(
        "--proof-dir",
        type=Path,
        default=Path("build/order45-fixed-pairs/cadical-proof-dynamic"),
    )
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/order45-fixed-pair-proof-manifest.json"),
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

    formula_manifest = json.loads(arguments.formula_manifest.read_text())
    if formula_manifest.get("schema") != "ramsey55.order45-fixed-pairs.v1":
        raise ValueError("unexpected formula manifest schema")
    symmetry_breaking = formula_manifest.get("symmetry_breaking")
    if not isinstance(symmetry_breaking, bool):
        raise ValueError("formula manifest does not declare symmetry mode")
    for executable in (arguments.checker, arguments.runner):
        if not executable.is_file():
            raise FileNotFoundError(executable)

    proofs: list[dict[str, Any]] = []
    for formula in formula_manifest["formulas"]:
        j_index = int(formula["j_index"])
        stem = f"h0-j{j_index}"
        cnf = arguments.cnf_dir / formula["path"]
        cubes = arguments.cube_dir / f"{stem}-d14.icnf"
        proof = arguments.proof_dir / f"{stem}.drat"
        results = arguments.proof_dir / f"{stem}.tsv"
        checker_log = arguments.proof_dir / f"{stem}.drat-trim.log"
        variables, clauses = dimacs_shape(cnf)
        if (variables, clauses) != (formula["variables"], formula["clauses"]):
            raise ValueError(f"formula shape mismatch for J{j_index}")
        if file_sha256(cnf) != formula["sha256"]:
            raise ValueError(f"formula hash mismatch for J{j_index}")
        roots = cube_count(cubes)
        statistics = audit_results(results, roots)
        if arguments.conflicts is not None:
            if statistics["minimum_conflict_limit"] != arguments.conflicts:
                raise ValueError(f"base conflict limit mismatch for J{j_index}")
            if statistics["maximum_conflict_limit"] > arguments.maximum_conflicts:
                raise ValueError(f"maximum conflict limit exceeded for J{j_index}")
        check_proof(arguments.checker, cnf, proof, checker_log)
        proofs.append(
            {
                "h_index": int(formula["h_index"]),
                "j_index": j_index,
                "formula": {
                    "path": str(cnf),
                    "sha256": formula["sha256"],
                    "variables": variables,
                    "clauses": clauses,
                },
                "cubes": {
                    "path": str(cubes),
                    "sha256": file_sha256(cubes),
                    "count": roots,
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
                "checker_log": {
                    "path": str(checker_log),
                    "sha256": file_sha256(checker_log),
                },
            }
        )
        print(f"verified J{j_index}: {proof}")

    document = {
        "schema": SCHEMA,
        "claim": (
            "both H100/J132 lex-leader CNFs are UNSAT; the labelled claim "
            "requires the finite-orbit symmetry bridge"
            if symmetry_breaking
            else "both complete labelled H100/J132 fixed-pair CNFs are UNSAT"
        ),
        "symmetry_breaking": symmetry_breaking,
        "symmetry_bridge_required": symmetry_breaking,
        "formula_manifest": {
            "path": str(arguments.formula_manifest),
            "sha256": file_sha256(arguments.formula_manifest),
        },
        "proof_runner": {
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
                }
                if arguments.conflicts is not None
                else None
            ),
        },
        "auditor": {
            "path": str(Path(__file__)),
            "sha256": file_sha256(Path(__file__)),
        },
        "proof_checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "proofs": proofs,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {arguments.output}")


if __name__ == "__main__":
    main()
