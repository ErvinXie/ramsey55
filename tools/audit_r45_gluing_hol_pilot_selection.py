#!/usr/bin/env python3
"""Audit the choice of a HOL pilot from a checked R(4,5,24) sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BRANCH_SCHEMAS = {
    "ramsey55.r45-gluing-branches.v1",
    "ramsey55.r45-gluing-branches.v2",
}
PROOF_SCHEMA = "ramsey55.r45-gluing-proofs.v1"
SCHEMA = "ramsey55.r45-gluing-hol-pilot-selection-audit.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def read_problem_list(path: Path) -> list[tuple[int, int]]:
    pairs = []
    with path.open(encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            fields = line.split()
            if len(fields) != 2:
                raise ValueError(
                    f"{path}:{line_number}: expected exactly two integer fields"
                )
            try:
                pair = (int(fields[0]), int(fields[1]))
            except ValueError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid problem pair"
                ) from error
            if pair[0] <= 0 or pair[1] <= 0:
                raise ValueError(f"{path}:{line_number}: nonpositive problem code")
            pairs.append(pair)
    if not pairs:
        raise ValueError(f"empty problem list: {path}")
    return pairs


def checked_proof(
    proof_directory: Path, record: dict[str, object]
) -> dict[str, object]:
    relative = Path(str(record.get("path", "")))
    if relative.is_absolute() or relative.name != str(relative):
        raise ValueError(f"proof path is not a basename: {relative}")
    path = proof_directory / relative
    expected_bytes = record.get("bytes")
    expected_sha256 = record.get("sha256")
    if (
        not path.is_file()
        or not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or path.stat().st_size != expected_bytes
        or not isinstance(expected_sha256, str)
        or file_sha256(path) != expected_sha256
    ):
        raise ValueError(f"proof artifact mismatch: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": expected_bytes,
        "sha256": expected_sha256,
    }


def audit(
    proof_manifest_path: Path,
    branch_manifest_path: Path,
    proof_directory: Path,
    full_problem_list_path: Path,
    pilot_problem_list_path: Path,
) -> dict[str, object]:
    proofs = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    branches = json.loads(branch_manifest_path.read_text(encoding="utf-8"))
    branch_schema = branches.get("schema")
    if proofs.get("schema") != PROOF_SCHEMA or branch_schema not in BRANCH_SCHEMAS:
        raise ValueError("unexpected proof or branch manifest schema")

    branch_manifest_sha256 = file_sha256(branch_manifest_path)
    link = proofs.get("branch_manifest")
    if (
        not isinstance(link, dict)
        or link.get("schema") != branch_schema
        or link.get("sha256") != branch_manifest_sha256
    ):
        raise ValueError("proof manifest does not bind the branch manifest")

    branch_records = branches.get("files")
    proof_records = proofs.get("results")
    pair_indices = branches.get("pair_indices")
    if (
        not isinstance(branch_records, list)
        or not branch_records
        or not isinstance(proof_records, list)
        or not isinstance(pair_indices, list)
    ):
        raise ValueError("missing sample records")
    branch_indices = [record.get("pair_index") for record in branch_records]
    proof_indices = [record.get("pair_index") for record in proof_records]
    if (
        branch_indices != pair_indices
        or proof_indices != branch_indices
        or len(branch_indices) != len(set(branch_indices))
    ):
        raise ValueError("sample pair indices are not exact, unique, and ordered")

    summary = proofs.get("summary")
    proof_bytes = []
    checked_artifacts: dict[int, dict[str, object]] = {}
    for record in proof_records:
        pair_index = record.get("pair_index")
        if not isinstance(pair_index, int) or record.get("status") != "VERIFIED_UNSAT":
            raise ValueError("sample contains a non-verified proof record")
        proof = record.get("proof")
        if not isinstance(proof, dict):
            raise ValueError(f"pair {pair_index}: missing proof artifact")
        checked = checked_proof(proof_directory, proof)
        proof_bytes.append(int(checked["bytes"]))
        checked_artifacts[pair_index] = checked
    if summary != {
        "formulas": len(proof_records),
        "verified_unsat": len(proof_records),
        "complete_unsat": True,
        "proof_bytes": sum(proof_bytes),
    }:
        raise ValueError("proof summary is not an exact complete-sample summary")

    total_pairs = branches.get("total_pairs")
    if not isinstance(total_pairs, int) or total_pairs <= max(branch_indices):
        raise ValueError("invalid total pair count")
    full_pairs = read_problem_list(full_problem_list_path)
    if len(full_pairs) != total_pairs:
        raise ValueError("full problem list length does not equal total_pairs")
    pilot_pairs = read_problem_list(pilot_problem_list_path)
    if len(pilot_pairs) != 1:
        raise ValueError("pilot problem list must contain exactly one pair")

    # A lower global pair index breaks a byte-count tie deterministically.
    ranked = sorted(
        zip(proof_records, branch_records, strict=True),
        key=lambda item: (-int(item[0]["proof"]["bytes"]), item[0]["pair_index"]),
    )
    selected_proof, selected_branch = ranked[0]
    selected_index = int(selected_proof["pair_index"])
    selected_pair = (
        int(selected_branch.get("left_code", 0)),
        int(selected_branch.get("right_code", 0)),
    )
    if min(selected_pair) <= 0:
        raise ValueError("selected branch has invalid generalized-graph codes")
    if full_pairs[selected_index] != selected_pair:
        raise ValueError("selected branch does not match its full problem-list row")
    if pilot_pairs[0] != selected_pair:
        raise ValueError("pilot problem list does not contain the selected branch")

    runner_up = None
    if len(ranked) > 1:
        second_proof, _ = ranked[1]
        runner_up = {
            "pair_index": second_proof["pair_index"],
            "proof_bytes": second_proof["proof"]["bytes"],
        }

    return {
        "schema": SCHEMA,
        "claim": (
            "selection audit for one HOL pilot from a checked sparse sample; "
            "no unsampled UNSAT claim"
        ),
        "verified": True,
        "inputs": {
            "proof_manifest": artifact(proof_manifest_path),
            "branch_manifest": artifact(branch_manifest_path),
            "proof_directory": str(proof_directory.resolve()),
            "full_problem_list": artifact(full_problem_list_path),
            "pilot_problem_list": artifact(pilot_problem_list_path),
        },
        "sample": {
            "fixed_star_degree": branches.get("fixed_star_degree"),
            "formulas": len(proof_records),
            "total_pairs": total_pairs,
            "verified_unsat": len(proof_records),
            "raw_proof_bytes": sum(proof_bytes),
            "raw_proof_artifacts_rehashed": len(checked_artifacts),
        },
        "selection": {
            "criterion": "maximum raw proof bytes; least pair_index breaks ties",
            "rank": 1,
            "pair_index_zero_based": selected_index,
            "full_problem_list_line_one_based": selected_index + 1,
            "left_code": selected_pair[0],
            "right_code": selected_pair[1],
            "proof": checked_artifacts[selected_index],
            "runner_up": runner_up,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_manifest", type=Path)
    parser.add_argument("branch_manifest", type=Path)
    parser.add_argument("proof_directory", type=Path)
    parser.add_argument("full_problem_list", type=Path)
    parser.add_argument("pilot_problem_list", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    document = audit(
        arguments.proof_manifest,
        arguments.branch_manifest,
        arguments.proof_directory,
        arguments.full_problem_list,
        arguments.pilot_problem_list,
    )
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "audited HOL pilot selection: "
        f"pair_index={document['selection']['pair_index_zero_based']}; "
        f"proof_bytes={document['selection']['proof']['bytes']}"
    )


if __name__ == "__main__":
    main()
