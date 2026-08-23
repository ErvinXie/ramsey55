#!/usr/bin/env python3
"""Summarize a checked sparse gluing sample without extrapolating a theorem."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

BRANCH_SCHEMAS = {
    "ramsey55.r45-gluing-branches.v1",
    "ramsey55.r45-gluing-branches.v2",
}
PROOF_SCHEMA = "ramsey55.r45-gluing-proofs.v1"
SCHEMA = "ramsey55.r45-gluing-sample-summary.v1"
TIME_FIELDS = {
    "user_seconds": r"^\s*User time \(seconds\):\s*(\S+)\s*$",
    "elapsed": r"^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)\s*$",
    "max_rss_kbytes": r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$",
    "exit_status": r"^\s*Exit status:\s*(\d+)\s*$",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_path(root: Path, record: dict[str, object]) -> Path:
    path = root / str(record["path"])
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or file_sha256(path) != record.get("sha256")
    ):
        raise ValueError(f"artifact mismatch: {path}")
    return path


def elapsed_seconds(raw: str) -> float:
    fields = [float(field) for field in raw.split(":")]
    if len(fields) == 2:
        minutes, seconds = fields
        return 60 * minutes + seconds
    if len(fields) == 3:
        hours, minutes, seconds = fields
        return 3600 * hours + 60 * minutes + seconds
    raise ValueError(f"invalid GNU time elapsed value: {raw}")


def time_record(path: Path) -> dict[str, float | int]:
    text = path.read_text(encoding="utf-8")
    matches: dict[str, str] = {}
    for name, pattern in TIME_FIELDS.items():
        found = re.findall(pattern, text, flags=re.MULTILINE)
        if len(found) != 1:
            raise ValueError(f"{path}: expected exactly one {name} field")
        matches[name] = found[0]
    return {
        "user_seconds": float(matches["user_seconds"]),
        "wall_seconds": elapsed_seconds(matches["elapsed"]),
        "max_rss_kbytes": int(matches["max_rss_kbytes"]),
        "exit_status": int(matches["exit_status"]),
    }


def distribution(values: list[float | int]) -> dict[str, float | int]:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    ordered = sorted(values)

    def nearest_rank(percent: int) -> float | int:
        return ordered[math.ceil(percent * len(ordered) / 100) - 1]

    total = sum(values)
    return {
        "count": len(values),
        "sum": total,
        "mean": round(total / len(values), 6),
        "min": ordered[0],
        "p50_nearest_rank": nearest_rank(50),
        "p90_nearest_rank": nearest_rank(90),
        "p95_nearest_rank": nearest_rank(95),
        "p99_nearest_rank": nearest_rank(99),
        "max": ordered[-1],
    }


def summarize(
    proof_manifest_path: Path,
    branch_manifest_path: Path,
    proof_dir: Path,
) -> dict[str, object]:
    proofs = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    branches = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    if (
        proofs.get("schema") != PROOF_SCHEMA
        or branches.get("schema") not in BRANCH_SCHEMAS
    ):
        raise ValueError("unexpected proof or branch manifest schema")
    link = proofs.get("branch_manifest")
    if (
        not isinstance(link, dict)
        or link.get("sha256") != file_sha256(branch_manifest_path)
        or link.get("schema") != branches.get("schema")
    ):
        raise ValueError("proof manifest does not bind branch manifest")
    branch_records = branches.get("files")
    proof_records = proofs.get("results")
    if (
        not isinstance(branch_records, list)
        or not isinstance(proof_records, list)
        or [record.get("pair_index") for record in branch_records]
        != [record.get("pair_index") for record in proof_records]
        or proofs.get("summary", {}).get("complete_unsat") is not True
    ):
        raise ValueError("checked sample coverage is incomplete")

    results = []
    for record in proof_records:
        proof = checked_path(proof_dir, record["proof"])
        solver_time = time_record(checked_path(proof_dir, record["solver_time"]))
        checker_time = time_record(checked_path(proof_dir, record["checker_time"]))
        if solver_time["exit_status"] != 20 or checker_time["exit_status"] != 0:
            raise ValueError(f"pair {record['pair_index']}: incorrect exit status")
        results.append(
            {
                "pair_index": record["pair_index"],
                "proof_bytes": proof.stat().st_size,
                "solver": solver_time,
                "checker": checker_time,
            }
        )

    def values(field: str, phase: str | None = None) -> list[float | int]:
        if phase is None:
            return [int(record[field]) for record in results]
        return [record[phase][field] for record in results]

    return {
        "schema": SCHEMA,
        "claim": "checked sparse-sample measurements only; no unsampled UNSAT claim",
        "branch_manifest": {
            "path": str(branch_manifest_path),
            "sha256": file_sha256(branch_manifest_path),
        },
        "proof_manifest": {
            "path": str(proof_manifest_path),
            "sha256": file_sha256(proof_manifest_path),
        },
        "fixed_star_degree": branches["fixed_star_degree"],
        "sample_formulas": len(results),
        "total_pairs": branches["total_pairs"],
        "quantile_definition": "nearest rank",
        "distribution": {
            "proof_bytes": distribution(values("proof_bytes")),
            "solver_user_seconds": distribution(values("user_seconds", "solver")),
            "solver_wall_seconds": distribution(values("wall_seconds", "solver")),
            "checker_user_seconds": distribution(values("user_seconds", "checker")),
            "checker_wall_seconds": distribution(values("wall_seconds", "checker")),
            "solver_max_rss_kbytes": distribution(values("max_rss_kbytes", "solver")),
            "checker_max_rss_kbytes": distribution(
                values("max_rss_kbytes", "checker")
            ),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("branch_manifest", type=Path)
    parser.add_argument("proof_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    document = summarize(
        arguments.proof_manifest, arguments.branch_manifest, arguments.proof_dir
    )
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {arguments.output}")


if __name__ == "__main__":
    main()
