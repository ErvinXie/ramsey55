#!/usr/bin/env python3
"""Audit the public extreme-catalog coverage of the order-45 excess split.

The global three-vertex identity guarantees a vertex with nonpositive local
contribution.  Up to colour complementation, its degree is 20, 21, or 22.
This script compares the elementary edge-sum threshold for each of those
three local splits with the edge layers present in McKay's public
``r45extreme`` archive.

An available pair here is only a pair of unlabelled local graph records.  It
is not a compatible gluing, and the report is therefore a coverage audit,
not an upper-bound certificate.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from math import comb
from pathlib import Path
import re
from typing import Mapping


EDGE_RANGES = {
    20: (68, 100),
    21: (77, 107),
    22: (88, 114),
    23: (101, 122),
    24: (116, 132),
}
WITNESS_DEGREES = (20, 21, 22)
LAYER_PATTERN = re.compile(r"r45(\d+)\.(\d+)\.g6")


@dataclass(frozen=True, slots=True)
class SplitCoverage:
    degree: int
    other_order: int
    doubled_constant: int
    minimum_edge_sum: int
    possible_pairs: tuple[tuple[int, int], ...]
    available_pairs: tuple[tuple[int, int], ...]
    raw_available_record_pairs: int
    symmetry_reduced_record_pairs: int | None

    def as_json(self) -> dict[str, object]:
        available_set = set(self.available_pairs)
        return {
            "degree": self.degree,
            "other_order": self.other_order,
            "doubled_constant": self.doubled_constant,
            "minimum_edge_sum": self.minimum_edge_sum,
            "possible_edge_pairs": [list(pair) for pair in self.possible_pairs],
            "available_edge_pairs": [list(pair) for pair in self.available_pairs],
            "missing_edge_pairs": [
                list(pair)
                for pair in self.possible_pairs
                if pair not in available_set
            ],
            "raw_available_record_pairs": self.raw_available_record_pairs,
            "symmetry_reduced_record_pairs": self.symmetry_reduced_record_pairs,
        }


def doubled_local_constant(degree: int) -> int:
    """Return twice the constant part of the order-45 local contribution."""

    return (44 - degree) * (43 - degree) - degree * (45 - 2 * degree)


def minimum_edge_sum(degree: int) -> int:
    """Integral edge threshold forced by a nonpositive local contribution."""

    constant = doubled_local_constant(degree)
    return (constant + 1) // 2


def count_records(path: Path) -> int:
    with path.open("r", encoding="ascii") as stream:
        return sum(1 for line in stream if line.strip() and not line.startswith("#"))


def short_graph6_order_and_size(record: str) -> tuple[int, int]:
    """Read order and edge count without constructing adjacency rows."""

    text = record.strip()
    if not text:
        raise ValueError("empty graph6 record")
    values = [ord(character) - 63 for character in text]
    if any(value < 0 or value > 63 for value in values):
        raise ValueError("invalid graph6 character")
    order = values[0]
    if not 0 <= order <= 62:
        raise ValueError("the extreme archive should use short graph6 headers")
    bits = comb(order, 2)
    words = (bits + 5) // 6
    if len(values) != words + 1:
        raise ValueError("incorrect short graph6 payload length")
    full_words, remainder = divmod(bits, 6)
    size = sum(value.bit_count() for value in values[1 : 1 + full_words])
    if remainder:
        final = values[-1]
        padding = 6 - remainder
        if final & ((1 << padding) - 1):
            raise ValueError("nonzero graph6 padding")
        size += (final >> padding).bit_count()
    return order, size


def catalog_histograms(
    root: Path, complete24: Path | None = None
) -> dict[int, Counter[int]]:
    """Count every explicitly available edge layer in an extracted archive."""

    histograms: dict[int, Counter[int]] = {}
    for path in sorted(root.glob("r45*.g6")):
        match = LAYER_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        order, edges = map(int, match.groups())
        histograms.setdefault(order, Counter())[edges] = count_records(path)

    complete24_path = complete24 or root / "r4524.all.g6"
    if complete24_path.exists():
        histogram: Counter[int] = Counter()
        with complete24_path.open("r", encoding="ascii") as stream:
            for line in stream:
                if not line.strip() or line.startswith("#"):
                    continue
                order, edges = short_graph6_order_and_size(line)
                if order != 24:
                    raise ValueError("r4524.all.g6 contains a graph of the wrong order")
                histogram[edges] += 1
        histograms[24] = histogram
    return histograms


def analyze_split(
    degree: int, histograms: Mapping[int, Mapping[int, int]]
) -> SplitCoverage:
    if degree not in WITNESS_DEGREES:
        raise ValueError("the normalized witness degree must be 20, 21, or 22")
    other = 44 - degree
    left_min, left_max = EDGE_RANGES[degree]
    right_min, right_max = EDGE_RANGES[other]
    threshold = minimum_edge_sum(degree)
    possible = tuple(
        (left, right)
        for left in range(left_min, left_max + 1)
        for right in range(right_min, right_max + 1)
        if left + right >= threshold
    )
    left_histogram = histograms.get(degree, {})
    right_histogram = histograms.get(other, {})
    available = tuple(
        (left, right)
        for left, right in possible
        if left in left_histogram and right in right_histogram
    )
    raw_pairs = sum(
        left_histogram[left] * right_histogram[right]
        for left, right in available
    )

    symmetry_reduced: int | None = None
    if degree == other:
        selected_records = sum(
            count
            for edges, count in left_histogram.items()
            if any(edges == left or edges == right for left, right in available)
        )
        # Every available high-layer pair in the current d=22 archive clears
        # the threshold.  Keep this guard so the formula cannot silently be
        # reused if different layers are supplied later.
        selected_edges = {
            edge for pair in available for edge in pair
        }
        if all(
            left + right >= threshold
            for left in selected_edges
            for right in selected_edges
        ):
            symmetry_reduced = selected_records * (selected_records + 1) // 2

    return SplitCoverage(
        degree=degree,
        other_order=other,
        doubled_constant=doubled_local_constant(degree),
        minimum_edge_sum=threshold,
        possible_pairs=possible,
        available_pairs=available,
        raw_available_record_pairs=raw_pairs,
        symmetry_reduced_record_pairs=symmetry_reduced,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "catalog_root",
        nargs="?",
        type=Path,
        default=Path("build/r45extreme-data/r45extreme"),
    )
    parser.add_argument(
        "--complete24",
        type=Path,
        default=Path("data/reference/r45_24.g6"),
        help="complete R(4,5,24) catalog (not included in r45extreme.tar.gz)",
    )
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()

    histograms = catalog_histograms(arguments.catalog_root, arguments.complete24)
    missing_orders = [order for order in EDGE_RANGES if order not in histograms]
    if missing_orders:
        raise ValueError(f"catalog archive lacks orders {missing_orders}")
    reports = [analyze_split(degree, histograms) for degree in WITNESS_DEGREES]
    if arguments.json:
        print(
            json.dumps(
                {
                    "catalog_root": str(arguments.catalog_root),
                    "available_layer_counts": {
                        str(order): dict(sorted(histogram.items()))
                        for order, histogram in sorted(histograms.items())
                        if order in EDGE_RANGES
                    },
                    "splits": [report.as_json() for report in reports],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print("degree other threshold edge-pairs available raw-record-pairs symmetry-reduced")
    for report in reports:
        symmetry = (
            "-"
            if report.symmetry_reduced_record_pairs is None
            else str(report.symmetry_reduced_record_pairs)
        )
        print(
            report.degree,
            report.other_order,
            report.minimum_edge_sum,
            len(report.possible_pairs),
            len(report.available_pairs),
            report.raw_available_record_pairs,
            symmetry,
        )


if __name__ == "__main__":
    main()
