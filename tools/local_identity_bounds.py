#!/usr/bin/env python3
"""Exact local LP bounds for the Engstrom/McKay-Radziszowski identity.

The relaxation records only the distribution of induced q-vertex subgraphs
and their mean edge count.  It is therefore a rigorous necessary condition,
not a proof that the bounds are attainable by a larger Ramsey graph.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb

from ramsey55 import Graph


EDGE_RANGES = {
    18: (50, 85),
    19: (57, 92),
    20: (68, 100),
    21: (77, 107),
    22: (88, 114),
    23: (101, 122),
    24: (116, 132),
}


@dataclass(frozen=True, slots=True)
class Features:
    edges: int
    triangles: int
    paths3: int
    cycles4: int
    stars: int
    paths4: int
    triangle_pendant: int
    diamonds: int


def features(graph: Graph) -> Features:
    triangles = paths3 = 0
    four = {"cycles4": 0, "stars": 0, "paths4": 0,
            "triangle_pendant": 0, "diamonds": 0}
    for vertices in combinations(range(graph.order), 3):
        edges = sum(graph.has_edge(u, v) for u, v in combinations(vertices, 2))
        triangles += edges == 3
        paths3 += edges == 2
    for vertices in combinations(range(graph.order), 4):
        degrees = [0] * 4
        edges = 0
        for i, j in combinations(range(4), 2):
            if graph.has_edge(vertices[i], vertices[j]):
                degrees[i] += 1
                degrees[j] += 1
                edges += 1
        signature = edges, tuple(sorted(degrees))
        name = {
            (4, (2, 2, 2, 2)): "cycles4",
            (3, (1, 1, 1, 3)): "stars",
            (3, (1, 1, 2, 2)): "paths4",
            (4, (1, 2, 2, 3)): "triangle_pendant",
            (5, (2, 2, 3, 3)): "diamonds",
        }.get(signature)
        if name is not None:
            four[name] += 1
    return Features(graph.size, triangles, paths3, **four)


def enumerate_types(order: int) -> tuple[list[Features], list[Features]]:
    pairs = tuple(combinations(range(order), 2))
    r45: list[Features] = []
    r54: list[Features] = []
    for bits in range(1 << len(pairs)):
        graph = Graph.from_edges(
            order,
            (pair for index, pair in enumerate(pairs) if bits & (1 << index)),
        )
        no_k4 = next(graph.clique_masks(4), None) is None
        no_i5 = next(graph.complement().clique_masks(5), None) is None
        no_k5 = next(graph.clique_masks(5), None) is None
        no_i4 = next(graph.complement().clique_masks(4), None) is None
        if no_k4 and no_i5:
            r45.append(features(graph))
        if no_k5 and no_i4:
            r54.append(features(graph))
    return r45, r54


def envelope(points: list[tuple[int, Fraction]], mean: Fraction, lower: bool) -> Fraction:
    best: Fraction | None = None
    for x1, y1 in points:
        for x2, y2 in points:
            if x1 == x2:
                if mean != x1:
                    continue
                value = y1
            else:
                weight = (mean - x2) / Fraction(x1 - x2)
                if not 0 <= weight <= 1:
                    continue
                value = weight * y1 + (1 - weight) * y2
            if best is None or (value < best if lower else value > best):
                best = value
    if best is None:
        raise ValueError(f"edge mean {mean} is outside the local convex hull")
    return best


def linear_feature_bound(
    larger_order: int,
    local_order: int,
    types: list[Features],
    edge_count: int,
    coefficients3: tuple[int, int],
    coefficients4: tuple[int, int, int, int, int],
    lower: bool,
) -> Fraction:
    denominator3 = comb(larger_order - 3, local_order - 3)
    denominator4 = comb(larger_order - 4, local_order - 4)
    by_edges: dict[int, Fraction] = {}
    for item in types:
        cost = Fraction(
            coefficients3[0] * item.triangles
            + coefficients3[1] * item.paths3,
            denominator3,
        ) + Fraction(
            coefficients4[0] * item.cycles4
            + coefficients4[1] * item.stars
            + coefficients4[2] * item.paths4
            + coefficients4[3] * item.triangle_pendant
            + coefficients4[4] * item.diamonds,
            denominator4,
        )
        old = by_edges.get(item.edges)
        if old is None or (cost < old if lower else cost > old):
            by_edges[item.edges] = cost
    mean_edges = Fraction(comb(local_order, 2) * edge_count, comb(larger_order, 2))
    return comb(larger_order, local_order) * envelope(
        list(by_edges.items()), mean_edges, lower
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-order", type=int, choices=(5, 6), default=6)
    parser.add_argument("--ambient", type=int, default=43)
    args = parser.parse_args()
    local = args.local_order
    ambient = args.ambient
    r45_types, r54_types = enumerate_types(local)
    print(
        f"local order {local}: {len(r45_types)} labelled R(4,5) types, "
        f"{len(r54_types)} labelled R(5,4) types"
    )

    a_bounds: dict[int, tuple[Fraction, Fraction]] = {}
    b_bounds: dict[int, tuple[Fraction, Fraction]] = {}
    for vertices, (edge_min, edge_max) in EDGE_RANGES.items():
        constant = (
            ambient * (ambient - 3) * vertices
            - (ambient * ambient + 2 * ambient - 6) * vertices**2
            + 3 * ambient * vertices**3
            - 2 * vertices**4
        )
        edge_coefficient = (
            2 * (ambient * ambient + ambient - 8)
            - 12 * (ambient - 1) * vertices
            + 12 * vertices**2
        )
        coefficients3 = (12 * (ambient - 2), 12 * (ambient + 2) - 24 * vertices)
        coefficients4 = (72, 24, 24, 24, 32)
        lows: list[tuple[Fraction, int]] = []
        highs: list[tuple[Fraction, int]] = []
        for edges in range(edge_min, edge_max + 1):
            fixed = constant + edge_coefficient * edges - 12 * edges**2
            lows.append((fixed + linear_feature_bound(
                vertices, local, r45_types, edges,
                coefficients3, coefficients4, True), edges))
            highs.append((fixed + linear_feature_bound(
                vertices, local, r45_types, edges,
                coefficients3, coefficients4, False), edges))
        low, high = min(lows), max(highs)
        a_bounds[vertices] = low[0], high[0]
        print(f"A({vertices}) [{low[0]}, {high[0]}] at edges {low[1]}/{high[1]}")

    for vertices, (z_edge_min, z_edge_max) in EDGE_RANGES.items():
        degree = ambient - 1 - vertices
        edge_min = comb(vertices, 2) - z_edge_max
        edge_max = comb(vertices, 2) - z_edge_min
        edge_coefficient = -2 * (ambient - 2) * degree + 4 * degree**2
        coefficients3 = (0, 2 * (ambient - 8) + 4 * degree)
        coefficients4 = (-8, -12, 0, -8, -24)
        lows = []
        highs = []
        for edges in range(edge_min, edge_max + 1):
            fixed = 4 * edges**2 + edge_coefficient * edges
            lows.append((fixed + linear_feature_bound(
                vertices, local, r54_types, edges,
                coefficients3, coefficients4, True), edges))
            highs.append((fixed + linear_feature_bound(
                vertices, local, r54_types, edges,
                coefficients3, coefficients4, False), edges))
        low, high = min(lows), max(highs)
        b_bounds[vertices] = low[0], high[0]
        print(f"B({vertices}) [{low[0]}, {high[0]}] at edges {low[1]}/{high[1]}")

    degrees = [
        degree
        for degree in sorted(EDGE_RANGES)
        if ambient - 1 - degree in b_bounds
    ]
    if not degrees:
        raise ValueError(
            "ambient order has no degree whose two local orders are covered"
        )
    print("combined degree bounds")
    for degree in degrees:
        lower = a_bounds[degree][0] + b_bounds[ambient - 1 - degree][0]
        upper = a_bounds[degree][1] + b_bounds[ambient - 1 - degree][1]
        print(f"  d={degree}: [{lower}, {upper}]")


if __name__ == "__main__":
    main()
