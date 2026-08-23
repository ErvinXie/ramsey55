#!/usr/bin/env python3
"""Independently hash-check and replay a complete gluing proof bundle."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import time
from pathlib import Path

BRANCH_SCHEMA = "ramsey55.r45-gluing-branches.v1"
PROOF_SCHEMA = "ramsey55.r45-gluing-proofs.v1"
SCHEMA = "ramsey55.r45-gluing-proof-audit.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_artifact(root: Path, record: dict[str, object]) -> Path:
    path = root / str(record["path"])
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or file_sha256(path) != record.get("sha256")
    ):
        raise ValueError(f"artifact does not match proof manifest: {path}")
    return path


def audit(
    proof_manifest_path: Path,
    branch_manifest_path: Path,
    proof_dir: Path,
    checker: Path,
    audit_dir: Path,
    output: Path,
    jobs: int,
    cnf_dir: Path | None = None,
) -> dict[str, object]:
    proofs = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    branches = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    if proofs.get("schema") != PROOF_SCHEMA or branches.get("schema") != BRANCH_SCHEMA:
        raise ValueError("unexpected gluing proof or branch schema")
    link = proofs.get("branch_manifest")
    if not isinstance(link, dict) or link.get("sha256") != file_sha256(
        branch_manifest_path
    ):
        raise ValueError("proof manifest does not bind the branch manifest")
    branch_records = branches.get("files")
    proof_records = proofs.get("results")
    if (
        not isinstance(branch_records, list)
        or not isinstance(proof_records, list)
        or [record.get("pair_index") for record in proof_records]
        != [record.get("pair_index") for record in branch_records]
        or proofs.get("summary", {}).get("complete_unsat") is not True
    ):
        raise ValueError("proof result coverage is incomplete")
    if output.exists() or audit_dir.exists():
        raise FileExistsError("refusing to overwrite an audit output")
    audit_dir.mkdir(parents=True)
    formulas = cnf_dir or branch_manifest_path.parent

    tasks = []
    for branch, proof in zip(branch_records, proof_records, strict=True):
        pair_index = int(branch["pair_index"])
        cnf = formulas / str(branch["path"])
        if (
            file_sha256(cnf) != branch.get("sha256")
            or proof.get("status") != "VERIFIED_UNSAT"
            or proof.get("cnf", {}).get("sha256") != branch.get("sha256")
        ):
            raise ValueError(f"pair {pair_index}: formula binding mismatch")
        for field in (
            "solver_log",
            "solver_time",
            "checker_log",
            "checker_time",
        ):
            checked_artifact(proof_dir, proof[field])
        proof_path = checked_artifact(proof_dir, proof["proof"])
        tasks.append((pair_index, cnf, proof_path))

    def replay(task: tuple[int, Path, Path]) -> dict[str, object]:
        pair_index, cnf, proof = task
        started = time.monotonic()
        completed = subprocess.run(
            [str(checker), str(cnf), str(proof)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        seconds = round(time.monotonic() - started, 6)
        log = audit_dir / f"pair-{pair_index:06d}.checker.log"
        log.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode or "s VERIFIED" not in completed.stdout:
            raise RuntimeError(f"pair {pair_index}: independent checker replay failed")
        print(f"replayed pair {pair_index}: {seconds:.3f}s", flush=True)
        return {
            "pair_index": pair_index,
            "status": "VERIFIED_UNSAT",
            "seconds": seconds,
            "checker_log": {
                "path": log.name,
                "bytes": log.stat().st_size,
                "sha256": file_sha256(log),
            },
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        replayed = list(executor.map(replay, tasks))
    document = {
        "schema": SCHEMA,
        "proof_manifest": {
            "path": str(proof_manifest_path),
            "sha256": file_sha256(proof_manifest_path),
        },
        "branch_manifest": {
            "path": str(branch_manifest_path),
            "sha256": file_sha256(branch_manifest_path),
        },
        "checker": {"path": str(checker), "sha256": file_sha256(checker)},
        "results": replayed,
        "summary": {
            "formulas": len(replayed),
            "verified_unsat": len(replayed),
            "complete_unsat": True,
        },
    }
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("branch_manifest", type=Path)
    parser.add_argument("proof_dir", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--cnf-dir", type=Path)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")
    audit(
        arguments.proof_manifest,
        arguments.branch_manifest,
        arguments.proof_dir,
        arguments.checker,
        arguments.audit_dir,
        arguments.output,
        arguments.jobs,
        arguments.cnf_dir,
    )
    print(f"wrote {arguments.output}")


if __name__ == "__main__":
    main()
