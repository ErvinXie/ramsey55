#!/usr/bin/env python3
"""Bind checked per-branch DRAT artifacts into one gluing proof manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BRANCH_SCHEMAS = {
    "ramsey55.r45-gluing-branches.v1",
    "ramsey55.r45-gluing-branches.v2",
}
SCHEMA = "ramsey55.r45-gluing-proofs.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exit_status(path: Path) -> int:
    matches = [
        line.split(":", 1)[1].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith("Exit status:")
    ]
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one GNU time exit status")
    return int(matches[0])


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"missing artifact: {path}")
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": file_sha256(path)}


def collect(
    branch_manifest_path: Path,
    proof_dir: Path,
    solver: Path,
    checker: Path,
    output: Path,
    cnf_dir: Path | None = None,
) -> dict[str, object]:
    branches = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    branch_schema = branches.get("schema")
    if branch_schema not in BRANCH_SCHEMAS:
        raise ValueError("unexpected gluing branch schema")
    branch_records = branches.get("files")
    if not isinstance(branch_records, list) or not branch_records:
        raise ValueError("gluing branch manifest has no formulas")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    root = cnf_dir or branch_manifest_path.parent

    results = []
    for branch in branch_records:
        pair_index = int(branch["pair_index"])
        cnf = root / str(branch["path"])
        if file_sha256(cnf) != branch.get("sha256"):
            raise ValueError(f"pair {pair_index}: CNF SHA-256 mismatch")
        stem = cnf.stem
        proof = proof_dir / f"{stem}.drat"
        solver_log = proof_dir / f"{stem}.solver.log"
        solver_time = proof_dir / f"{stem}.solver.time.log"
        checker_log = proof_dir / f"{stem}.checker.log"
        checker_time = proof_dir / f"{stem}.checker.time.log"
        if exit_status(solver_time) != 20 or "s UNSATISFIABLE" not in solver_log.read_text(
            encoding="utf-8"
        ):
            raise ValueError(f"pair {pair_index}: solver did not report UNSAT")
        if exit_status(checker_time) != 0 or "s VERIFIED" not in checker_log.read_text(
            encoding="utf-8"
        ):
            raise ValueError(f"pair {pair_index}: checker did not verify proof")
        result = {
            "pair_index": pair_index,
            "cnf": {
                "path": cnf.name,
                "sha256": branch["sha256"],
                "variables": branch["variables"],
                "clauses": branch["clauses"],
            },
            "status": "VERIFIED_UNSAT",
            "proof": artifact(proof),
            "solver_log": artifact(solver_log),
            "solver_time": artifact(solver_time),
            "checker_log": artifact(checker_log),
            "checker_time": artifact(checker_time),
        }
        results.append(result)
        print(
            f"collected pair {pair_index}: proof_bytes={result['proof']['bytes']}"
        )

    document = {
        "schema": SCHEMA,
        "branch_manifest": {
            "path": str(branch_manifest_path),
            "sha256": file_sha256(branch_manifest_path),
            "schema": branch_schema,
        },
        "solver": {"path": str(solver), "sha256": file_sha256(solver)},
        "checker": {"path": str(checker), "sha256": file_sha256(checker)},
        "results": results,
        "summary": {
            "formulas": len(results),
            "verified_unsat": len(results),
            "complete_unsat": True,
            "proof_bytes": sum(int(result["proof"]["bytes"]) for result in results),
        },
    }
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("branch_manifest", type=Path)
    parser.add_argument("proof_dir", type=Path)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--cnf-dir", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    output = arguments.output or arguments.proof_dir / "manifest.json"
    collect(
        arguments.branch_manifest,
        arguments.proof_dir,
        arguments.solver,
        arguments.checker,
        output,
        arguments.cnf_dir,
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
