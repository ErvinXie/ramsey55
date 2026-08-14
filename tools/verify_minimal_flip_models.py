#!/usr/bin/env python3
"""Independently close an enumerated fixed-cardinality flip search with DRAT."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from enumerate_minimal_flip_models import PAIRS, read_checkpoint
from ramsey55 import Graph


VERIFICATION_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_blocking_clauses(
    source: Path, destination: Path, models: list[tuple[int, ...]]
) -> None:
    found_header = False
    with source.open(encoding="ascii") as input_file, destination.open(
        "w", encoding="ascii"
    ) as output_file:
        for line in input_file:
            if line.startswith("p cnf "):
                if found_header:
                    raise ValueError(f"multiple DIMACS headers in {source}")
                fields = line.split()
                if len(fields) != 4:
                    raise ValueError(f"invalid DIMACS header in {source}: {line!r}")
                variables, clauses = map(int, fields[2:])
                output_file.write(f"p cnf {variables} {clauses + len(models)}\n")
                found_header = True
            else:
                output_file.write(line)
        if not found_header:
            raise ValueError(f"missing DIMACS header in {source}")
        for model in models:
            output_file.write(" ".join(str(-(edge + 1)) for edge in model))
            output_file.write(" 0\n")


def toggle_graph(graph: Graph, model: tuple[int, ...]) -> Graph:
    toggle = {PAIRS[edge] for edge in model}
    return Graph.from_edges(
        42,
        (
            (u, v)
            for u in range(42)
            for v in range(u + 1, 42)
            if graph.has_edge(u, v) != ((u, v) in toggle)
        ),
    )


def check_models_are_inclusion_minimal(
    graph: Graph, models: list[tuple[int, ...]], flips: int, index: int
) -> None:
    for model in models:
        if not toggle_graph(graph, model).is_ramsey_55_graph():
            raise AssertionError(
                f"representative {index} model {model} is not Ramsey-free"
            )
        for subset_size in range(1, flips):
            for subset in itertools.combinations(model, subset_size):
                if toggle_graph(graph, subset).is_ramsey_55_graph():
                    raise AssertionError(
                        f"representative {index} model {model} has safe proper "
                        f"subset {subset}"
                    )


def write_marker(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as output:
            json.dump(payload, output, sort_keys=True, separators=(",", ":"))
            output.write("\n")
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def verify_one(
    task: tuple[
        int,
        int,
        str,
        Path,
        Path,
        Path,
        Path,
        Path,
        Path,
        str,
        str,
        str,
        str,
    ]
) -> tuple[int, int, bool]:
    (
        index,
        flips,
        graph6,
        graphs_path,
        generator,
        solver,
        proof_checker,
        checkpoint_dir,
        verification_dir,
        temporary_root,
        generator_sha256,
        solver_sha256,
        proof_checker_sha256,
    ) = task
    checkpoint = checkpoint_dir / f"rep{index:03d}.json.gz"
    models = read_checkpoint(checkpoint, index, flips, graph6)
    expected_marker = {
        "version": VERIFICATION_VERSION,
        "representative": index,
        "flips": flips,
        "graph6": graph6,
        "model_count": len(models),
        "checkpoint_sha256": sha256_file(checkpoint),
        "generator_sha256": generator_sha256,
        "solver_sha256": solver_sha256,
        "proof_checker_sha256": proof_checker_sha256,
        "result": "UNSAT_VERIFIED",
    }
    marker = verification_dir / f"rep{index:03d}.json"
    if marker.exists():
        with marker.open(encoding="ascii") as source:
            recorded = json.load(source)
        if recorded == expected_marker:
            return index, len(models), True

    graph = Graph.from_graph6(graph6)
    check_models_are_inclusion_minimal(graph, models, flips, index)
    with tempfile.TemporaryDirectory(
        prefix=f"verify-rep{index:03d}-", dir=temporary_root
    ) as directory:
        raw_cnf = Path(directory) / "raw.cnf"
        blocked_cnf = Path(directory) / "blocked.cnf"
        proof = Path(directory) / "exhausted.drat"
        subprocess.run(
            [
                str(generator),
                str(graphs_path),
                str(index),
                str(raw_cnf),
                str(flips),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        add_blocking_clauses(raw_cnf, blocked_cnf, models)
        solved = subprocess.run(
            [str(solver), str(blocked_cnf), str(proof)],
            text=True,
            capture_output=True,
        )
        if solved.returncode != 20:
            raise RuntimeError(
                f"blocked enumeration for representative {index} was not UNSAT: "
                f"return code {solved.returncode}\n{solved.stdout}\n{solved.stderr}"
            )
        checked = subprocess.run(
            [str(proof_checker), str(blocked_cnf), str(proof)],
            text=True,
            capture_output=True,
        )
        if checked.returncode != 0 or "s VERIFIED" not in checked.stdout:
            raise RuntimeError(
                f"DRAT verification failed for representative {index}:\n"
                f"{checked.stdout}\n{checked.stderr}"
            )
    write_marker(marker, expected_marker)
    return index, len(models), False


def load_graph6(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--generator", type=Path, default=Path("build/generate_three_flip_cnf")
    )
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--proof-checker", type=Path, required=True)
    parser.add_argument("--flips", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=328)
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        help="enumeration checkpoints (default: build/minimal-N-flip-models)",
    )
    parser.add_argument(
        "--verification-dir",
        type=Path,
        help="successful proof-check markers (default: build/minimal-N-flip-verified)",
    )
    args = parser.parse_args()
    if not 0 <= args.start <= args.stop <= 328 or args.jobs < 1:
        raise ValueError("invalid representative range or job count")
    records = load_graph6(args.graphs)
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")
    checkpoint_dir = args.checkpoint_dir or Path(
        f"build/minimal-{args.flips}-flip-models"
    )
    verification_dir = args.verification_dir or Path(
        f"build/minimal-{args.flips}-flip-verified"
    )
    verification_dir.mkdir(parents=True, exist_ok=True)
    for executable in (args.generator, args.solver, args.proof_checker):
        if not executable.is_file():
            raise FileNotFoundError(executable)
    hashes = tuple(
        sha256_file(executable)
        for executable in (args.generator, args.solver, args.proof_checker)
    )
    with tempfile.TemporaryDirectory(prefix="ramsey55-verify-flips-") as root:
        tasks = [
            (
                index,
                args.flips,
                records[index],
                args.graphs,
                args.generator,
                args.solver,
                args.proof_checker,
                checkpoint_dir,
                verification_dir,
                root,
                *hashes,
            )
            for index in range(args.start, args.stop)
        ]
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(verify_one, task) for task in tasks]
            results = []
            for completed, future in enumerate(as_completed(futures), start=1):
                index, models, resumed = future.result()
                results.append((index, models))
                print(
                    f"verified {completed}/{len(tasks)} representative={index} "
                    f"models={models} source={'marker' if resumed else 'DRAT'}",
                    flush=True,
                )
    print(f"verified minimal safe {args.flips}-flip enumeration")
    print(f"  representatives: {args.start}..{args.stop - 1}")
    print(f"  blocked models: {sum(models for _, models in results)}")
    print(f"  independently checked UNSAT proofs: {len(results)}")
    print(f"  verification markers: {verification_dir}")


if __name__ == "__main__":
    main()
