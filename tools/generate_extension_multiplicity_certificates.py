#!/usr/bin/env python3
"""Generate covers proving at least two violations in every apex attachment."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from ramsey55 import (
    ExtensionBranch,
    ExtensionLeaf,
    ExtensionMultiplicityCertificate,
    ExtensionMultiplicityLeaf,
    Graph,
    generate_extension_multiplicity_certificate,
    verify_extension_multiplicity_certificate,
)


FORMAT = "ramsey55-extension-multiplicity-cover-v1"
MULTIPLICITY = 2


def encode_witness(witness: ExtensionLeaf) -> list[int]:
    return [int(witness.color), *witness.vertices]


def decode_witness(encoded: list[int]) -> ExtensionLeaf:
    if len(encoded) != 5 or encoded[0] not in (0, 1):
        raise ValueError(f"invalid multiplicity witness: {encoded!r}")
    return ExtensionLeaf(bool(encoded[0]), tuple(encoded[1:5]))  # type: ignore[arg-type]


def encode_certificate(
    certificate: ExtensionMultiplicityCertificate,
) -> list[list[object]]:
    encoded: list[list[object]] = []
    for node in certificate.nodes:
        if isinstance(node, ExtensionMultiplicityLeaf):
            encoded.append([0, *(encode_witness(w) for w in node.witnesses)])
        else:
            encoded.append([1, node.vertex, node.true_child, node.false_child])
    return encoded


def decode_certificate(
    encoded: list[list[object]],
) -> ExtensionMultiplicityCertificate:
    nodes: list[ExtensionMultiplicityLeaf | ExtensionBranch] = []
    for item in encoded:
        if len(item) == 3 and item[0] == 0:
            first, second = item[1], item[2]
            if not isinstance(first, list) or not isinstance(second, list):
                raise ValueError(f"invalid multiplicity leaf: {item!r}")
            nodes.append(
                ExtensionMultiplicityLeaf(
                    (decode_witness(first), decode_witness(second))
                )
            )
        elif len(item) == 4 and item[0] == 1:
            if not all(isinstance(value, int) for value in item[1:]):
                raise ValueError(f"invalid multiplicity branch: {item!r}")
            nodes.append(ExtensionBranch(item[1], item[2], item[3]))  # type: ignore[arg-type]
        else:
            raise ValueError(f"invalid multiplicity node: {item!r}")
    return ExtensionMultiplicityCertificate(MULTIPLICITY, tuple(nodes))


def load_graph6(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def write_deterministic_gzip(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graphs",
        type=Path,
        default=Path("data/reference/r55_42some.g6"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/r55_42_extension_two_covers.json.gz"),
    )
    args = parser.parse_args()

    graph6_records = load_graph6(args.graphs)
    if len(graph6_records) != 328:
        raise ValueError(f"expected 328 representatives, found {len(graph6_records)}")

    records: list[dict[str, object]] = []
    total_branches = 0
    total_leaves = 0
    largest = 0
    started = time.monotonic()

    for index, graph6 in enumerate(graph6_records):
        graph = Graph.from_graph6(graph6)
        certificate = generate_extension_multiplicity_certificate(
            graph, MULTIPLICITY
        )
        if not verify_extension_multiplicity_certificate(graph, certificate):
            raise AssertionError(f"generated certificate {index} failed verification")
        if not verify_extension_multiplicity_certificate(
            graph.complement(), certificate.complement()
        ):
            raise AssertionError(f"complement certificate {index} failed verification")

        total_branches += certificate.branch_count
        total_leaves += certificate.leaf_count
        largest = max(largest, len(certificate.nodes))
        records.append({"graph6": graph6, "nodes": encode_certificate(certificate)})

    document = {
        "format": FORMAT,
        "multiplicity": MULTIPLICITY,
        "records": records,
    }
    payload = json.dumps(document, separators=(",", ":"), sort_keys=True).encode("ascii")
    write_deterministic_gzip(args.output, payload)

    with gzip.open(args.output, "rb") as compressed:
        decoded = json.loads(compressed.read())
    if (
        decoded.get("format") != FORMAT
        or decoded.get("multiplicity") != MULTIPLICITY
        or len(decoded.get("records", [])) != 328
    ):
        raise AssertionError("serialized multiplicity certificate did not round-trip")
    for index, record in enumerate(decoded["records"]):
        graph = Graph.from_graph6(record["graph6"])
        certificate = decode_certificate(record["nodes"])
        if not verify_extension_multiplicity_certificate(graph, certificate):
            raise AssertionError(f"serialized certificate {index} failed verification")

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print("R(5,5,42) two-violation extension covers")
    print(f"  representatives: {len(records)}")
    print(f"  complements covered by colour duality: {len(records)}")
    print(f"  branches/leaves: {total_branches}/{total_leaves}")
    print(f"  largest tree: {largest} nodes")
    print(f"  output bytes: {args.output.stat().st_size}")
    print(f"  sha256: {digest}")
    print(f"  elapsed: {time.monotonic() - started:.2f}s")


if __name__ == "__main__":
    main()
