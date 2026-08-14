#!/usr/bin/env python3
"""Compress the 328 public representatives into six single-flip components.

Nauty is used only to discover which catalog graph a flipped graph matches.
The emitted certificate contains explicit vertex permutations and is checked
without nauty before it is accepted.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from ramsey55 import Graph


FORMAT = "ramsey55-catalog-flip-forest-v1"
ORDER = 42
EDGE_COUNT = ORDER * (ORDER - 1) // 2
PAIRS = tuple((u, v) for v in range(1, ORDER) for u in range(v))


def load_graph6(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def toggle_graph6(graph6: str, edge_index: int) -> str:
    if not 0 <= edge_index < EDGE_COUNT or ord(graph6[0]) - 63 != ORDER:
        raise ValueError("expected a short graph6 record of order 42")
    word = 1 + edge_index // 6
    shift = 5 - edge_index % 6
    changed = chr(((ord(graph6[word]) - 63) ^ (1 << shift)) + 63)
    return graph6[:word] + changed + graph6[word + 1 :]


def joint_refine(
    left: Graph,
    right: Graph,
    left_colors: tuple[int, ...],
    right_colors: tuple[int, ...],
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    while True:
        left_signatures = tuple(
            (
                left_colors[v],
                tuple(
                    sorted(
                        left_colors[w]
                        for w in range(ORDER)
                        if left.has_edge(v, w)
                    )
                ),
            )
            for v in range(ORDER)
        )
        right_signatures = tuple(
            (
                right_colors[v],
                tuple(
                    sorted(
                        right_colors[w]
                        for w in range(ORDER)
                        if right.has_edge(v, w)
                    )
                ),
            )
            for v in range(ORDER)
        )
        identifiers = {
            signature: index
            for index, signature in enumerate(
                sorted(set(left_signatures + right_signatures))
            )
        }
        new_left = tuple(identifiers[s] for s in left_signatures)
        new_right = tuple(identifiers[s] for s in right_signatures)
        if Counter(new_left) != Counter(new_right):
            return None
        if new_left == left_colors and new_right == right_colors:
            return new_left, new_right
        left_colors, right_colors = new_left, new_right


def find_isomorphism(left: Graph, right: Graph) -> tuple[int, ...]:
    """Return a permutation mapping left vertices to right vertices."""

    def search(
        left_colors: tuple[int, ...], right_colors: tuple[int, ...]
    ) -> tuple[int, ...] | None:
        refined = joint_refine(left, right, left_colors, right_colors)
        if refined is None:
            return None
        left_colors, right_colors = refined
        cells = Counter(left_colors)
        if all(size == 1 for size in cells.values()):
            inverse = {color: vertex for vertex, color in enumerate(right_colors)}
            permutation = tuple(inverse[color] for color in left_colors)
            if all(
                left.has_edge(u, v)
                == right.has_edge(permutation[u], permutation[v])
                for u in range(ORDER)
                for v in range(ORDER)
            ):
                return permutation
            return None

        color = min(
            (color for color, size in cells.items() if size > 1),
            key=lambda item: (cells[item], item),
        )
        left_vertex = next(v for v, value in enumerate(left_colors) if value == color)
        marker = max(max(left_colors), max(right_colors)) + 1
        for right_vertex, value in enumerate(right_colors):
            if value != color:
                continue
            next_left = list(left_colors)
            next_right = list(right_colors)
            next_left[left_vertex] = marker
            next_right[right_vertex] = marker
            result = search(tuple(next_left), tuple(next_right))
            if result is not None:
                return result
        return None

    initial_left = tuple(left.degrees)
    initial_right = tuple(right.degrees)
    result = search(initial_left, initial_right)
    if result is None:
        raise ValueError("graphs reported isomorphic have no checked permutation")
    return result


def toggled_graph(graph: Graph, edge: tuple[int, int]) -> Graph:
    toggle_u, toggle_v = edge
    return Graph.from_edges(
        graph.order,
        (
            (u, v)
            for v in range(1, graph.order)
            for u in range(v)
            if graph.has_edge(u, v) != ((u, v) == (toggle_u, toggle_v))
        ),
    )


def has_triangle(adjacency: tuple[int, ...], candidates: int) -> bool:
    while candidates:
        first_bit = candidates & -candidates
        candidates -= first_bit
        first = first_bit.bit_length() - 1
        seconds = adjacency[first] & candidates
        while seconds:
            second_bit = seconds & -seconds
            seconds -= second_bit
            second = second_bit.bit_length() - 1
            if adjacency[second] & seconds:
                return True
    return False


def flip_is_ramsey_free(graph: Graph, edge: tuple[int, int]) -> bool:
    """Use the only K5 type that toggling one pair can create."""

    u, v = edge
    if graph.has_edge(u, v):
        complement = graph.complement()
        common_nonneighbors = complement.adjacency[u] & complement.adjacency[v]
        return not has_triangle(complement.adjacency, common_nonneighbors)
    common_neighbors = graph.adjacency[u] & graph.adjacency[v]
    return not has_triangle(graph.adjacency, common_neighbors)


def verify_document(document: dict[str, object], records: list[str]) -> None:
    if document.get("format") != FORMAT:
        raise AssertionError("bad flip-certificate format")
    roots = document.get("roots")
    transitions = document.get("transitions")
    safe_transitions = document.get("safe_transitions")
    if (
        not isinstance(roots, list)
        or not isinstance(transitions, list)
        or not isinstance(safe_transitions, list)
    ):
        raise AssertionError("missing flip forest")
    if len(roots) != 6 or len(transitions) != 322 or len(safe_transitions) != 2040:
        raise AssertionError("unexpected flip-certificate census")

    graphs = [Graph.from_graph6(record) for record in records]
    if not all(graph.is_ramsey_55_graph() for graph in graphs):
        raise AssertionError("flip closure requires Ramsey-free base graphs")

    def verify_transition(item: object) -> tuple[int, int, tuple[int, int]]:
        if not isinstance(item, dict):
            raise AssertionError("invalid transition")
        parent = item.get("parent")
        child = item.get("child")
        complement = item.get("complement")
        edge = item.get("edge")
        permutation = item.get("permutation")
        if (
            not isinstance(parent, int)
            or not isinstance(child, int)
            or not isinstance(complement, bool)
            or not isinstance(edge, list)
            or len(edge) != 2
            or not all(isinstance(value, int) for value in edge)
            or not isinstance(permutation, list)
            or not all(isinstance(value, int) for value in permutation)
        ):
            raise AssertionError("malformed transition")
        if not 0 <= parent < 328 or not 0 <= child < 328:
            raise AssertionError("transition endpoint is outside the catalog")
        if tuple(edge) not in PAIRS:
            raise AssertionError("transition edge is outside the base graph")
        if sorted(permutation) != list(range(ORDER)):
            raise AssertionError("transition permutation is not bijective")

        left = toggled_graph(graphs[parent], (edge[0], edge[1]))
        right = graphs[child].complement() if complement else graphs[child]
        if not all(
            left.has_edge(u, v)
            == right.has_edge(permutation[u], permutation[v])
            for u in range(ORDER)
            for v in range(ORDER)
        ):
            raise AssertionError(f"transition {parent}->{child} is not valid")
        return parent, child, (edge[0], edge[1])

    expected_safe = {
        (parent, *edge)
        for parent, graph in enumerate(graphs)
        for edge in PAIRS
        if flip_is_ramsey_free(graph, edge)
    }
    seen_safe: set[tuple[int, int, int]] = set()
    for item in safe_transitions:
        parent, _, edge = verify_transition(item)
        key = (parent, *edge)
        if key in seen_safe:
            raise AssertionError("duplicate safe transition")
        seen_safe.add(key)
    if seen_safe != expected_safe:
        raise AssertionError("safe-transition list is not complete")

    reached = set(roots)
    for item in transitions:
        parent, child, _ = verify_transition(item)
        if parent not in reached or child in reached:
            raise AssertionError("transitions are not a rooted forest order")
        reached.add(child)
    if reached != set(range(328)):
        raise AssertionError("flip forest does not cover the public catalog")


def write_deterministic_gzip(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument("--labelg", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    args = parser.parse_args()

    records = load_graph6(args.graphs)
    if len(records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(records)}")
    graphs = [Graph.from_graph6(record) for record in records]
    catalog = [
        encoded
        for graph in graphs
        for encoded in (graph.to_graph6(), graph.complement().to_graph6())
    ]
    candidates = catalog + [
        toggle_graph6(records[index], edge_index)
        for index in range(328)
        for edge_index in range(EDGE_COUNT)
    ]
    completed = subprocess.run(
        [str(args.labelg), "-q"],
        input="\n".join(candidates) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    canonical = completed.stdout.splitlines()
    if len(canonical) != len(candidates):
        raise AssertionError("labelg output length mismatch")
    lookup = {value: index for index, value in enumerate(canonical[:656])}
    if len(lookup) != 656:
        raise AssertionError("catalog contains duplicate unlabelled graphs")

    adjacency: list[list[dict[str, object]]] = [[] for _ in range(328)]
    safe_transitions: list[dict[str, object]] = []
    offset = 656
    for parent in range(328):
        for edge_index in range(EDGE_COUNT):
            catalog_index = lookup.get(canonical[offset])
            offset += 1
            edge = PAIRS[edge_index]
            safe = flip_is_ramsey_free(graphs[parent], edge)
            if safe != (catalog_index is not None):
                raise AssertionError(
                    f"safe flip {parent}:{edge} escapes the public catalog"
                )
            if catalog_index is None:
                continue
            child = catalog_index // 2
            complemented = bool(catalog_index % 2)
            left = toggled_graph(graphs[parent], edge)
            right = graphs[child].complement() if complemented else graphs[child]
            item: dict[str, object] = {
                "parent": parent,
                "child": child,
                "complement": complemented,
                "edge": list(edge),
                "permutation": list(find_isomorphism(left, right)),
            }
            safe_transitions.append(item)
            if child != parent:
                adjacency[parent].append(item)

    roots: list[int] = []
    transitions: list[dict[str, object]] = []
    reached: set[int] = set()
    for root in range(328):
        if root in reached:
            continue
        roots.append(root)
        reached.add(root)
        queue = deque([root])
        while queue:
            parent = queue.popleft()
            for item in adjacency[parent]:
                child = item["child"]
                if not isinstance(child, int):
                    raise AssertionError("generated child index is not an integer")
                if child in reached:
                    continue
                transitions.append(item)
                reached.add(child)
                queue.append(child)

    document: dict[str, object] = {
        "format": FORMAT,
        "roots": roots,
        "transitions": transitions,
        "safe_transitions": safe_transitions,
    }
    verify_document(document, records)
    payload = json.dumps(document, separators=(",", ":"), sort_keys=True).encode("ascii")
    write_deterministic_gzip(args.output, payload)

    with gzip.open(args.output, "rt", encoding="ascii") as compressed:
        round_trip = json.load(compressed)
    verify_document(round_trip, records)
    children = {item["child"]: item["parent"] for item in transitions}
    # Count roots by following the already verified parent pointers.
    root_counts = Counter()
    for vertex in range(328):
        while vertex in children:
            vertex = children[vertex]
        root_counts[vertex] += 1
    quotient_edges = {
        (min(parent, child), max(parent, child))
        for parent, neighbors in enumerate(adjacency)
        for item in neighbors
        for child in [item["child"]]
        if isinstance(child, int)
        if parent != child
    }

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print("R(5,5,42) catalog single-flip forest")
    print(f"  roots: {roots}")
    print(f"  component sizes: {[root_counts[root] for root in roots]}")
    print(f"  quotient flip edges: {len(quotient_edges)}")
    print(f"  safe labelled flips: {len(safe_transitions)}")
    print(f"  transitions: {len(transitions)}")
    print(f"  output bytes: {args.output.stat().st_size}")
    print(f"  sha256: {digest}")


if __name__ == "__main__":
    main()
