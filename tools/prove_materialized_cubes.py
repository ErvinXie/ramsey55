#!/usr/bin/env python3
"""Produce independently checked DRAT proofs for materialized CNF cubes."""

from __future__ import annotations

import argparse
import concurrent.futures
import errno
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

if __package__:
    from tools.solve_external_cubes import parse_model, read_cnf, read_cubes, render_cnf
else:
    from solve_external_cubes import parse_model, read_cnf, read_cubes, render_cnf


SCHEMA = "ramsey55.materialized-cube-proofs.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cube_sha256(cube: list[int]) -> str:
    return hashlib.sha256(
        (" ".join(map(str, cube)) + " 0\n").encode("ascii")
    ).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def publish_proof(source: Path, destination: Path) -> None:
    """Atomically publish a checked proof, including across filesystems."""

    part = destination.with_name(f".{destination.name}.publish.part")
    if destination.exists() or part.exists():
        raise RuntimeError(f"refusing to overwrite proof artifact {destination}")
    try:
        source.replace(destination)
        return
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
    try:
        shutil.copyfile(source, part)
        with part.open("rb") as stream:
            os.fsync(stream.fileno())
        part.replace(destination)
        source.unlink()
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def completed_results(
    executor: concurrent.futures.Executor,
    function: Any,
    items: Any,
) -> Any:
    """Yield successful results as workers finish, then report any failure.

    Waiting in input order can hide already published proofs behind one slow
    earlier cube and prevents the progress manifest from recording them.  Keep
    collecting successful futures even if another worker fails so every
    safely published artifact can be checkpointed before the error escapes.
    """

    futures = [executor.submit(function, item) for item in items]
    failure: Exception | None = None
    for future in concurrent.futures.as_completed(futures):
        try:
            yield future.result()
        except Exception as error:
            if failure is None:
                failure = error
    if failure is not None:
        raise failure


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=16,
        help="atomically rewrite progress after this many ordered results",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        help="per-cube wall limit; zero means unlimited",
    )
    parser.add_argument(
        "--solver-argument",
        action="append",
        default=[],
        help="repeat for solver options; use --solver-argument=--unsat",
    )
    parser.add_argument(
        "--compact-proof",
        action="store_true",
        help="retain a smaller independently replayed binary DRAT core when possible",
    )
    parser.add_argument(
        "--scratch-directory",
        type=Path,
        help="place transient CNFs and raw/compact proof candidates here",
    )
    arguments = parser.parse_args()
    if arguments.jobs <= 0 or arguments.checkpoint_every <= 0 or arguments.seconds < 0:
        parser.error(
            "--jobs and --checkpoint-every must be positive; --seconds must be nonnegative"
        )
    for path, label in (
        (arguments.cnf, "CNF"),
        (arguments.cubes, "cube file"),
        (arguments.solver, "solver"),
        (arguments.checker, "checker"),
    ):
        if not path.is_file():
            parser.error(f"{label} does not exist: {path}")
    if (
        arguments.scratch_directory is not None
        and not arguments.scratch_directory.is_dir()
    ):
        parser.error(f"scratch directory does not exist: {arguments.scratch_directory}")

    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    progress_path = output / "progress.json"
    if manifest_path.exists() or progress_path.exists():
        parser.error("output directory already contains a manifest or progress file")

    before, after, variables, clauses = read_cnf(arguments.cnf)
    cubes = read_cubes(arguments.cubes, variables)
    cnf_sha256 = file_sha256(arguments.cnf)
    cubes_sha256 = file_sha256(arguments.cubes)
    solver_sha256 = file_sha256(arguments.solver)
    checker_sha256 = file_sha256(arguments.checker)
    results: list[dict[str, Any] | None] = [None] * len(cubes)
    result_lock = threading.Lock()

    document: dict[str, Any] = {
        "schema": SCHEMA,
        "formula": {
            "path": str(arguments.cnf),
            "sha256": cnf_sha256,
            "variables": variables,
            "clauses": clauses,
        },
        "cubes": {
            "path": str(arguments.cubes),
            "sha256": cubes_sha256,
            "count": len(cubes),
        },
        "solver": {
            "path": str(arguments.solver),
            "sha256": solver_sha256,
            "arguments": arguments.solver_argument,
        },
        "checker": {
            "path": str(arguments.checker),
            "sha256": checker_sha256,
        },
        "per_cube_seconds": arguments.seconds,
        "compact_proof": arguments.compact_proof,
        "scratch_directory": (
            str(arguments.scratch_directory)
            if arguments.scratch_directory is not None
            else None
        ),
        "jobs": min(arguments.jobs, len(cubes)),
        "results": results,
    }
    atomic_json(progress_path, document)

    temporary_parent = arguments.scratch_directory or output
    with tempfile.TemporaryDirectory(
        prefix="materialized-cubes-", dir=temporary_parent
    ) as raw:
        temporary_directory = Path(raw)

        def prove(item: tuple[int, list[int]]) -> tuple[int, dict[str, Any]]:
            index, cube = item
            cube_digest = cube_sha256(cube)
            stem = f"cube-{index:06d}-{cube_digest[:16]}"
            formula = temporary_directory / f"{stem}.cnf"
            formula.write_text(
                render_cnf(before, after, variables, clauses, cube),
                encoding="ascii",
            )
            augmented_sha256 = file_sha256(formula)
            proof = output / f"{stem}.drat"
            proof_part = temporary_directory / f"{stem}.raw.drat"
            compact_part = temporary_directory / f"{stem}.compact.drat"
            publish_part = proof.with_name(f".{proof.name}.publish.part")
            checker_log = output / f"{stem}.checker.log"
            compact_log = output / f"{stem}.compact.log"
            sat_log = output / f"{stem}.sat.log"
            if (
                proof.exists()
                or publish_part.exists()
                or checker_log.exists()
                or compact_log.exists()
                or sat_log.exists()
            ):
                raise RuntimeError(f"refusing to overwrite artifacts for cube {index}")
            started = time.monotonic()
            try:
                try:
                    process = subprocess.run(
                        [
                            str(arguments.solver),
                            *arguments.solver_argument,
                            str(formula),
                            str(proof_part),
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=arguments.seconds or None,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    proof_part.unlink(missing_ok=True)
                    return index, {
                        "index": index,
                        "cube": cube,
                        "cube_sha256": cube_digest,
                        "augmented_cnf_sha256": augmented_sha256,
                        "status": 0,
                        "seconds": round(time.monotonic() - started, 6),
                    }
                seconds = round(time.monotonic() - started, 6)
                if process.returncode == 10:
                    proof_part.unlink(missing_ok=True)
                    sat_log.write_text(process.stdout, encoding="utf-8")
                    try:
                        model: str | None = parse_model(process.stdout, variables)
                    except ValueError:
                        model = None
                    result = {
                        "index": index,
                        "cube": cube,
                        "cube_sha256": cube_digest,
                        "augmented_cnf_sha256": augmented_sha256,
                        "status": 10,
                        "seconds": seconds,
                        "model": model,
                        "solver_log": sat_log.name,
                        "solver_log_sha256": file_sha256(sat_log),
                    }
                    return index, result
                if process.returncode != 20:
                    raise RuntimeError(
                        f"solver exited {process.returncode} on cube {index}: "
                        f"{process.stdout[-2000:]}"
                    )
                if not proof_part.is_file() or proof_part.stat().st_size == 0:
                    raise RuntimeError(f"solver emitted no proof for cube {index}")
                source_proof_bytes = proof_part.stat().st_size
                source_proof_sha256 = file_sha256(proof_part)
                compaction: dict[str, Any] | None = None
                if arguments.compact_proof:
                    checked = subprocess.run(
                        [
                            str(arguments.checker),
                            str(formula),
                            str(proof_part),
                            "-C",
                            "-l",
                            str(compact_part),
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                    compact_log.write_text(checked.stdout, encoding="utf-8")
                    if (
                        checked.returncode
                        or "s VERIFIED" not in checked.stdout
                        or not compact_part.is_file()
                        or compact_part.stat().st_size == 0
                    ):
                        raise RuntimeError(
                            f"proof compaction rejected cube {index}; see {compact_log}"
                        )
                    retain_compact = compact_part.stat().st_size < source_proof_bytes
                    if retain_compact:
                        replayed = subprocess.run(
                            [
                                str(arguments.checker),
                                str(formula),
                                str(compact_part),
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            check=False,
                        )
                        checker_log.write_text(replayed.stdout, encoding="utf-8")
                        if replayed.returncode or "s VERIFIED" not in replayed.stdout:
                            raise RuntimeError(
                                f"checker rejected compact proof for cube {index}; "
                                f"see {checker_log}"
                        )
                        proof_part.unlink()
                        publish_proof(compact_part, proof)
                    else:
                        checker_log.write_text(checked.stdout, encoding="utf-8")
                        compact_part.unlink()
                        publish_proof(proof_part, proof)
                    compaction = {
                        "method": "drat-trim -C -l",
                        "retained": retain_compact,
                        "source_proof_bytes": source_proof_bytes,
                        "source_proof_sha256": source_proof_sha256,
                        "log": compact_log.name,
                        "log_sha256": file_sha256(compact_log),
                    }
                else:
                    checked = subprocess.run(
                        [str(arguments.checker), str(formula), str(proof_part)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False,
                    )
                    checker_log.write_text(checked.stdout, encoding="utf-8")
                    if checked.returncode or "s VERIFIED" not in checked.stdout:
                        raise RuntimeError(
                            f"checker rejected cube {index}; see {checker_log}"
                        )
                    publish_proof(proof_part, proof)
                result = {
                    "index": index,
                    "cube": cube,
                    "cube_sha256": cube_digest,
                    "augmented_cnf_sha256": augmented_sha256,
                    "status": 20,
                    "seconds": seconds,
                    "proof": proof.name,
                    "proof_bytes": proof.stat().st_size,
                    "proof_sha256": file_sha256(proof),
                    "checker_log": checker_log.name,
                    "checker_log_sha256": file_sha256(checker_log),
                }
                if compaction is not None:
                    result["compaction"] = compaction
                return index, result
            finally:
                formula.unlink(missing_ok=True)

        completed = 0
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(arguments.jobs, len(cubes))
        ) as executor:
            try:
                for index, result in completed_results(
                    executor, prove, enumerate(cubes)
                ):
                    with result_lock:
                        results[index] = result
                        completed += 1
                        if (
                            completed % arguments.checkpoint_every == 0
                            or result["status"] == 10
                        ):
                            atomic_json(progress_path, document)
                    print(
                        f"finished {completed}/{len(cubes)} "
                        f"cube={index} status={result['status']}",
                        flush=True,
                    )
            except BaseException:
                # Small portfolios often finish fewer rows than the periodic
                # checkpoint interval before another worker fails.  Preserve
                # every safely collected result so published proofs remain
                # recoverable from the progress document.
                with result_lock:
                    atomic_json(progress_path, document)
                raise

    if any(result is None for result in results):
        raise RuntimeError("missing cube result")
    statuses = [int(result["status"]) for result in results if result is not None]
    document["summary"] = {
        "unsat_verified": statuses.count(20),
        "unknown": statuses.count(0),
        "sat": statuses.count(10),
        "complete_unsat": all(status == 20 for status in statuses),
    }
    atomic_json(manifest_path, document)
    progress_path.unlink()
    print(json.dumps(document["summary"], sort_keys=True))
    if 10 in statuses:
        return 10
    return 20 if all(status == 20 for status in statuses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
