#!/usr/bin/env python3
"""Check every local completion represented by a generalized-graph cover."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

SCHEMA = "ramsey55.generalized-graph-cover-local-audit.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def edge_order(size: int) -> list[tuple[int, int]]:
    return [(first, second) for first in range(size) for second in range(first + 1, size)]


def decode(code: int, size: int) -> tuple[int, ...]:
    digits: list[int] = []
    value = code
    while value >= 3:
        digits.append(value % 3)
        value //= 3
    digits.reverse()
    if value != 1 or len(digits) != size * (size - 1) // 2:
        raise ValueError("invalid leading-one base-three graph code")
    return tuple(digits)


def encode(colors: tuple[int, ...]) -> int:
    value = 1
    for color in colors:
        value = value * 3 + color
    return value


def matrix(colors: tuple[int, ...], size: int) -> list[list[int]]:
    result = [[0 for _ in range(size)] for _ in range(size)]
    for (first, second), color in zip(edge_order(size), colors, strict=True):
        result[first][second] = color
        result[second][first] = color
    return result


def colors_from_matrix(graph: list[list[int]]) -> tuple[int, ...]:
    return tuple(graph[first][second] for first, second in edge_order(len(graph)))


def is_ramsey_graph(
    colors: tuple[int, ...], size: int, blue_clique: int, red_clique: int
) -> bool:
    graph = matrix(colors, size)
    for clique_size, color in ((blue_clique, 1), (red_clique, 2)):
        for vertices in itertools.combinations(range(size), clique_size):
            if all(
                graph[first][second] == color
                for first, second in itertools.combinations(vertices, 2)
            ):
                return False
    return True


def original_coordinates(
    normalized: tuple[int, ...], permutation: tuple[int, ...], size: int
) -> tuple[int, ...]:
    if sorted(permutation) != list(range(size)):
        raise ValueError("witness suffix is not a permutation")
    normal_matrix = matrix(normalized, size)
    inverse = [0] * size
    for new_vertex, old_vertex in enumerate(permutation):
        inverse[old_vertex] = new_vertex
    original = [
        [normal_matrix[inverse[first]][inverse[second]] for second in range(size)]
        for first in range(size)
    ]
    return colors_from_matrix(original)


def isomorphic(source: tuple[int, ...], target: tuple[int, ...], size: int) -> bool:
    """Exact backtracking isomorphism for complete two-colour graphs."""
    source_matrix = matrix(source, size)
    target_matrix = matrix(target, size)

    def signatures(graph: list[list[int]]) -> list[tuple[int, int]]:
        return [
            (
                sum(color == 1 for color in graph[vertex]),
                sum(color == 2 for color in graph[vertex]),
            )
            for vertex in range(size)
        ]

    source_signatures = signatures(source_matrix)
    target_signatures = signatures(target_matrix)
    if sorted(source_signatures) != sorted(target_signatures):
        return False
    candidates = {
        vertex: [
            other
            for other in range(size)
            if target_signatures[other] == source_signatures[vertex]
        ]
        for vertex in range(size)
    }
    order = sorted(range(size), key=lambda vertex: (len(candidates[vertex]), vertex))
    assignment: dict[int, int] = {}
    used: set[int] = set()

    def search(position: int) -> bool:
        if position == size:
            return True
        vertex = order[position]
        for other in candidates[vertex]:
            if other in used or any(
                source_matrix[vertex][assigned_vertex]
                != target_matrix[other][assigned_other]
                for assigned_vertex, assigned_other in assignment.items()
            ):
                continue
            assignment[vertex] = other
            used.add(other)
            if search(position + 1):
                return True
            used.remove(other)
            del assignment[vertex]
        return False

    return search(0)


def valid_completions(
    parent: tuple[int, ...], size: int, blue_clique: int, red_clique: int
) -> set[tuple[int, ...]]:
    holes = [index for index, color in enumerate(parent) if color == 0]
    result: set[tuple[int, ...]] = set()
    for assignment in itertools.product((1, 2), repeat=len(holes)):
        child = list(parent)
        for index, color in zip(holes, assignment, strict=True):
            child[index] = color
        colors = tuple(child)
        if is_ramsey_graph(colors, size, blue_clique, red_clique):
            result.add(colors)
    return result


def audit_cover(
    cover: Path,
    size: int,
    blue_clique: int,
    red_clique: int,
) -> dict[str, object]:
    lines = cover.read_text(encoding="ascii").splitlines()
    catalog: list[tuple[int, ...]] = []
    for line_number, line in enumerate(lines, 1):
        fields = line.split()
        if len(fields) < 2:
            raise ValueError(f"{cover}:{line_number}: cover row has no witnesses")
        for field in fields[1:]:
            pieces = field.split("_")
            if len(pieces) != size + 1:
                raise ValueError(f"{cover}:{line_number}: malformed witness")
            catalog.append(decode(int(pieces[0]), size))

    normalized_seen: set[int] = set()
    row_records = []
    for line_number, line in enumerate(lines, 1):
        fields = line.split()
        if len(fields) < 2:
            raise ValueError(f"{cover}:{line_number}: cover row has no witnesses")
        parent_code = int(fields[0])
        parent = decode(parent_code, size)
        listed: set[tuple[int, ...]] = set()
        normalized_codes = []
        for field in fields[1:]:
            pieces = field.split("_")
            if len(pieces) != size + 1:
                raise ValueError(f"{cover}:{line_number}: malformed witness")
            normalized_code = int(pieces[0])
            normalized = decode(normalized_code, size)
            if 0 in normalized or not is_ramsey_graph(
                normalized, size, blue_clique, red_clique
            ):
                raise ValueError(f"{cover}:{line_number}: invalid normalized child")
            original = original_coordinates(
                normalized, tuple(map(int, pieces[1:])), size
            )
            if any(
                fixed and original[index] != fixed
                for index, fixed in enumerate(parent)
            ):
                raise ValueError(f"{cover}:{line_number}: witness does not extend parent")
            if original in listed or normalized_code in normalized_seen:
                raise ValueError(f"{cover}:{line_number}: duplicate witness")
            listed.add(original)
            normalized_seen.add(normalized_code)
            normalized_codes.append(str(normalized_code))
        expected = valid_completions(parent, size, blue_clique, red_clique)
        if not listed <= expected:
            raise ValueError(
                f"{cover}:{line_number}: a listed witness is not a valid completion"
            )
        for completion in expected - listed:
            if not any(isomorphic(completion, normalized, size) for normalized in catalog):
                raise ValueError(
                    f"{cover}:{line_number}: a valid local completion is not "
                    "covered up to isomorphism"
                )
        holes = parent.count(0)
        row_records.append(
            {
                "line": line_number,
                "parent_code": str(parent_code),
                "holes": holes,
                "assignments": 2**holes,
                "valid_completions": len(expected),
                "normalized_child_codes_sha256": hashlib.sha256(
                    ("\n".join(normalized_codes) + "\n").encode("ascii")
                ).hexdigest(),
            }
        )
        print(
            f"verified row {line_number}: holes={holes} "
            f"valid_completions={len(expected)}"
        )
    if not row_records:
        raise ValueError(f"{cover}: empty cover")
    return {
        "schema": SCHEMA,
        "claim": (
            "all locally valid completions of every listed generalized graph are "
            "represented up to isomorphism; global exhaustiveness still depends "
            "on an independently checked Ramsey-graph enumeration"
        ),
        "cover": {
            "path": str(cover),
            "bytes": cover.stat().st_size,
            "sha256": file_sha256(cover),
        },
        "order": size,
        "forbidden_cliques": {"blue": blue_clique, "red": red_clique},
        "rows": row_records,
        "summary": {
            "generalized_graphs": len(row_records),
            "normalized_children": len(normalized_seen),
            "maximum_holes": max(int(record["holes"]) for record in row_records),
            "all_local_completions_covered_up_to_isomorphism": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cover", type=Path)
    parser.add_argument("--order", type=int, required=True)
    parser.add_argument("--blue-clique", type=int, required=True)
    parser.add_argument("--red-clique", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    if min(arguments.order, arguments.blue_clique, arguments.red_clique) <= 0:
        parser.error("orders and clique sizes must be positive")
    document = audit_cover(
        arguments.cover,
        arguments.order,
        arguments.blue_clique,
        arguments.red_clique,
    )
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {arguments.output}")


if __name__ == "__main__":
    main()
