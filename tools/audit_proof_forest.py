#!/usr/bin/env python3
"""Audit a proof-forest snapshot and every per-root Boolean refinement cover."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from tools.export_proof_forest import (
        SCHEMA,
        file_sha256,
        read_rows_bytes,
        reconstruct_forest,
    )
    from tools.export_proof_frontier import read_cubes
    from tools.verify_cube_cover import cover_by_dpll
else:
    from export_proof_forest import (
        SCHEMA,
        file_sha256,
        read_rows_bytes,
        reconstruct_forest,
    )
    from export_proof_frontier import read_cubes
    from verify_cube_cover import cover_by_dpll


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected proof-forest schema")
    root = arguments.manifest.parent
    source = Path(document["source_cubes"]["path"])
    if file_sha256(source) != document["source_cubes"]["sha256"]:
        raise ValueError("source cube hash mismatch")
    cubes = read_cubes(source)
    if len(cubes) != int(document["source_cubes"]["count"]):
        raise ValueError("source cube count mismatch")
    snapshot = root / document["source_results"]["snapshot"]
    result_bytes = snapshot.read_bytes()
    if file_sha256(snapshot) != document["source_results"]["sha256"]:
        raise ValueError("result snapshot hash mismatch")
    forest = reconstruct_forest(cubes, read_rows_bytes(result_bytes, len(cubes)))
    closed_path = root / document["closed"]["path"]
    open_path = root / document["open"]["path"]
    if file_sha256(closed_path) != document["closed"]["sha256"]:
        raise ValueError("closed cube hash mismatch")
    if file_sha256(open_path) != document["open"]["sha256"]:
        raise ValueError("open cube hash mismatch")
    closed = read_cubes(closed_path) if document["closed"]["count"] else ()
    open_cubes = read_cubes(open_path) if document["open"]["count"] else ()
    expected_closed = tuple(cube for leaves in forest for cube in leaves.closed)
    expected_open = tuple(cube for leaves in forest for cube in leaves.open)
    if closed != expected_closed or open_cubes != expected_open:
        raise ValueError("exported leaves differ from reconstructed forest")
    if len(closed) != int(document["closed"]["count"]):
        raise ValueError("closed cube count mismatch")
    if len(open_cubes) != int(document["open"]["count"]):
        raise ValueError("open cube count mismatch")

    total_dpll_nodes = 0
    closed_offset = open_offset = 0
    for root_index, (parent, leaves, entry) in enumerate(
        zip(cubes, forest, document["roots"], strict=True)
    ):
        if int(entry["root"]) != root_index:
            raise ValueError("root manifest order mismatch")
        expected_entry = {
            "root": root_index,
            "rows": leaves.rows,
            "closed_start": closed_offset,
            "closed_count": len(leaves.closed),
            "open_start": open_offset,
            "open_count": len(leaves.open),
        }
        if entry != expected_entry:
            raise ValueError(f"root manifest mismatch at root {root_index}")
        closed_offset += len(leaves.closed)
        open_offset += len(leaves.open)
        children = leaves.closed + leaves.open
        suffixes = []
        for child in children:
            if child[: len(parent)] != parent:
                raise ValueError(f"root prefix mismatch at root {root_index}")
            suffixes.append(frozenset(child[len(parent) :]))
        covered, dpll_nodes, witness = cover_by_dpll(suffixes)
        if not covered:
            raise ValueError(
                f"leaf family does not cover root {root_index}; witness={witness}"
            )
        total_dpll_nodes += dpll_nodes
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "roots": len(cubes),
                "closed": len(closed),
                "open": len(open_cubes),
                "dpll_nodes": total_dpll_nodes,
                "all_root_refinements_cover": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
