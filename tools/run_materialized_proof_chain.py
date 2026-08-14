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


def double_unknown_cubes(
    cubes: list[list[int]], results: list[dict[str, object]]
) -> list[list[int]]:
    if len(cubes) != len(results) or len(cubes) % 2:
        raise ValueError("binary refinement did not produce paired results")
    retry: list[list[int]] = []
    for offset in range(0, len(cubes), 2):
        pair = results[offset : offset + 2]
        statuses = [int(row["status"]) for row in pair]
        if 10 in statuses:
            raise RuntimeError("SAT result requires investigation")
        if any(status not in (0, 20) for status in statuses):
            raise ValueError("invalid materialized-proof status")
        if statuses == [0, 0]:
            retry.extend(cubes[offset : offset + 2])
    return retry


def write_icnf(path: Path, cubes: list[list[int]]) -> None:
    path.write_text(
        "".join(f"a {' '.join(map(str, cube))} 0\n" for cube in cubes),
        encoding="ascii",
    )


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
    parser.add_argument(
        "--quick-seconds",
        type=float,
        default=0.0,
        help=(
            "optional first-pass budget; only sibling pairs that both remain "
            "UNKNOWN are retried with --seconds"
        ),
    )
    parser.add_argument("--first-round", type=int, default=0)
    parser.add_argument("--max-rounds", type=int, default=100)
    parser.add_argument("--solver-argument", action="append", default=[])
    parser.add_argument(
        "--fallback-solver",
        type=Path,
        help=(
            "optional second solver for sibling pairs that remain jointly "
            "UNKNOWN after the normal staged retry"
        ),
    )
    parser.add_argument("--fallback-seconds", type=float, default=0.0)
    parser.add_argument("--fallback-solver-argument", action="append", default=[])
    parser.add_argument("--compact-proof", action="store_true")
    parser.add_argument(
        "--scratch-directory",
        type=Path,
        help="pass a transient proof/CNF directory to the materialized producer",
    )
    arguments = parser.parse_args()
    if (
        arguments.jobs <= 0
        or arguments.seconds <= 0
        or arguments.quick_seconds < 0
        or arguments.quick_seconds >= arguments.seconds
        or arguments.fallback_seconds < 0
        or arguments.first_round < 0
        or arguments.max_rounds <= 0
    ):
        parser.error("invalid jobs, seconds, quick-seconds, or round bound")
    if arguments.fallback_solver is None:
        if arguments.fallback_seconds or arguments.fallback_solver_argument:
            parser.error("fallback options require --fallback-solver")
    elif arguments.fallback_seconds <= 0 or arguments.quick_seconds <= 0:
        parser.error(
            "--fallback-solver requires positive --fallback-seconds and "
            "--quick-seconds"
        )
    for path in (
        arguments.formula,
        arguments.seed_manifest,
        arguments.refiner,
        arguments.solver,
        arguments.checker,
    ):
        if not path.is_file():
            parser.error(f"required file does not exist: {path}")
    if (
        arguments.fallback_solver is not None
        and not arguments.fallback_solver.is_file()
    ):
        parser.error(f"required file does not exist: {arguments.fallback_solver}")
    if (
        arguments.scratch_directory is not None
        and not arguments.scratch_directory.is_dir()
    ):
        parser.error(f"scratch directory does not exist: {arguments.scratch_directory}")

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
        quick_directory = prefix.with_name(prefix.name + "-quick-proofs")
        quick_log = prefix.with_name(prefix.name + "-quick-proofs.log")
        quick_audit_log = prefix.with_name(prefix.name + "-quick-proofs-audit.log")
        retry_cubes_path = prefix.with_name(prefix.name + "-retry.icnf")
        retry_directory = prefix.with_name(prefix.name + "-retry-proofs")
        retry_log = prefix.with_name(prefix.name + "-retry-proofs.log")
        retry_audit_log = prefix.with_name(prefix.name + "-retry-proofs-audit.log")
        compose_log = prefix.with_name(prefix.name + "-compose.log")
        primary_directory = prefix.with_name(prefix.name + "-primary-proofs")
        fallback_cubes_path = prefix.with_name(prefix.name + "-fallback.icnf")
        fallback_directory = prefix.with_name(prefix.name + "-fallback-proofs")
        fallback_log = prefix.with_name(prefix.name + "-fallback-proofs.log")
        fallback_audit_log = prefix.with_name(
            prefix.name + "-fallback-proofs-audit.log"
        )
        fallback_compose_log = prefix.with_name(
            prefix.name + "-fallback-compose.log"
        )
        for path in (
            parents,
            frontier_manifest,
            children,
            refine_results,
            refine_log,
            refinement_manifest,
            proof_directory,
            proof_log,
            quick_directory,
            quick_log,
            quick_audit_log,
            retry_cubes_path,
            retry_directory,
            retry_log,
            retry_audit_log,
            compose_log,
            primary_directory,
            fallback_cubes_path,
            fallback_directory,
            fallback_log,
            fallback_audit_log,
            fallback_compose_log,
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

        staged = arguments.quick_seconds > 0
        first_proof_directory = quick_directory if staged else proof_directory
        first_proof_log = quick_log if staged else proof_log
        first_seconds = arguments.quick_seconds if staged else arguments.seconds
        prove_command = [
            sys.executable,
            str(tools / "prove_materialized_cubes.py"),
            str(arguments.formula),
            str(children),
            str(first_proof_directory),
            "--solver",
            str(arguments.solver),
            "--checker",
            str(arguments.checker),
            "--jobs",
            str(min(arguments.jobs, 2 * unknown)),
            "--seconds",
            str(first_seconds),
        ]
        for option in arguments.solver_argument:
            prove_command.append(f"--solver-argument={option}")
        if arguments.compact_proof:
            prove_command.append("--compact-proof")
        if arguments.scratch_directory is not None:
            prove_command.extend(
                ("--scratch-directory", str(arguments.scratch_directory))
            )
        proof_status = run_logged(prove_command, first_proof_log)
        if proof_status == 10:
            raise RuntimeError(f"solver found SAT at round {round_number}")
        if proof_status not in (0, 20):
            raise RuntimeError(f"proof producer failed at round {round_number}")
        current_manifest = first_proof_directory / "manifest.json"
        if staged:
            quick_audit_status = run_logged(
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
                quick_audit_log,
            )
            if quick_audit_status:
                raise RuntimeError(f"quick proof audit failed at round {round_number}")
            quick_document = json.loads(current_manifest.read_text(encoding="utf-8"))
            quick_results = quick_document["results"]
            child_cubes = [row["cube"] for row in quick_results]
            retry_cubes = double_unknown_cubes(child_cubes, quick_results)
            staged_directory = (
                primary_directory
                if arguments.fallback_solver is not None
                else proof_directory
            )
            if retry_cubes:
                write_icnf(retry_cubes_path, retry_cubes)
                retry_command = [
                    sys.executable,
                    str(tools / "prove_materialized_cubes.py"),
                    str(arguments.formula),
                    str(retry_cubes_path),
                    str(retry_directory),
                    "--solver",
                    str(arguments.solver),
                    "--checker",
                    str(arguments.checker),
                    "--jobs",
                    str(min(arguments.jobs, len(retry_cubes))),
                    "--seconds",
                    str(arguments.seconds),
                ]
                for option in arguments.solver_argument:
                    retry_command.append(f"--solver-argument={option}")
                if arguments.compact_proof:
                    retry_command.append("--compact-proof")
                if arguments.scratch_directory is not None:
                    retry_command.extend(
                        ("--scratch-directory", str(arguments.scratch_directory))
                    )
                retry_status = run_logged(retry_command, retry_log)
                if retry_status == 10:
                    raise RuntimeError(f"retry solver found SAT at round {round_number}")
                if retry_status not in (0, 20):
                    raise RuntimeError(f"retry proof producer failed at round {round_number}")
                retry_manifest = retry_directory / "manifest.json"
                retry_audit_command = [
                    sys.executable,
                    str(tools / "audit_materialized_cube_proofs.py"),
                    str(retry_manifest),
                    "--checker",
                    str(arguments.checker),
                ]
                if retry_status == 0:
                    retry_audit_command.append("--allow-partial")
                retry_audit_command.extend(("--jobs", str(arguments.jobs)))
                retry_audit_status = run_logged(
                    retry_audit_command, retry_audit_log
                )
                if retry_audit_status:
                    raise RuntimeError(f"retry proof audit failed at round {round_number}")
                compose_status = run_logged(
                    [
                        sys.executable,
                        str(tools / "compose_materialized_cube_proofs.py"),
                        str(current_manifest),
                        str(retry_manifest),
                        str(staged_directory),
                    ],
                    compose_log,
                )
                if compose_status:
                    raise RuntimeError(f"proof composition failed at round {round_number}")
            else:
                quick_directory.replace(staged_directory)
            current_manifest = staged_directory / "manifest.json"
            if arguments.fallback_solver is not None:
                staged_document = json.loads(
                    current_manifest.read_text(encoding="utf-8")
                )
                staged_results = staged_document["results"]
                fallback_cubes = double_unknown_cubes(child_cubes, staged_results)
                if fallback_cubes:
                    write_icnf(fallback_cubes_path, fallback_cubes)
                    fallback_command = [
                        sys.executable,
                        str(tools / "prove_materialized_cubes.py"),
                        str(arguments.formula),
                        str(fallback_cubes_path),
                        str(fallback_directory),
                        "--solver",
                        str(arguments.fallback_solver),
                        "--checker",
                        str(arguments.checker),
                        "--jobs",
                        str(min(arguments.jobs, len(fallback_cubes))),
                        "--seconds",
                        str(arguments.fallback_seconds),
                    ]
                    for option in arguments.fallback_solver_argument:
                        fallback_command.append(f"--solver-argument={option}")
                    if arguments.compact_proof:
                        fallback_command.append("--compact-proof")
                    if arguments.scratch_directory is not None:
                        fallback_command.extend(
                            (
                                "--scratch-directory",
                                str(arguments.scratch_directory),
                            )
                        )
                    fallback_status = run_logged(fallback_command, fallback_log)
                    if fallback_status == 10:
                        raise RuntimeError(
                            f"fallback solver found SAT at round {round_number}"
                        )
                    if fallback_status not in (0, 20):
                        raise RuntimeError(
                            f"fallback proof producer failed at round {round_number}"
                        )
                    fallback_manifest = fallback_directory / "manifest.json"
                    fallback_audit_command = [
                        sys.executable,
                        str(tools / "audit_materialized_cube_proofs.py"),
                        str(fallback_manifest),
                        "--checker",
                        str(arguments.checker),
                    ]
                    if fallback_status == 0:
                        fallback_audit_command.append("--allow-partial")
                    fallback_audit_command.extend(("--jobs", str(arguments.jobs)))
                    fallback_audit_status = run_logged(
                        fallback_audit_command, fallback_audit_log
                    )
                    if fallback_audit_status:
                        raise RuntimeError(
                            f"fallback proof audit failed at round {round_number}"
                        )
                    fallback_compose_status = run_logged(
                        [
                            sys.executable,
                            str(tools / "compose_materialized_cube_proofs.py"),
                            str(current_manifest),
                            str(fallback_manifest),
                            str(proof_directory),
                        ],
                        fallback_compose_log,
                    )
                    if fallback_compose_status:
                        raise RuntimeError(
                            f"fallback proof composition failed at round {round_number}"
                        )
                else:
                    primary_directory.replace(proof_directory)
            current_manifest = proof_directory / "manifest.json"
            final_document = json.loads(current_manifest.read_text(encoding="utf-8"))
            proof_status = 20 if final_document["summary"]["complete_unsat"] else 0
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
