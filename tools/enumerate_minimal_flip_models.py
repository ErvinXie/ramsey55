#!/usr/bin/env python3
"""Enumerate every minimal fixed-cardinality flip set in generated CNFs."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from ramsey55 import Graph


PAIRS = tuple((u, v) for u in range(42) for v in range(u + 1, 42))
CHECKPOINT_VERSION = 1


def read_checkpoint(path: Path, index: int, flips: int, graph6: str) -> list[tuple[int, ...]]:
    with gzip.open(path, "rt", encoding="ascii") as compressed:
        payload: Any = json.load(compressed)
    expected = {
        "version": CHECKPOINT_VERSION,
        "representative": index,
        "flips": flips,
        "graph6": graph6,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(
                f"checkpoint {path} has {key}={payload.get(key)!r}, expected {value!r}"
            )
    models = [tuple(model) for model in payload.get("models", [])]
    validate_models(models, flips, path)
    if payload.get("model_count") != len(models):
        raise ValueError(f"checkpoint {path} has an inconsistent model count")
    return models


def validate_models(
    models: list[tuple[int, ...]], flips: int, source: Path | str
) -> None:
    if any(
        len(model) != flips
        or tuple(sorted(model)) != model
        or len(set(model)) != flips
        or any(not 0 <= edge < len(PAIRS) for edge in model)
        for model in models
    ):
        raise ValueError(f"invalid model in {source}")
    if len(models) != len(set(models)):
        raise ValueError(f"duplicate model in {source}")


def write_checkpoint(
    path: Path,
    index: int,
    flips: int,
    graph6: str,
    models: list[tuple[int, ...]],
) -> None:
    payload = {
        "version": CHECKPOINT_VERSION,
        "representative": index,
        "flips": flips,
        "graph6": graph6,
        "model_count": len(models),
        "models": models,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                compressed.write(
                    (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
                        "ascii"
                    )
                )
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def enumerate_one(
    task: tuple[int, int, str, Path, Path, Path, Path, str]
) -> tuple[int, list[tuple[int, ...]], bool]:
    index, flips, graph6, graphs, generator, enumerator, result_dir, temporary_root = task
    checkpoint = result_dir / f"rep{index:03d}.json.gz"
    if checkpoint.exists():
        return index, read_checkpoint(checkpoint, index, flips, graph6), True
    with tempfile.TemporaryDirectory(
        prefix=f"rep{index:03d}-", dir=temporary_root
    ) as directory:
        cnf = Path(directory) / "minimal-flips.cnf"
        raw_models = Path(directory) / "models.tsv"
        subprocess.run(
            [str(generator), str(graphs), str(index), str(cnf), str(flips)],
            text=True,
            capture_output=True,
            check=True,
        )
        with raw_models.open("w", encoding="ascii") as output:
            subprocess.run(
                [str(enumerator), str(cnf), str(len(PAIRS))],
                text=True,
                stdout=output,
                stderr=subprocess.PIPE,
                check=True,
            )
        models: list[tuple[int, ...]] = []
        reported_count: int | None = None
        with raw_models.open(encoding="ascii") as lines:
            for line in lines:
                fields = line.rstrip("\n").split("\t")
                if fields[0] == "model":
                    models.append(tuple(map(int, fields[1:])))
                elif fields[0] == "models" and len(fields) == 2:
                    reported_count = int(fields[1])
                else:
                    raise ValueError(f"unexpected enumerator output: {line.rstrip()}")
    validate_models(models, flips, f"representative {index}")
    if reported_count != len(models):
        raise ValueError(
            f"enumerator reported {reported_count} models for representative {index}, "
            f"parsed {len(models)}"
        )
    write_checkpoint(checkpoint, index, flips, graph6, models)
    return index, models, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--generator", type=Path, default=Path("build/generate_three_flip_cnf")
    )
    parser.add_argument("--enumerator", type=Path, required=True)
    parser.add_argument("--labelg", type=Path, required=True)
    parser.add_argument(
        "--forest",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    parser.add_argument("--flips", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=328)
    parser.add_argument(
        "--result-dir",
        type=Path,
        help="persistent checkpoint directory (default: build/minimal-N-flip-models)",
    )
    args = parser.parse_args()
    if not 0 <= args.start <= args.stop <= 328 or args.jobs < 1:
        raise ValueError("invalid representative range or job count")

    records = [
        line.strip()
        for line in args.graphs.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")
    graphs = [Graph.from_graph6(record) for record in records]
    result_dir = args.result_dir or Path(f"build/minimal-{args.flips}-flip-models")
    result_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ramsey55-enumerate-flips-") as root:
        tasks = [
            (
                index,
                args.flips,
                records[index],
                args.graphs,
                args.generator,
                args.enumerator,
                result_dir,
                root,
            )
            for index in range(args.start, args.stop)
        ]
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {executor.submit(enumerate_one, task): task[0] for task in tasks}
            by_graph = []
            for completed, future in enumerate(as_completed(futures), start=1):
                index, models, resumed = future.result()
                by_graph.append((index, models))
                print(
                    f"completed {completed}/{len(tasks)} representative={index} "
                    f"models={len(models)} source={'checkpoint' if resumed else 'solver'}",
                    flush=True,
                )
    by_graph.sort()

    candidates: list[tuple[int, tuple[int, ...], Graph]] = []
    for index, models in by_graph:
        graph = graphs[index]
        for model in models:
            toggle = {PAIRS[edge] for edge in model}
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
                raise AssertionError("enumerated model is not a Ramsey graph")
            candidates.append((index, model, candidate))

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
    unknown = [
        (parent, model, candidate)
        for (parent, model, candidate), target in zip(candidates, targets)
        if target is None
    ]

    with gzip.open(args.forest, "rt", encoding="ascii") as compressed:
        forest = json.load(compressed)
    parents = {item["child"]: item["parent"] for item in forest["transitions"]}

    def root(vertex: int) -> int:
        while vertex in parents:
            vertex = parents[vertex]
        return vertex

    component_moves = Counter(
        (root(parent), root(target // 2))
        for (parent, _, _), target in zip(candidates, targets)
        if target is not None
    )
    model_histogram = Counter(len(models) for _, models in by_graph)
    print(f"minimal safe {args.flips}-flip model enumeration")
    print(f"  representatives: {args.start}..{args.stop - 1}")
    print(f"  checkpoints: {result_dir}")
    print(f"  total labelled models: {len(candidates)}")
    print(f"  models per representative: {dict(sorted(model_histogram.items()))}")
    print(f"  catalog component moves: {dict(sorted(component_moves.items()))}")
    print(f"  new catalog types: {len(unknown)}")
    for parent, model, candidate in unknown:
        print(
            f"NEW representative={parent} edge_indices={model} "
            f"graph6={candidate.to_graph6()}"
        )


if __name__ == "__main__":
    main()
