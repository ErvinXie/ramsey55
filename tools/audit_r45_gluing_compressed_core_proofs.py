#!/usr/bin/env python3
"""Independently audit checked and losslessly compressed R45 gluing cores."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


CORE_SCHEMA = "ramsey55.r45-gluing-core-proofs.v1"
COMPRESSED_SCHEMA = "ramsey55.r45-gluing-compressed-core-proofs.v1"
PROOF_SCHEMA = "ramsey55.r45-gluing-proofs.v1"
BRANCH_SCHEMAS = {
    "ramsey55.r45-gluing-branches.v1",
    "ramsey55.r45-gluing-branches.v2",
}
AUDIT_SCHEMA = "ramsey55.r45-gluing-compressed-core-proofs-audit.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def load_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid {label} JSON: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} is not a JSON object: {path}")
    return document


def valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_record(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"missing or malformed {label} record")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise ValueError(f"invalid {label} path")
    if not isinstance(record.get("bytes"), int) or record["bytes"] < 0:
        raise ValueError(f"invalid {label} byte count")
    if not valid_sha256(record.get("sha256")):
        raise ValueError(f"invalid {label} SHA-256")
    return record


def basename_artifact(root: Path, record: object, label: str) -> tuple[Path, dict[str, Any]]:
    checked = validate_record(record, label)
    relative = Path(checked["path"])
    if relative.is_absolute() or relative.name != str(relative):
        raise ValueError(f"{label} path is not a basename")
    path = root / relative
    if not path.is_file() or path.stat().st_size != checked["bytes"]:
        raise ValueError(f"{label} artifact mismatch: {path}")
    return path, checked


def linked_path(project_root: Path, record: object, label: str) -> Path:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise ValueError(f"missing or malformed {label} record")
    if not valid_sha256(record.get("sha256")):
        raise ValueError(f"invalid {label} SHA-256")
    recorded = Path(record["path"])
    path = recorded if recorded.is_absolute() else project_root / recorded
    if not path.is_file() or file_sha256(path) != record["sha256"]:
        raise ValueError(f"{label} artifact mismatch: {path}")
    return path


def exact_verified_log(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    return sum(line.rstrip("\r") == "s VERIFIED" for line in lines) == 1


def decompressed_identity(zstd: Path, compressed: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    process = subprocess.Popen(
        [str(zstd), "-q", "-d", "-c", str(compressed)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    for block in iter(lambda: process.stdout.read(1 << 23), b""):
        total += len(block)
        digest.update(block)
    _, error = process.communicate()
    if process.returncode:
        raise RuntimeError(
            f"zstd decompression failed for {compressed}: "
            f"{error.decode('utf-8', errors='replace').strip()}"
        )
    return total, digest.hexdigest()


def audit(
    core_manifest_path: Path,
    compressed_manifest_path: Path,
    zstd: Path,
    project_root: Path,
    jobs: int,
) -> dict[str, Any]:
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    for path, label in (
        (core_manifest_path, "core manifest"),
        (compressed_manifest_path, "compressed manifest"),
        (zstd, "zstd executable"),
    ):
        if not path.is_file():
            raise ValueError(f"missing {label}: {path}")

    core = load_document(core_manifest_path, "core manifest")
    compressed = load_document(compressed_manifest_path, "compressed manifest")
    if core.get("schema") != CORE_SCHEMA:
        raise ValueError("unexpected core manifest schema")
    if compressed.get("schema") != COMPRESSED_SCHEMA:
        raise ValueError("unexpected compressed manifest schema")

    proof_path = linked_path(project_root, core.get("proof_manifest"), "proof manifest")
    branch_path = linked_path(
        project_root, core.get("branch_manifest"), "branch manifest"
    )
    checker_path = linked_path(project_root, core.get("checker"), "checker")
    proofs = load_document(proof_path, "proof manifest")
    branches = load_document(branch_path, "branch manifest")
    if proofs.get("schema") != PROOF_SCHEMA:
        raise ValueError("unexpected proof manifest schema")
    if branches.get("schema") not in BRANCH_SCHEMAS:
        raise ValueError("unexpected branch manifest schema")
    proof_branch = proofs.get("branch_manifest")
    if (
        not isinstance(proof_branch, dict)
        or proof_branch.get("sha256") != file_sha256(branch_path)
        or proof_branch.get("schema") != branches.get("schema")
    ):
        raise ValueError("proof manifest does not bind the branch manifest")

    core_link = compressed.get("core_manifest")
    if (
        not isinstance(core_link, dict)
        or core_link.get("schema") != CORE_SCHEMA
        or core_link.get("sha256") != file_sha256(core_manifest_path)
    ):
        raise ValueError("compressed manifest does not bind the core manifest")

    compression = compressed.get("compression")
    if not isinstance(compression, dict) or compression.get("format") != "zstd":
        raise ValueError("invalid compression record")
    if compression.get("executable_sha256") != file_sha256(zstd):
        raise ValueError("zstd executable hash mismatch")
    version = subprocess.run(
        [str(zstd), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout.strip()
    if compression.get("version") != version:
        raise ValueError("zstd version mismatch")

    core_results = core.get("results")
    compressed_results = compressed.get("results")
    proof_results = proofs.get("results")
    branch_results = branches.get("files")
    core_summary = core.get("summary")
    compressed_summary = compressed.get("summary")
    proof_summary = proofs.get("summary")
    if not all(
        isinstance(value, list)
        for value in (core_results, compressed_results, proof_results, branch_results)
    ):
        raise ValueError("one or more manifests lack result lists")
    assert isinstance(core_results, list)
    assert isinstance(compressed_results, list)
    assert isinstance(proof_results, list)
    assert isinstance(branch_results, list)
    if not core_results or not (
        len(core_results)
        == len(compressed_results)
        == len(proof_results)
        == len(branch_results)
    ):
        raise ValueError("manifest result counts disagree")
    if not all(
        isinstance(value, dict)
        for value in (core_summary, compressed_summary, proof_summary)
    ):
        raise ValueError("one or more manifests lack summaries")
    assert isinstance(core_summary, dict)
    assert isinstance(compressed_summary, dict)
    assert isinstance(proof_summary, dict)

    count = len(core_results)
    if (
        core_summary.get("complete_for_listed_formulas") is not True
        or core_summary.get("formulas") != count
        or core_summary.get("verified_unsat") != count
        or compressed_summary.get("complete_for_listed_formulas") is not True
        or compressed_summary.get("formulas") != count
        or proof_summary.get("complete_unsat") is not True
        or proof_summary.get("formulas") != count
        or proof_summary.get("verified_unsat") != count
    ):
        raise ValueError("one or more manifest summaries are incomplete")

    pair_indices = [record.get("pair_index") for record in core_results]
    if len(set(pair_indices)) != count or any(
        pair_indices
        != [record.get("pair_index") for record in records]
        for records in (compressed_results, proof_results, branch_results)
    ):
        raise ValueError("pair-index order or uniqueness mismatch")

    tasks: list[
        tuple[
            int,
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
        ]
    ] = []
    source_bytes = core_bytes = compressed_bytes = 0
    for index, (core_result, compressed_result, proof_result, branch_result) in enumerate(
        zip(core_results, compressed_results, proof_results, branch_results, strict=True)
    ):
        if not all(
            isinstance(value, dict)
            for value in (core_result, compressed_result, proof_result, branch_result)
        ):
            raise ValueError(f"malformed result at index {index}")
        pair_index = int(pair_indices[index])
        if core_result.get("status") != "VERIFIED_UNSAT" or proof_result.get(
            "status"
        ) != "VERIFIED_UNSAT":
            raise ValueError(f"pair {pair_index}: result is not VERIFIED_UNSAT")
        if core_result.get("cnf_sha256") != branch_result.get("sha256") or proof_result.get(
            "cnf", {}
        ).get("sha256") != branch_result.get("sha256"):
            raise ValueError(f"pair {pair_index}: CNF binding mismatch")
        source_record = validate_record(
            core_result.get("source_proof"), f"pair {pair_index} source proof"
        )
        upstream_source = validate_record(
            proof_result.get("proof"), f"pair {pair_index} upstream source proof"
        )
        if any(
            source_record[key] != upstream_source[key]
            for key in ("path", "bytes", "sha256")
        ):
            raise ValueError(f"pair {pair_index}: source proof binding mismatch")

        core_path, core_record = basename_artifact(
            core_manifest_path.parent,
            core_result.get("core_proof"),
            f"pair {pair_index} core proof",
        )
        compressed_path, compressed_record = basename_artifact(
            compressed_manifest_path.parent,
            compressed_result,
            f"pair {pair_index} compressed proof",
        )
        source_log, source_log_record = basename_artifact(
            core_manifest_path.parent,
            core_result.get("source_checker_log"),
            f"pair {pair_index} source checker log",
        )
        core_log, core_log_record = basename_artifact(
            core_manifest_path.parent,
            core_result.get("core_checker_log"),
            f"pair {pair_index} core checker log",
        )
        if compressed_result.get("core_bytes") != core_record["bytes"] or compressed_result.get(
            "core_sha256"
        ) != core_record["sha256"]:
            raise ValueError(f"pair {pair_index}: compressed/core binding mismatch")
        if not isinstance(core_result.get("source_checker_seconds"), (int, float)) or core_result[
            "source_checker_seconds"
        ] < 0:
            raise ValueError(f"pair {pair_index}: invalid source checker duration")
        if not isinstance(core_result.get("core_checker_seconds"), (int, float)) or core_result[
            "core_checker_seconds"
        ] < 0:
            raise ValueError(f"pair {pair_index}: invalid core checker duration")
        source_bytes += int(source_record["bytes"])
        core_bytes += int(core_record["bytes"])
        compressed_bytes += int(compressed_record["bytes"])
        tasks.append(
            (
                pair_index,
                core_path,
                core_record,
                compressed_path,
                compressed_record,
                source_log,
                source_log_record,
                core_log,
                core_log_record,
            )
        )

    if (
        source_bytes != core_summary.get("source_proof_bytes")
        or source_bytes != compressed_summary.get("source_proof_bytes")
        or source_bytes != proof_summary.get("proof_bytes")
        or core_bytes != core_summary.get("core_proof_bytes")
        or core_bytes != compressed_summary.get("core_bytes")
        or compressed_bytes != compressed_summary.get("compressed_bytes")
        or core_summary.get("core_to_source_ratio")
        != round(core_bytes / source_bytes, 9)
        or compressed_summary.get("compressed_to_core_ratio")
        != round(compressed_bytes / core_bytes, 9)
        or compressed_summary.get("compressed_to_source_ratio")
        != round(compressed_bytes / source_bytes, 9)
    ):
        raise ValueError("byte totals or compression ratios disagree")

    def worker(
        task: tuple[
            int,
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
            Path,
            dict[str, Any],
        ]
    ) -> dict[str, object]:
        (
            pair_index,
            core_path,
            core_record,
            compressed_path,
            compressed_record,
            source_log,
            source_log_record,
            core_log,
            core_log_record,
        ) = task
        if file_sha256(core_path) != core_record["sha256"]:
            raise ValueError(f"pair {pair_index}: core proof hash mismatch")
        if file_sha256(compressed_path) != compressed_record["sha256"]:
            raise ValueError(f"pair {pair_index}: compressed proof hash mismatch")
        if file_sha256(source_log) != source_log_record["sha256"]:
            raise ValueError(f"pair {pair_index}: source checker log hash mismatch")
        if file_sha256(core_log) != core_log_record["sha256"]:
            raise ValueError(f"pair {pair_index}: core checker log hash mismatch")
        if not exact_verified_log(source_log) or not exact_verified_log(core_log):
            raise ValueError(f"pair {pair_index}: checker log lacks one exact s VERIFIED")
        decompressed_bytes, decompressed_sha256 = decompressed_identity(
            zstd, compressed_path
        )
        if (
            decompressed_bytes != core_record["bytes"]
            or decompressed_sha256 != core_record["sha256"]
        ):
            raise ValueError(f"pair {pair_index}: decompressed core mismatch")
        return {
            "pair_index": pair_index,
            "core_bytes": core_record["bytes"],
            "core_sha256": core_record["sha256"],
            "compressed_bytes": compressed_record["bytes"],
            "compressed_sha256": compressed_record["sha256"],
            "decompressed_identity": True,
            "source_checker_exact_verified": True,
            "core_checker_exact_verified": True,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        results = list(executor.map(worker, tasks))

    return {
        "schema": AUDIT_SCHEMA,
        "verified": True,
        "core_manifest": file_record(core_manifest_path),
        "compressed_manifest": file_record(compressed_manifest_path),
        "proof_manifest": file_record(proof_path),
        "branch_manifest": file_record(branch_path),
        "checker": file_record(checker_path),
        "zstd": {**file_record(zstd), "version": version},
        "results": results,
        "summary": {
            "formulas": count,
            "source_checker_logs_exact_verified": count,
            "core_checker_logs_exact_verified": count,
            "decompressed_identities": count,
            "source_proof_bytes": source_bytes,
            "core_proof_bytes": core_bytes,
            "compressed_bytes": compressed_bytes,
            "core_to_source_ratio": round(core_bytes / source_bytes, 9),
            "compressed_to_core_ratio": round(compressed_bytes / core_bytes, 9),
            "compressed_to_source_ratio": round(compressed_bytes / source_bytes, 9),
            "complete_for_listed_formulas": True,
        },
    }


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("core_manifest", type=Path)
    parser.add_argument("compressed_manifest", type=Path)
    parser.add_argument("--zstd", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists() or arguments.output.with_suffix(
        arguments.output.suffix + ".tmp"
    ).exists():
        parser.error("refusing to overwrite output or temporary output")
    document = audit(
        arguments.core_manifest,
        arguments.compressed_manifest,
        arguments.zstd,
        arguments.project_root,
        arguments.jobs,
    )
    atomic_json(arguments.output, document)
    print(json.dumps(document["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
