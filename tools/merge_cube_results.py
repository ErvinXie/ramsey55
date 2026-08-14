#!/usr/bin/env python3
"""Merge a second solve pass over the UNKNOWN rows of a first pass."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Row:
    status: int
    seconds: float
    model: str


def read_results(path: Path) -> list[Row]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "cube\tstatus\tseconds\tmodel":
        raise ValueError(f"invalid result header in {path}")
    rows: list[Row] = []
    for expected, line in enumerate(lines[1:]):
        fields = line.split("\t")
        if len(fields) < 3 or int(fields[0]) != expected:
            raise ValueError(f"invalid result row in {path}")
        status = int(fields[1])
        if status not in (0, 10, 20):
            raise ValueError(f"unexpected solver status {status}")
        rows.append(Row(status, float(fields[2]), fields[3] if len(fields) > 3 else ""))
    return rows


def merge_results(primary: list[Row], secondary: list[Row]) -> list[Row]:
    if any(row.status == 10 for row in primary):
        raise ValueError("primary results contain a SAT candidate")
    if len(secondary) != sum(row.status == 0 for row in primary):
        raise ValueError("secondary row count does not match primary UNKNOWN count")
    secondary_iterator = iter(secondary)
    merged = [
        next(secondary_iterator) if row.status == 0 else row for row in primary
    ]
    if any(row.status == 10 for row in merged):
        raise ValueError("merged results contain a SAT candidate")
    return merged


def write_results(path: Path, rows: list[Row]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as output:
        output.write("cube\tstatus\tseconds\tmodel\n")
        for index, row in enumerate(rows):
            output.write(
                f"{index}\t{row.status}\t{row.seconds:.6f}\t{row.model}\n"
            )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary", type=Path)
    parser.add_argument("secondary", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    merged = merge_results(
        read_results(arguments.primary), read_results(arguments.secondary)
    )
    write_results(arguments.output, merged)
    print(
        f"merged {len(merged)} rows: "
        f"closed={sum(row.status == 20 for row in merged)} "
        f"unknown={sum(row.status == 0 for row in merged)}"
    )


if __name__ == "__main__":
    main()
