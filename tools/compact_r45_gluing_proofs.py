#!/usr/bin/env python3
"""Emit and recheck binary core proofs for a checked gluing family."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

BRANCH_SCHEMAS = {
    "ramsey55.r45-gluing-branches.v1",
    "ramsey55.r45-gluing-branches.v2",
}
PROOF_SCHEMA = "ramsey55.r45-gluing-proofs.v1"
SCHEMA = "ramsey55.r45-gluing-core-proofs.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_artifact(root: Path, record: object) -> Path:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise TypeError("missing or malformed artifact record")
    path = root / record["path"]
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or file_sha256(path) != record.get("sha256")
    ):
        raise ValueError(f"artifact mismatch: {path}")
    return path


def artifact(path: Path) -> dict[str, object]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def exact_verified(path: Path) -> bool:
    return any(
        line.rstrip("\n").strip("\r") == "s VERIFIED"
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
    )


def run_checker(command: list[str], log: Path) -> tuple[int, float]:
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as output:
        completed = subprocess.run(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return completed.returncode, round(time.monotonic() - started, 6)


def compact(
    proof_manifest_path: Path,
    branch_manifest_path: Path,
    proof_dir: Path,
    checker: Path,
    output_dir: Path,
    jobs: int,
    cnf_dir: Path | None = None,
) -> dict[str, object]:
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    if not checker.is_file():
        raise ValueError(f"missing checker: {checker}")

    proofs = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    branches = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    branch_schema = branches.get("schema")
    if proofs.get("schema") != PROOF_SCHEMA or branch_schema not in BRANCH_SCHEMAS:
        raise ValueError("unexpected gluing proof or branch schema")
    link = proofs.get("branch_manifest")
    if (
        not isinstance(link, dict)
        or link.get("sha256") != file_sha256(branch_manifest_path)
        or link.get("schema") != branch_schema
    ):
        raise ValueError("proof manifest does not bind branch manifest")
    checker_record = proofs.get("checker")
    if (
        not isinstance(checker_record, dict)
        or checker_record.get("sha256") != file_sha256(checker)
    ):
        raise ValueError("checker does not match proof manifest")
    summary = proofs.get("summary")
    branch_records = branches.get("files")
    proof_records = proofs.get("results")
    if (
        not isinstance(summary, dict)
        or summary.get("complete_unsat") is not True
        or not isinstance(branch_records, list)
        or not isinstance(proof_records, list)
        or not branch_records
        or [record.get("pair_index") for record in branch_records]
        != [record.get("pair_index") for record in proof_records]
    ):
        raise ValueError("checked proof family is incomplete")

    formulas = cnf_dir or branch_manifest_path.parent
    tasks = []
    for branch, proof in zip(branch_records, proof_records, strict=True):
        pair_index = int(branch["pair_index"])
        cnf = formulas / str(branch["path"])
        if (
            not cnf.is_file()
            or file_sha256(cnf) != branch.get("sha256")
            or proof.get("status") != "VERIFIED_UNSAT"
            or proof.get("cnf", {}).get("sha256") != branch.get("sha256")
        ):
            raise ValueError(f"pair {pair_index}: formula binding mismatch")
        source = checked_artifact(proof_dir, proof.get("proof"))
        tasks.append((pair_index, cnf, source))

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent)
    )
    try:
        def worker(task: tuple[int, Path, Path]) -> dict[str, object]:
            pair_index, cnf, source = task
            stem = cnf.stem
            core = temporary / f"{stem}.core.drat"
            source_log = temporary / f"{stem}.source-checker.log"
            core_log = temporary / f"{stem}.core-checker.log"
            source_status, source_seconds = run_checker(
                [str(checker), str(cnf), str(source), "-l", str(core), "-C"],
                source_log,
            )
            if source_status or not exact_verified(source_log) or not core.is_file():
                raise RuntimeError(f"pair {pair_index}: source proof/core trim failed")
            core_status, core_seconds = run_checker(
                [str(checker), str(cnf), str(core)], core_log
            )
            if core_status or not exact_verified(core_log):
                raise RuntimeError(f"pair {pair_index}: core proof replay failed")
            result = {
                "pair_index": pair_index,
                "status": "VERIFIED_UNSAT",
                "cnf_sha256": file_sha256(cnf),
                "source_proof": artifact(source),
                "core_proof": artifact(core),
                "source_checker_log": artifact(source_log),
                "core_checker_log": artifact(core_log),
                "source_checker_seconds": source_seconds,
                "core_checker_seconds": core_seconds,
            }
            print(
                f"compacted pair {pair_index}: "
                f"{result['source_proof']['bytes']} -> {result['core_proof']['bytes']}",
                flush=True,
            )
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(worker, tasks))

        source_bytes = sum(int(result["source_proof"]["bytes"]) for result in results)
        core_bytes = sum(int(result["core_proof"]["bytes"]) for result in results)
        document = {
            "schema": SCHEMA,
            "claim": "checked core proofs for listed formulas only",
            "proof_manifest": {
                "path": str(proof_manifest_path),
                "sha256": file_sha256(proof_manifest_path),
                "schema": PROOF_SCHEMA,
            },
            "branch_manifest": {
                "path": str(branch_manifest_path),
                "sha256": file_sha256(branch_manifest_path),
                "schema": branch_schema,
            },
            "checker": {"path": str(checker), "sha256": file_sha256(checker)},
            "results": results,
            "summary": {
                "formulas": len(results),
                "verified_unsat": len(results),
                "complete_for_listed_formulas": True,
                "source_proof_bytes": source_bytes,
                "core_proof_bytes": core_bytes,
                "core_to_source_ratio": round(core_bytes / source_bytes, 9),
            },
        }
        manifest = temporary / "manifest.json"
        manifest.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.rename(output_dir)
        return document
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("branch_manifest", type=Path)
    parser.add_argument("proof_dir", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--cnf-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    compact(
        arguments.proof_manifest,
        arguments.branch_manifest,
        arguments.proof_dir,
        arguments.checker,
        arguments.output_dir,
        arguments.jobs,
        arguments.cnf_dir,
    )
    print(f"wrote {arguments.output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
