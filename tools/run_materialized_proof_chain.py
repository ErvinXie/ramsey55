#!/usr/bin/env python3
"""Resume a certified materialized-proof frontier through binary refinements."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def run_logged(command: list[str], log: Path) -> int:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("formula", type=Path)
    parser.add_argument("seed_manifest", type=Path)
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--refiner", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--first-round", type=int, default=0)
    parser.add_argument("--max-rounds", type=int, default=100)
    parser.add_argument("--solver-argument", action="append", default=[])
    arguments = parser.parse_args()
    if (
        arguments.jobs <= 0
        or arguments.seconds <= 0
        or arguments.first_round < 0
        or arguments.max_rounds <= 0
    ):
        parser.error("invalid jobs, seconds, or round bound")
    for path in (
        arguments.formula,
        arguments.seed_manifest,
        arguments.refiner,
        arguments.solver,
        arguments.checker,
    ):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")

    root = Path(__file__).resolve().parents[1]
    tools = root / "tools"
    arguments.workdir.mkdir(parents=True, exist_ok=True)
    state_path = arguments.workdir / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        round_number = int(state["round"])
        current_manifest = Path(state["current_manifest"])
    else:
        round_number = arguments.first_round
        current_manifest = arguments.seed_manifest
        state = {
            "schema": "ramsey55.materialized-proof-chain.v1",
            "round": round_number,
            "current_manifest": str(current_manifest),
            "complete": False,
        }
        atomic_json(state_path, state)

    final_round = round_number + arguments.max_rounds
    while round_number < final_round:
        proof_document = json.loads(current_manifest.read_text(encoding="utf-8"))
        summary = proof_document["summary"]
        if int(summary["sat"]):
            raise RuntimeError(f"SAT result requires investigation: {current_manifest}")
        if bool(summary["complete_unsat"]):
            state.update(complete=True, current_manifest=str(current_manifest))
            atomic_json(state_path, state)
            print(f"complete at round {round_number}", flush=True)
            return 20

        prefix = arguments.workdir / f"r{round_number:04d}"
        parents = prefix.with_name(prefix.name + "-parents.icnf")
        frontier_manifest = prefix.with_name(prefix.name + "-parents.json")
        children = prefix.with_name(prefix.name + "-children.icnf")
        refine_results = prefix.with_name(prefix.name + "-refine.tsv")
        refine_log = prefix.with_name(prefix.name + "-refine.log")
        refinement_manifest = prefix.with_name(prefix.name + "-refinement.json")
        proof_directory = prefix.with_name(prefix.name + "-proofs")
        proof_log = prefix.with_name(prefix.name + "-proofs.log")
        for path in (
            parents,
            frontier_manifest,
            children,
            refine_results,
            refine_log,
            refinement_manifest,
            proof_directory,
            proof_log,
        ):
            if path.exists():
                raise RuntimeError(f"refusing to overwrite round artifact {path}")

        audit_status = run_logged(
            [
                sys.executable,
                str(tools / "audit_materialized_cube_proofs.py"),
                str(current_manifest),
                "--checker",
                str(arguments.checker),
                "--allow-partial",
                "--jobs",
                str(arguments.jobs),
            ],
            prefix.with_name(prefix.name + "-seed-audit.log"),
        )
        if audit_status:
            raise RuntimeError(f"seed proof audit failed at round {round_number}")
        export_status = run_logged(
            [
                sys.executable,
                str(tools / "export_materialized_proof_frontier.py"),
                str(current_manifest),
                str(parents),
                "--manifest",
                str(frontier_manifest),
            ],
            prefix.with_name(prefix.name + "-parents.log"),
        )
        if export_status:
            raise RuntimeError(f"frontier export failed at round {round_number}")
        unknown = int(
            json.loads(frontier_manifest.read_text(encoding="utf-8"))[
                "output_cube_count"
            ]
        )
        if unknown <= 0:
            raise RuntimeError("incomplete proof manifest exported no UNKNOWN cubes")

        refine_status = run_logged(
            [
                str(arguments.refiner),
                str(arguments.formula),
                str(parents),
                str(min(arguments.jobs, unknown)),
                str(children),
                str(refine_results),
            ],
            refine_log,
        )
        if refine_status == 10:
            raise RuntimeError(f"refiner found SAT at round {round_number}")
        if refine_status:
            raise RuntimeError(f"refiner failed at round {round_number}")
        refinement_status = run_logged(
            [
                sys.executable,
                str(tools / "audit_binary_cube_refinement.py"),
                str(parents),
                str(children),
                str(refine_results),
                "--manifest",
                str(refinement_manifest),
            ],
            prefix.with_name(prefix.name + "-refinement-audit.log"),
        )
        if refinement_status:
            raise RuntimeError(f"refinement audit failed at round {round_number}")

        prove_command = [
            sys.executable,
            str(tools / "prove_materialized_cubes.py"),
            str(arguments.formula),
            str(children),
            str(proof_directory),
            "--solver",
            str(arguments.solver),
            "--checker",
            str(arguments.checker),
            "--jobs",
            str(min(arguments.jobs, 2 * unknown)),
            "--seconds",
            str(arguments.seconds),
        ]
        for option in arguments.solver_argument:
            prove_command.append(f"--solver-argument={option}")
        proof_status = run_logged(prove_command, proof_log)
        if proof_status == 10:
            raise RuntimeError(f"solver found SAT at round {round_number}")
        if proof_status not in (0, 20):
            raise RuntimeError(f"proof producer failed at round {round_number}")
        current_manifest = proof_directory / "manifest.json"
        proof_audit_command = [
            sys.executable,
            str(tools / "audit_materialized_cube_proofs.py"),
            str(current_manifest),
            "--checker",
            str(arguments.checker),
        ]
        if proof_status == 0:
            proof_audit_command.append("--allow-partial")
        proof_audit_command.extend(("--jobs", str(arguments.jobs)))
        proof_audit_status = run_logged(
            proof_audit_command,
            prefix.with_name(prefix.name + "-proofs-audit.log"),
        )
        if proof_audit_status:
            raise RuntimeError(f"new proof audit failed at round {round_number}")
        round_number += 1
        state.update(
            round=round_number,
            current_manifest=str(current_manifest),
            complete=proof_status == 20,
        )
        atomic_json(state_path, state)
        next_summary = json.loads(current_manifest.read_text(encoding="utf-8"))[
            "summary"
        ]
        print(
            f"round {round_number} parents={unknown} "
            f"verified={next_summary['unsat_verified']} "
            f"unknown={next_summary['unknown']}",
            flush=True,
        )
        if proof_status == 20:
            print(f"complete at round {round_number}", flush=True)
            return 20
    print(f"round limit reached at {round_number}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
