#!/usr/bin/env python3
"""Independently replay a materialized-cube proof manifest."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

if __package__:
    from tools.prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from tools.solve_external_cubes import read_cnf, read_cubes, render_cnf
else:
    from prove_materialized_cubes import SCHEMA, cube_sha256, file_sha256
    from solve_external_cubes import read_cnf, read_cubes, render_cnf


def artifact(root: Path, name: object) -> Path:
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError(f"invalid artifact name {name!r}")
    return root / name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    document: dict[str, Any] = json.loads(
        arguments.manifest.read_text(encoding="utf-8")
    )
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected materialized-proof schema")
    if not arguments.checker.is_file():
        parser.error(f"checker does not exist: {arguments.checker}")
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")

    formula_entry = document["formula"]
    cubes_entry = document["cubes"]
    cnf = Path(formula_entry["path"])
    cubes_path = Path(cubes_entry["path"])
    if file_sha256(cnf) != formula_entry["sha256"]:
        raise ValueError("formula hash mismatch")
    if file_sha256(cubes_path) != cubes_entry["sha256"]:
        raise ValueError("cube-file hash mismatch")
    before, after, variables, clauses = read_cnf(cnf)
    if (variables, clauses) != (
        int(formula_entry["variables"]),
        int(formula_entry["clauses"]),
    ):
        raise ValueError("formula shape mismatch")
    cubes = read_cubes(cubes_path, variables)
    results = document["results"]
    if len(cubes) != int(cubes_entry["count"]) or len(results) != len(cubes):
        raise ValueError("cube/result count mismatch")
    statuses = [None if result is None else int(result["status"]) for result in results]
    expected_summary = {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": statuses.count(10),
        "complete_unsat": all(status == 20 for status in statuses),
    }
    if document.get("summary") != expected_summary:
        raise ValueError("manifest summary mismatch")

    root = arguments.manifest.parent
    verified = 0
    unknown = statuses.count(0)
    with tempfile.TemporaryDirectory(prefix="materialized-proof-audit-") as raw:
        temporary = Path(raw)

        def check(item: tuple[int, list[int], dict[str, Any] | None]) -> int:
            index, cube, result = item
            if result is None or int(result["index"]) != index:
                raise ValueError(f"missing or misindexed result {index}")
            if result["cube"] != cube or result["cube_sha256"] != cube_sha256(cube):
                raise ValueError(f"cube binding mismatch at index {index}")
            if float(result["seconds"]) < 0:
                raise ValueError(f"negative solve time at cube {index}")
            augmented = temporary / f"cube-{index:06d}.cnf"
            augmented.write_text(
                render_cnf(before, after, variables, clauses, cube), encoding="ascii"
            )
            if file_sha256(augmented) != result["augmented_cnf_sha256"]:
                raise ValueError(f"augmented CNF hash mismatch at cube {index}")
            status = int(result["status"])
            if status == 10:
                raise ValueError(f"SAT result at cube {index} requires investigation")
            if status == 0:
                augmented.unlink()
                return 0
            if status != 20:
                raise ValueError(f"invalid status {status} at cube {index}")
            proof = artifact(root, result["proof"])
            checker_log = artifact(root, result["checker_log"])
            if proof.stat().st_size != int(result["proof_bytes"]):
                raise ValueError(f"proof size mismatch at cube {index}")
            if file_sha256(proof) != result["proof_sha256"]:
                raise ValueError(f"proof hash mismatch at cube {index}")
            if file_sha256(checker_log) != result["checker_log_sha256"]:
                raise ValueError(f"producer checker-log hash mismatch at cube {index}")
            checked = subprocess.run(
                [str(arguments.checker), str(augmented), str(proof)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if checked.returncode or "s VERIFIED" not in checked.stdout:
                raise RuntimeError(f"checker rejected proof at cube {index}")
            augmented.unlink()
            return 20

        work = (
            (index, cube, result)
            for index, (cube, result) in enumerate(zip(cubes, results, strict=True))
        )
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(arguments.jobs, len(cubes))
        ) as executor:
            for completed, status in enumerate(executor.map(check, work), start=1):
                verified += status == 20
                if completed == len(cubes) or completed % 256 == 0:
                    print(
                        f"audited {completed}/{len(cubes)} verified={verified}",
                        flush=True,
                    )
    if unknown and not arguments.allow_partial:
        raise ValueError(f"manifest is incomplete: {unknown} UNKNOWN cubes")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "cubes": len(cubes),
                "verified": verified,
                "unknown": unknown,
                "complete_unsat": verified == len(cubes),
                "checker_sha256": file_sha256(arguments.checker),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
