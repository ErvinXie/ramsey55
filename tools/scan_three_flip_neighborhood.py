#!/usr/bin/env python3
"""Search for Ramsey graphs first reachable by three simultaneous flips."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

from ramsey55 import Graph


PAIRS = tuple((u, v) for u in range(42) for v in range(u + 1, 42))


def load_graph6(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def scan_one(
    task: tuple[int, int, Path, Path, Path, Path | None, str]
) -> tuple[int, str, tuple[int, ...] | None, str]:
    (
        index,
        flip_count,
        graphs_path,
        generator,
        solver,
        proof_checker,
        temporary_root,
    ) = task
    with tempfile.TemporaryDirectory(
        prefix=f"rep{index:03d}-", dir=temporary_root
    ) as directory:
        cnf = Path(directory) / "minimal-three.cnf"
        generated = subprocess.run(
            [
                str(generator),
                str(graphs_path),
                str(index),
                str(cnf),
                str(flip_count),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        proof = Path(directory) / "unsat.drat"
        solver_command = [str(solver), str(cnf)]
        if proof_checker is not None:
            solver_command.append(str(proof))
        solved = subprocess.run(
            solver_command,
            text=True,
            capture_output=True,
        )
        if solved.returncode == 20 and proof_checker is not None:
            checked = subprocess.run(
                [str(proof_checker), str(cnf), str(proof)],
                text=True,
                capture_output=True,
            )
            if checked.returncode != 0 or "s VERIFIED" not in checked.stdout:
                raise RuntimeError(
                    f"DRAT verification failed for representative {index}:\n"
                    f"{checked.stdout}\n{checked.stderr}"
                )
    if solved.returncode == 20:
        return index, "UNSAT", None, generated.stdout
    if solved.returncode != 10:
        raise RuntimeError(
            f"solver failed for representative {index}: "
            f"{solved.returncode}\n{solved.stdout}\n{solved.stderr}"
        )
    positive: set[int] = set()
    for line in solved.stdout.splitlines():
        if line.startswith("v "):
            positive.update(
                literal
                for literal in map(int, line.split()[1:])
                if 1 <= literal <= len(PAIRS)
            )
    if len(positive) != flip_count:
        raise AssertionError(
            f"expected {flip_count} primary variables, got {positive}"
        )
    return index, "SAT", tuple(sorted(value - 1 for value in positive)), generated.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--generator", type=Path, default=Path("build/generate_three_flip_cnf")
    )
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument(
        "--proof-checker",
        type=Path,
        help="write each UNSAT proof, verify it independently, then discard it",
    )
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument("--flips", type=int, default=3)
    parser.add_argument("--labelg", type=Path)
    parser.add_argument(
        "--forest",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=328)
    args = parser.parse_args()
    if (
        not 0 <= args.start <= args.stop <= 328
        or args.jobs < 1
        or not 2 <= args.flips <= 9
    ):
        raise ValueError("invalid catalog range or job count")

    records = load_graph6(args.graphs)
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")
    graphs = [Graph.from_graph6(record) for record in records]
    with tempfile.TemporaryDirectory(prefix="ramsey55-three-flip-") as root:
        tasks = [
            (
                index,
                args.flips,
                args.graphs,
                args.generator,
                args.solver,
                args.proof_checker,
                root,
            )
            for index in range(args.start, args.stop)
        ]
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            results = list(executor.map(scan_one, tasks))

    sat_results = [result for result in results if result[1] == "SAT"]
    candidates: list[tuple[int, tuple[int, ...], Graph]] = []
    for index, _, flips, _ in sat_results:
        assert flips is not None
        toggle = {PAIRS[edge] for edge in flips}
        graph = graphs[index]
        candidate = Graph.from_edges(
            42,
            (
                (u, v)
                for u in range(42)
                for v in range(u + 1, 42)
                if graph.has_edge(u, v) != ((u, v) in toggle)
            ),
        )
        if not candidate.is_ramsey_55_graph():
            raise AssertionError("SAT model did not produce a Ramsey graph")
        candidates.append((index, flips, candidate))

    new_types = 0
    if args.labelg is None:
        for index, flips, candidate in candidates:
            print(
                f"SAT representative={index} edge_indices={flips} "
                f"graph6={candidate.to_graph6()}"
            )
    else:
        catalog = [
            encoded
            for graph in graphs
            for encoded in (graph.to_graph6(), graph.complement().to_graph6())
        ]
        canonical = subprocess.run(
            [str(args.labelg), "-q"],
            input="\n".join(
                catalog + [candidate.to_graph6() for _, _, candidate in candidates]
            )
            + "\n",
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        lookup = {value: index for index, value in enumerate(canonical[:656])}
        targets = [lookup.get(value) for value in canonical[656:]]
        new_types = sum(target is None for target in targets)

        with gzip.open(args.forest, "rt", encoding="ascii") as compressed:
            forest = json.load(compressed)
        parents = {
            item["child"]: item["parent"] for item in forest["transitions"]
        }

        def root(vertex: int) -> int:
            while vertex in parents:
                vertex = parents[vertex]
            return vertex

        component_moves = Counter(
            (root(parent), root(target // 2))
            for (parent, _, _), target in zip(candidates, targets)
            if target is not None
        )
        print(f"  catalog component moves: {dict(sorted(component_moves.items()))}")
        for (parent, flips, candidate), target in zip(candidates, targets):
            if target is None:
                print(
                    f"NEW representative={parent} edge_indices={flips} "
                    f"graph6={candidate.to_graph6()}"
                )

    print(f"minimal safe {args.flips}-flip scan")
    print(f"  representatives: {args.start}..{args.stop - 1}")
    print(f"  UNSAT: {len(results) - len(sat_results)}")
    print(f"  SAT: {len(sat_results)}")
    if args.labelg is not None:
        print(f"  new catalog types: {new_types}")
    print(f"  independently checked proofs: {len(results) if args.proof_checker else 0}")


if __name__ == "__main__":
    main()
