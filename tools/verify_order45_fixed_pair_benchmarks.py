#!/usr/bin/env python3
"""Independently verify the complete H100/J132 benchmark manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from verify_order45_fixed_pair_cnf import sha256, verify


SCHEMA = "ramsey55.order45-fixed-pairs.v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cnf-dir", type=Path)
    arguments = parser.parse_args()
    document = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError("unexpected fixed-pair manifest schema")
    h_catalog = Path(document["h_catalog"]["path"])
    j_catalog = Path(document["j_catalog"]["path"])
    if sha256(h_catalog) != document["h_catalog"]["sha256"]:
        raise ValueError("H catalog hash differs")
    if sha256(j_catalog) != document["j_catalog"]["sha256"]:
        raise ValueError("J catalog hash differs")
    root = arguments.cnf_dir or arguments.manifest.parent
    observed_indices = []
    for formula in document["formulas"]:
        report = verify(
            SimpleNamespace(
                h_catalog=h_catalog,
                h_index=formula["h_index"],
                j_catalog=j_catalog,
                j_index=formula["j_index"],
                cnf=root / formula["path"],
                no_symmetry=True,
            )
        )
        observed_indices.append(report["j_index"])
        comparisons = {
            "h_graph6": report["h_graph6"],
            "j_graph6": report["j_graph6"],
            "variables": report["variables"],
            "clauses": report["clauses"],
            "ramsey_clauses": report["ramsey_clauses"],
            "degree_bound_clauses": report["degree_bound_clauses"],
            "symmetry_clauses": report["symmetry_clauses"],
            "sha256": report["cnf_sha256"],
        }
        for key, observed in comparisons.items():
            if formula.get(key) != observed:
                raise ValueError(f"J{formula['j_index']} {key} differs")
        print(
            f"verified J{formula['j_index']}: {report['variables']} variables, "
            f"{report['clauses']} clauses"
        )
    if observed_indices != [297775, 326185]:
        raise ValueError("manifest does not cover the complete J132 layer")


if __name__ == "__main__":
    main()
