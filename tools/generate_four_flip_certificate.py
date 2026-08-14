#!/usr/bin/env python3
"""Certify every inclusion-minimal safe four-edge catalog move explicitly."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from typing import Any

from enumerate_minimal_flip_models import PAIRS, read_checkpoint
from generate_catalog_flip_certificate import (
    find_isomorphism,
    load_graph6,
    write_deterministic_gzip,
)
from ramsey55 import Graph


FORMAT = "ramsey55-minimal-four-flip-catalog-v1"
ORDER = 42
FLIPS = 4


def toggle_graph(graph: Graph, edge_indices: tuple[int, ...]) -> Graph:
    toggle = {PAIRS[index] for index in edge_indices}
    return Graph.from_edges(
        ORDER,
        (
            (u, v)
            for u in range(ORDER)
            for v in range(u + 1, ORDER)
            if graph.has_edge(u, v) != ((u, v) in toggle)
        ),
    )


def verify_document(document: object, records: list[str]) -> None:
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise AssertionError("bad four-flip certificate format")
    if document.get("order") != ORDER or document.get("flip_count") != FLIPS:
        raise AssertionError("bad four-flip certificate parameters")
    representatives = document.get("representatives")
    if not isinstance(representatives, list) or len(representatives) != 328:
        raise AssertionError("expected 328 representative records")
    graphs = [Graph.from_graph6(record) for record in records]
    if len(graphs) != 328 or not all(graph.is_ramsey_55_graph() for graph in graphs):
        raise AssertionError("invalid public catalog")

    model_counts: Counter[int] = Counter()
    seen: set[tuple[int, tuple[int, ...]]] = set()
    for expected_parent, representative in enumerate(representatives):
        if not isinstance(representative, dict):
            raise AssertionError("malformed representative record")
        parent = representative.get("parent")
        models = representative.get("models")
        if parent != expected_parent or not isinstance(models, list):
            raise AssertionError("representative records are not in catalog order")
        model_counts[len(models)] += 1
        for item in models:
            if not isinstance(item, dict):
                raise AssertionError("malformed four-flip model")
            edge_indices = item.get("edge_indices")
            edges = item.get("edges")
            child = item.get("child")
            complemented = item.get("complement")
            permutation = item.get("permutation")
            if (
                not isinstance(edge_indices, list)
                or len(edge_indices) != FLIPS
                or not all(isinstance(value, int) for value in edge_indices)
                or edge_indices != sorted(set(edge_indices))
                or any(not 0 <= value < len(PAIRS) for value in edge_indices)
                or not isinstance(edges, list)
                or edges != [list(PAIRS[value]) for value in edge_indices]
                or not isinstance(child, int)
                or not 0 <= child < 328
                or not isinstance(complemented, bool)
                or not isinstance(permutation, list)
                or sorted(permutation) != list(range(ORDER))
            ):
                raise AssertionError("malformed four-flip model fields")
            model = tuple(edge_indices)
            key = (parent, model)
            if key in seen:
                raise AssertionError("duplicate four-flip model")
            seen.add(key)

            candidate = toggle_graph(graphs[parent], model)
            if not candidate.is_ramsey_55_graph():
                raise AssertionError("four-flip model does not remain Ramsey-free")
            for subset_size in range(1, FLIPS):
                for subset in itertools.combinations(model, subset_size):
                    if toggle_graph(graphs[parent], subset).is_ramsey_55_graph():
                        raise AssertionError("four-flip model has a safe proper subset")
            target = graphs[child].complement() if complemented else graphs[child]
            if not all(
                candidate.has_edge(u, v)
                == target.has_edge(permutation[u], permutation[v])
                for u in range(ORDER)
                for v in range(ORDER)
            ):
                raise AssertionError("explicit four-flip isomorphism is invalid")

    if model_counts != Counter({0: 208, 1: 80, 2: 40}) or len(seen) != 160:
        raise AssertionError(
            f"unexpected four-flip census: {dict(sorted(model_counts.items()))}, "
            f"total={len(seen)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("build/minimal-4-flip-models"),
    )
    parser.add_argument("--labelg", type=Path, required=True)
    parser.add_argument(
        "--forest",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/r55_42_minimal_four_flips.json.gz"),
    )
    args = parser.parse_args()

    records = load_graph6(args.graphs)
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")
    graphs = [Graph.from_graph6(record) for record in records]
    models_by_parent = [
        read_checkpoint(
            args.checkpoint_dir / f"rep{parent:03d}.json.gz",
            parent,
            FLIPS,
            records[parent],
        )
        for parent in range(328)
    ]
    candidates = [
        (parent, model, toggle_graph(graphs[parent], model))
        for parent, models in enumerate(models_by_parent)
        for model in models
    ]
    if len(candidates) != 160:
        raise AssertionError(f"expected 160 models, found {len(candidates)}")

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
    if len(canonical) != 656 + len(candidates):
        raise AssertionError("labelg output length mismatch")
    lookup = {value: index for index, value in enumerate(canonical[:656])}
    if len(lookup) != 656:
        raise AssertionError("catalog contains duplicate unlabelled graphs")
    targets = [lookup.get(value) for value in canonical[656:]]
    if any(target is None for target in targets):
        raise AssertionError("a minimal four-flip model escapes the public catalog")

    model_items: dict[int, list[dict[str, Any]]] = {
        parent: [] for parent in range(328)
    }
    for (parent, model, candidate), catalog_index in zip(candidates, targets):
        assert catalog_index is not None
        child = catalog_index // 2
        complemented = bool(catalog_index % 2)
        target = graphs[child].complement() if complemented else graphs[child]
        model_items[parent].append(
            {
                "edge_indices": list(model),
                "edges": [list(PAIRS[index]) for index in model],
                "child": child,
                "complement": complemented,
                "permutation": list(find_isomorphism(candidate, target)),
            }
        )

    document: dict[str, Any] = {
        "format": FORMAT,
        "order": ORDER,
        "flip_count": FLIPS,
        "representatives": [
            {"parent": parent, "models": model_items[parent]}
            for parent in range(328)
        ],
    }
    verify_document(document, records)
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
        "ascii"
    )
    write_deterministic_gzip(args.output, payload)
    with gzip.open(args.output, "rt", encoding="ascii") as source:
        verify_document(json.load(source), records)

    with gzip.open(args.forest, "rt", encoding="ascii") as source:
        forest = json.load(source)
    parent_of = {
        transition["child"]: transition["parent"]
        for transition in forest["transitions"]
    }

    def root(vertex: int) -> int:
        while vertex in parent_of:
            vertex = parent_of[vertex]
        return vertex

    component_moves = Counter(
        (root(parent), root(item["child"]))
        for parent, items in model_items.items()
        for item in items
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print("R(5,5,42) minimal four-flip certificate")
    print(f"  models: {len(candidates)}")
    print(
        "  models per representative: "
        f"{dict(sorted(Counter(map(len, models_by_parent)).items()))}"
    )
    print(f"  catalog component moves: {dict(sorted(component_moves.items()))}")
    print(f"  output bytes: {args.output.stat().st_size}")
    print(f"  sha256: {digest}")


if __name__ == "__main__":
    main()
