#!/usr/bin/env python3
"""Find the minimum apex-violation count for the public 42-vertex graphs."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ramsey55 import (
    ExtensionMultiplicityCounterexample,
    Graph,
    generate_extension_multiplicity_certificate,
    verify_extension_multiplicity_certificate,
)


def analyze_record(task: tuple[int, str, int, int]) -> tuple[int, int | None, int]:
    index, graph6, start_bound, maximum = task
    graph = Graph.from_graph6(graph6)
    total_nodes = 0
    for proposed_bound in range(start_bound, maximum + 1):
        try:
            certificate = generate_extension_multiplicity_certificate(
                graph, proposed_bound
            )
        except ExtensionMultiplicityCounterexample as counterexample:
            return index, counterexample.violation_count, total_nodes
        if not verify_extension_multiplicity_certificate(graph, certificate):
            raise AssertionError(
                f"multiplicity-{proposed_bound} certificate {index} failed"
            )
        total_nodes += len(certificate.nodes)
    return index, None, total_nodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs",
        type=Path,
        default=Path("data/reference/r55_42some.g6"),
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--start-bound",
        type=int,
        default=3,
        help="first proposed bound; smaller bounds must already be certified",
    )
    parser.add_argument(
        "--maximum",
        type=int,
        default=6,
        help="report a lower bound if no attachment below this value is found",
    )
    args = parser.parse_args()
    if (
        args.jobs < 1
        or args.start_bound < 2
        or args.maximum < args.start_bound
    ):
        raise ValueError("invalid jobs or multiplicity-bound interval")

    records = [
        line.strip()
        for line in args.graphs.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")

    tasks = [
        (index, graph6, args.start_bound, args.maximum)
        for index, graph6 in enumerate(records)
    ]
    if args.jobs == 1:
        results = list(map(analyze_record, tasks))
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            results = list(executor.map(analyze_record, tasks, chunksize=1))

    by_minimum: dict[int | None, list[int]] = defaultdict(list)
    checked_nodes = 0
    for index, minimum, nodes in results:
        by_minimum[minimum].append(index)
        checked_nodes += nodes

    print("Minimum monochromatic K5s created by one apex")
    for minimum in sorted(value for value in by_minimum if value is not None):
        indices = by_minimum[minimum]
        print(f"  exactly {minimum}: {len(indices)}")
        print("   ", " ".join(map(str, indices)))
    if None in by_minimum:
        indices = by_minimum[None]
        print(f"  at least {args.maximum}: {len(indices)}")
        print("   ", " ".join(map(str, indices)))
    print(f"  successful lower-bound tree nodes checked: {checked_nodes}")


if __name__ == "__main__":
    main()
