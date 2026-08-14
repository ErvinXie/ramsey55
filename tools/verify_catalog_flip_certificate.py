#!/usr/bin/env python3
"""Verify the catalog flip forest using only explicit graph permutations."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from generate_catalog_flip_certificate import load_graph6, verify_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--certificate",
        type=Path,
        default=Path("data/reference/r55_42_flip_forest.json.gz"),
    )
    args = parser.parse_args()

    records = load_graph6(args.graphs)
    with gzip.open(args.certificate, "rt", encoding="ascii") as compressed:
        document = json.load(compressed)
    verify_document(document, records)
    print(
        "verified 2,040 safe flips, six roots, 322 forest transitions, "
        "and all 328 representatives"
    )


if __name__ == "__main__":
    main()
