#!/usr/bin/env python3
"""Independently reconstruct an order-45 fixed H/J pair CNF.

The generator is C++; this verifier deliberately reimplements graph6 decoding,
the reduced Ramsey clauses, cardinality counters, automorphism enumeration, and
lex-leader encoding in Python.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterable, Iterator, Sequence


Clause = tuple[int, ...]
A_SIZE = 20
B_SIZE = 24
ORDER_WITHOUT_STAR = A_SIZE + B_SIZE
PRIMARY_VARIABLES = A_SIZE * B_SIZE


def read_record(path: Path, target: int) -> str:
    index = 0
    with path.open(encoding="ascii") as stream:
        for line in stream:
            record = line.strip()
            if not record or record.startswith("#"):
                continue
            if index == target:
                return record
            index += 1
    raise ValueError(f"catalog index {target} is out of range for {path}")


def decode_short_graph6(record: str, expected_order: int) -> tuple[int, ...]:
    values = [ord(character) - 63 for character in record]
    if not values or values[0] != expected_order:
        raise ValueError(f"expected a short graph6 record of order {expected_order}")
    if any(value < 0 or value > 63 for value in values):
        raise ValueError("invalid graph6 character")
    bits = [
        (value >> shift) & 1
        for value in values[1:]
        for shift in range(5, -1, -1)
    ]
    needed = expected_order * (expected_order - 1) // 2
    if len(bits) < needed or any(bits[needed:]):
        raise ValueError("truncated graph6 record or nonzero padding")
    adjacency = [0] * expected_order
    bit = 0
    for right in range(1, expected_order):
        for left in range(right):
            if bits[bit]:
                adjacency[left] |= 1 << right
                adjacency[right] |= 1 << left
            bit += 1
    return tuple(adjacency)


def is_edge(adjacency: Sequence[int], left: int, right: int) -> bool:
    return bool((adjacency[left] >> right) & 1)


def edge_count(adjacency: Sequence[int]) -> int:
    return sum(value.bit_count() for value in adjacency) // 2


def contains_clique(adjacency: Sequence[int], size: int) -> bool:
    return any(
        all(is_edge(adjacency, left, right) for left, right in itertools.combinations(vertices, 2))
        for vertices in itertools.combinations(range(len(adjacency)), size)
    )


def find_automorphisms(adjacency: Sequence[int]) -> list[tuple[int, ...]]:
    """Enumerate automorphisms in the deterministic order used by the C++ tool."""

    size = len(adjacency)
    degrees = [value.bit_count() for value in adjacency]
    neighbour_degree_counts: list[tuple[int, ...]] = []
    for vertex in range(size):
        counts = [0] * size
        for neighbour in range(size):
            if is_edge(adjacency, vertex, neighbour):
                counts[degrees[neighbour]] += 1
        neighbour_degree_counts.append(tuple(counts))

    image = [-1] * size
    used = [False] * size
    result: list[tuple[int, ...]] = []

    def compatible(vertex: int, candidate: int) -> bool:
        if (
            used[candidate]
            or degrees[vertex] != degrees[candidate]
            or neighbour_degree_counts[vertex] != neighbour_degree_counts[candidate]
        ):
            return False
        return all(
            is_edge(adjacency, vertex, other)
            == is_edge(adjacency, candidate, image[other])
            for other in range(size)
            if image[other] >= 0
        )

    def search(assigned: int) -> None:
        if assigned == size:
            result.append(tuple(image))
            return
        vertex = -1
        candidates: list[int] = []
        for probe in range(size):
            if image[probe] >= 0:
                continue
            probe_candidates = [
                candidate for candidate in range(size) if compatible(probe, candidate)
            ]
            if not probe_candidates:
                return
            if vertex < 0 or len(probe_candidates) < len(candidates):
                vertex = probe
                candidates = probe_candidates
        for candidate in candidates:
            image[vertex] = candidate
            used[candidate] = True
            search(assigned + 1)
            used[candidate] = False
            image[vertex] = -1

    search(0)
    return result


def cross_variable(row: int, column: int) -> int:
    return row * B_SIZE + column + 1


def reduced_ramsey_clauses(
    h_adjacency: Sequence[int], j_adjacency: Sequence[int]
) -> Iterator[Clause]:
    def edge_value(left: int, right: int) -> tuple[bool, bool, int]:
        if left > right:
            left, right = right, left
        if right < A_SIZE:
            return True, is_edge(h_adjacency, left, right), 0
        if left < A_SIZE:
            return False, False, cross_variable(left, right - A_SIZE)
        j_edge = is_edge(j_adjacency, left - A_SIZE, right - A_SIZE)
        return True, not j_edge, 0

    for vertices in itertools.combinations(range(ORDER_WITHOUT_STAR), 5):
        clique: list[int] = []
        independent: list[int] = []
        clique_satisfied = False
        independent_satisfied = False
        for left, right in itertools.combinations(vertices, 2):
            fixed, value, variable = edge_value(left, right)
            if fixed:
                clique_satisfied |= not value
                independent_satisfied |= value
            else:
                clique.append(-variable)
                independent.append(variable)
        if not clique_satisfied:
            if not clique:
                raise ValueError("fixed pair contains a K5")
            yield tuple(clique)
        if not independent_satisfied:
            if not independent:
                raise ValueError("fixed pair contains an independent 5-set")
            yield tuple(independent)


def cardinality_range(
    inputs: Sequence[int], lower: int, upper: int, maximum_variable: int
) -> tuple[int, list[Clause]]:
    size = len(inputs)
    if lower < 0 or lower > upper or upper > size:
        raise ValueError("invalid cardinality range")
    if lower == 0 and upper == size:
        return maximum_variable, []
    threshold = min(size, upper + 1)
    state = [[0] * (threshold + 1) for _ in range(size + 1)]
    clauses: list[Clause] = []
    variable = maximum_variable
    for prefix in range(1, size + 1):
        item = inputs[prefix - 1]
        for count in range(1, min(prefix, threshold) + 1):
            variable += 1
            current = state[prefix][count] = variable
            if prefix == 1 and count == 1:
                clauses.extend(((-current, item), (-item, current)))
            elif count == 1:
                previous = state[prefix - 1][1]
                clauses.extend(
                    ((-previous, current), (-item, current), (-current, previous, item))
                )
            elif count == prefix:
                diagonal = state[prefix - 1][count - 1]
                clauses.extend(
                    ((-current, diagonal), (-current, item), (-diagonal, -item, current))
                )
            else:
                previous = state[prefix - 1][count]
                diagonal = state[prefix - 1][count - 1]
                clauses.extend(
                    (
                        (-previous, current),
                        (-diagonal, -item, current),
                        (-current, previous, diagonal),
                        (-current, previous, item),
                    )
                )
    if lower:
        clauses.append((state[size][lower],))
    if upper < size:
        clauses.append((-state[size][upper + 1],))
    return variable, clauses


def degree_bound_clauses(
    h_adjacency: Sequence[int], j_adjacency: Sequence[int], maximum_variable: int
) -> tuple[int, list[Clause]]:
    clauses: list[Clause] = []
    variable = maximum_variable
    for vertex in range(A_SIZE):
        fixed_degree = h_adjacency[vertex].bit_count()
        incident = [cross_variable(vertex, column) for column in range(B_SIZE)]
        variable, encoded = cardinality_range(
            incident,
            max(0, 19 - fixed_degree),
            min(B_SIZE, 23 - fixed_degree),
            variable,
        )
        clauses.extend(encoded)
    for vertex in range(B_SIZE):
        fixed_degree = B_SIZE - 1 - j_adjacency[vertex].bit_count()
        incident = [cross_variable(row, vertex) for row in range(A_SIZE)]
        variable, encoded = cardinality_range(
            incident,
            max(0, 20 - fixed_degree),
            min(A_SIZE, 24 - fixed_degree),
            variable,
        )
        clauses.extend(encoded)
    return variable, clauses


def lex_leader(
    left: Sequence[int], right: Sequence[int], maximum_variable: int
) -> tuple[int, list[Clause]]:
    differences = [pair for pair in zip(left, right) if pair[0] != pair[1]]
    clauses: list[Clause] = []
    variable = maximum_variable
    equal_prefix = 0
    for index, (left_bit, right_bit) in enumerate(differences):
        if equal_prefix == 0:
            clauses.append((-left_bit, right_bit))
        else:
            clauses.append((-equal_prefix, -left_bit, right_bit))
        if index + 1 == len(differences):
            continue
        variable += 1
        next_prefix = variable
        if equal_prefix == 0:
            clauses.extend(
                (
                    (-next_prefix, -left_bit, right_bit),
                    (-next_prefix, left_bit, -right_bit),
                    (left_bit, right_bit, next_prefix),
                    (-left_bit, -right_bit, next_prefix),
                )
            )
        else:
            clauses.extend(
                (
                    (-next_prefix, equal_prefix),
                    (-next_prefix, -left_bit, right_bit),
                    (-next_prefix, left_bit, -right_bit),
                    (-equal_prefix, left_bit, right_bit, next_prefix),
                    (-equal_prefix, -left_bit, -right_bit, next_prefix),
                )
            )
        equal_prefix = next_prefix
    return variable, clauses


def symmetry_clauses(
    h_group: Sequence[Sequence[int]],
    j_group: Sequence[Sequence[int]],
    maximum_variable: int,
) -> tuple[int, list[Clause]]:
    clauses: list[Clause] = []
    variable = maximum_variable
    h_identity = tuple(range(A_SIZE))
    j_identity = tuple(range(B_SIZE))
    left = [
        cross_variable(row, column)
        for row in range(A_SIZE)
        for column in range(B_SIZE)
    ]
    for permutation in h_group:
        if tuple(permutation) == h_identity:
            continue
        right = [
            cross_variable(permutation[row], column)
            for row in range(A_SIZE)
            for column in range(B_SIZE)
        ]
        variable, encoded = lex_leader(left, right, variable)
        clauses.extend(encoded)
    for permutation in j_group:
        if tuple(permutation) == j_identity:
            continue
        right = [
            cross_variable(row, permutation[column])
            for row in range(A_SIZE)
            for column in range(B_SIZE)
        ]
        variable, encoded = lex_leader(left, right, variable)
        clauses.extend(encoded)
    return variable, clauses


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(arguments: argparse.Namespace) -> dict[str, object]:
    h_record = read_record(arguments.h_catalog, arguments.h_index)
    j_record = read_record(arguments.j_catalog, arguments.j_index)
    h_adjacency = decode_short_graph6(h_record, A_SIZE)
    j_adjacency = decode_short_graph6(j_record, B_SIZE)
    if edge_count(h_adjacency) != 100 or edge_count(j_adjacency) != 132:
        raise ValueError("fixed pair does not belong to the H100/J132 stratum")
    if contains_clique(h_adjacency, 4) or contains_clique(j_adjacency, 4):
        raise ValueError("a fixed side contains a K4")

    h_group = find_automorphisms(h_adjacency)
    j_group = find_automorphisms(j_adjacency)
    ramsey = list(reduced_ramsey_clauses(h_adjacency, j_adjacency))
    variables, degree = degree_bound_clauses(
        h_adjacency, j_adjacency, PRIMARY_VARIABLES
    )
    if arguments.no_symmetry:
        symmetry: list[Clause] = []
    else:
        variables, symmetry = symmetry_clauses(h_group, j_group, variables)
    clause_count = len(ramsey) + len(degree) + len(symmetry)

    with arguments.cnf.open(encoding="ascii") as stream:
        comment = stream.readline().rstrip("\n")
        expected_comment = (
            f"c order-45 fixed pair J={arguments.j_index} H={arguments.h_index}"
        )
        if comment != expected_comment:
            raise ValueError(f"unexpected DIMACS comment: {comment!r}")
        header = stream.readline().split()
        expected_header = ["p", "cnf", str(variables), str(clause_count)]
        if header != expected_header:
            raise ValueError(f"header {header!r} != {expected_header!r}")
        expected: Iterable[Clause] = itertools.chain(ramsey, degree, symmetry)
        observed_count = 0
        for observed_count, clause in enumerate(expected, 1):
            fields = stream.readline().split()
            if not fields or fields[-1] != "0":
                raise ValueError(f"clause {observed_count} lacks a DIMACS terminator")
            if tuple(map(int, fields[:-1])) != clause:
                raise ValueError(f"clause {observed_count} differs")
        if stream.readline():
            raise ValueError("CNF contains trailing clauses")
    if observed_count != clause_count:
        raise ValueError("reconstructed clause count differs")

    return {
        "schema": "ramsey55.order45-fixed-pair-verification.v1",
        "h_catalog": str(arguments.h_catalog),
        "h_index": arguments.h_index,
        "h_graph6": h_record,
        "h_edges": edge_count(h_adjacency),
        "h_automorphisms": len(h_group),
        "j_catalog": str(arguments.j_catalog),
        "j_index": arguments.j_index,
        "j_graph6": j_record,
        "j_edges": edge_count(j_adjacency),
        "j_automorphisms": len(j_group),
        "variables": variables,
        "ramsey_clauses": len(ramsey),
        "degree_bound_clauses": len(degree),
        "symmetry_clauses": len(symmetry),
        "symmetry_enabled": not arguments.no_symmetry,
        "clauses": clause_count,
        "cnf_sha256": sha256(arguments.cnf),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("h_catalog", type=Path)
    parser.add_argument("h_index", type=int)
    parser.add_argument("j_catalog", type=Path)
    parser.add_argument("j_index", type=int)
    parser.add_argument("cnf", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-symmetry", action="store_true")
    arguments = parser.parse_args()
    report = verify(arguments)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
