#!/usr/bin/env python3
"""Compose the exact two-flip scan with the checked single-flip closure."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import subprocess

from generate_catalog_flip_certificate import load_graph6, verify_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--forest",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    parser.add_argument(
        "--scanner", type=Path, default=Path("build/catalog_two_flip_scan")
    )
    parser.add_argument("--jobs", type=int, default=10)
    args = parser.parse_args()

    records = load_graph6(args.graphs)
    with gzip.open(args.forest, "rt", encoding="ascii") as compressed:
        forest = json.load(compressed)
    verify_document(forest, records)

    scanned = subprocess.run(
        [str(args.scanner), str(args.graphs), str(args.jobs)],
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    candidates = [line for line in scanned.splitlines() if line.startswith("candidate\t")]
    summary = {
        fields[0]: int(fields[1])
        for line in scanned.splitlines()
        if len(fields := line.split("\t")) == 2
    }
    expected = {
        "representatives": 328,
        "near_one_five_sets": 3940161,
        "near_two_five_sets": 19436558,
        "safe_single_flips": 2040,
        "safe_two_flips": 5568,
        "safe_two_flips_without_safe_intermediate": 0,
    }
    if summary != expected or candidates:
        raise AssertionError(f"unexpected two-flip census: {summary}, {candidates}")

    print("safe two-edge flip census")
    print("  all safe pairs: 5,568")
    print("  without a safe single intermediate: 0")
    print("  consequence: every safe double flip returns to the public catalog")


if __name__ == "__main__":
    main()
