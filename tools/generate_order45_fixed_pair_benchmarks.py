#!/usr/bin/env python3
"""Generate the complete H100/J132 fixed-pair benchmark family."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from analyze_order45_excess_coverage import short_graph6_order_and_size


SCHEMA = "ramsey55.order45-fixed-pairs.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def records(path: Path) -> list[str]:
    with path.open(encoding="ascii") as stream:
        return [
            line.strip()
            for line in stream
            if line.strip() and not line.startswith("#")
        ]


def parse_statistics(output: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in output.splitlines():
        fields = line.split("\t", 1)
        if len(fields) == 2 and fields[1].isdigit():
            result[fields[0]] = int(fields[1])
    required = {
        "J",
        "H",
        "variables",
        "ramsey_clauses",
        "degree_bound_clauses",
        "symmetry_clauses",
    }
    missing = required - result.keys()
    if missing:
        raise ValueError(f"generator omitted statistics {sorted(missing)}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generator", type=Path, default=Path("build/generate_order45_fixed_pair_cnf")
    )
    parser.add_argument(
        "--h-catalog", type=Path, default=Path("data/reference/r4520.100.g6")
    )
    parser.add_argument(
        "--j-catalog", type=Path, default=Path("data/reference/r45_24.g6")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/order45-fixed-pairs")
    )
    parser.add_argument(
        "--symmetry",
        action="store_true",
        help="emit independently verifiable lex-leader constraints",
    )
    arguments = parser.parse_args()

    h_records = records(arguments.h_catalog)
    if len(h_records) != 1 or short_graph6_order_and_size(h_records[0]) != (20, 100):
        raise ValueError("H catalog must be the unique 20-vertex 100-edge layer")
    j_records = records(arguments.j_catalog)
    j_indices = [
        index
        for index, record in enumerate(j_records)
        if short_graph6_order_and_size(record) == (24, 132)
    ]
    if j_indices != [297775, 326185]:
        raise ValueError(f"unexpected complete J132 layer: {j_indices}")

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    formulas = []
    for j_index in j_indices:
        suffix = "sym" if arguments.symmetry else "nosym"
        path = arguments.output_dir / f"h0-j{j_index}-{suffix}.cnf"
        command = [
            str(arguments.generator),
            str(arguments.j_catalog),
            str(j_index),
            str(arguments.h_catalog),
            "0",
            str(path),
        ]
        if not arguments.symmetry:
            command.append("--no-symmetry")
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        statistics = parse_statistics(completed.stdout)
        clauses = (
            statistics["ramsey_clauses"]
            + statistics["degree_bound_clauses"]
            + statistics["symmetry_clauses"]
        )
        formulas.append(
            {
                "h_index": 0,
                "h_graph6": h_records[0],
                "j_index": j_index,
                "j_graph6": j_records[j_index],
                "path": path.name,
                "variables": statistics["variables"],
                "clauses": clauses,
                "ramsey_clauses": statistics["ramsey_clauses"],
                "degree_bound_clauses": statistics["degree_bound_clauses"],
                "symmetry_clauses": statistics["symmetry_clauses"],
                "sha256": file_sha256(path),
                **(
                    {
                        "h_automorphisms": statistics["H_automorphisms"],
                        "j_automorphisms": statistics["J_automorphisms"],
                    }
                    if arguments.symmetry
                    else {}
                ),
            }
        )
        print(f"generated {path}: {statistics['variables']} variables, {clauses} clauses")

    document = {
        "schema": SCHEMA,
        "order": 45,
        "fixed_star_degree": 20,
        "degree_window": [20, 24],
        "h_layer": {"order": 20, "edges": 100, "records": 1},
        "j_layer": {"order": 24, "edges": 132, "records": len(j_indices)},
        "coverage": (
            "lex leaders for all labelled gluings of the complete unlabelled "
            "H100/J132 layers; requires the finite-orbit symmetry bridge"
            if arguments.symmetry
            else "all labelled gluings of the complete unlabelled H100/J132 layers"
        ),
        "symmetry_breaking": arguments.symmetry,
        "h_catalog": {
            "path": str(arguments.h_catalog),
            "sha256": file_sha256(arguments.h_catalog),
        },
        "j_catalog": {
            "path": str(arguments.j_catalog),
            "sha256": file_sha256(arguments.j_catalog),
            "records": len(j_records),
        },
        "formulas": formulas,
    }
    manifest = arguments.output_dir / "manifest.json"
    manifest.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest}")


if __name__ == "__main__":
    main()
