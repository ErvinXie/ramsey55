#!/usr/bin/env python3
"""Generate the exact Ramsey(5,5,n) DIMACS instance."""

from __future__ import annotations

import argparse
from pathlib import Path

from ramsey55.sat import write_dimacs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--fixed-star-degree", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    variables, clauses = write_dimacs(
        args.output,
        args.order,
        fixed_star_degree=args.fixed_star_degree,
    )
    print(f"wrote {args.output}")
    print(f"variables: {variables}")
    print(f"clauses: {clauses}")


if __name__ == "__main__":
    main()
