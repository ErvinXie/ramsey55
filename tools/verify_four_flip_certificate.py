#!/usr/bin/env python3
"""Check the minimal four-flip catalog certificate without nauty."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from generate_catalog_flip_certificate import load_graph6
from generate_four_flip_certificate import verify_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs", type=Path, default=Path("data/reference/r55_42some.g6")
    )
    parser.add_argument(
        "--certificate",
        type=Path,
        default=Path("data/reference/r55_42_minimal_four_flips.json.gz"),
    )
    args = parser.parse_args()
    records = load_graph6(args.graphs)
    with gzip.open(args.certificate, "rt", encoding="ascii") as source:
        document = json.load(source)
    verify_document(document, records)
    print(
        "verified 160 inclusion-minimal safe four-edge models, their proper "
        "subsets, and all explicit catalog isomorphisms"
    )


if __name__ == "__main__":
    main()
