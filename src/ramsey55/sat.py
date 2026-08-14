"""Exact CNF encoding for diagonal Ramsey(5,5) colourings."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from .graph import Graph

Clause = tuple[int, ...]


def variable_count(order: int) -> int:
    return order * (order - 1) // 2


def edge_variable(u: int, v: int) -> int:
    """One-based variable for edge {u,v}, in graph6 column-major order."""

    if u == v or u < 0 or v < 0:
        raise ValueError("an edge needs two distinct nonnegative vertices")
    if u > v:
        u, v = v, u
    return v * (v - 1) // 2 + u + 1


def clique_edge_variables(vertices: Sequence[int]) -> tuple[int, ...]:
    return tuple(edge_variable(u, v) for u, v in combinations(vertices, 2))


def ramsey55_clauses(order: int) -> Iterator[Clause]:
    """Yield the two ten-literal clauses for every five-vertex subset.

    A true variable denotes an edge of the encoded graph. The negative clause
    forbids a 5-clique; the positive clause forbids a 5-independent set.
    """

    for vertices in combinations(range(order), 5):
        variables = clique_edge_variables(vertices)
        yield tuple(-variable for variable in variables)
        yield variables


def fixed_star_clauses(order: int, degree: int) -> Iterator[Clause]:
    """Fix vertex 0 adjacent to 1..degree and nonadjacent to the rest."""

    if not 0 <= degree < order:
        raise ValueError("star degree outside graph")
    for vertex in range(1, order):
        variable = edge_variable(0, vertex)
        yield (variable,) if vertex <= degree else (-variable,)


def assignment_from_graph(graph: Graph) -> dict[int, bool]:
    return {
        edge_variable(u, v): graph.has_edge(u, v)
        for v in range(1, graph.order)
        for u in range(v)
    }


def clause_is_satisfied(clause: Clause, assignment: Mapping[int, bool]) -> bool:
    return any(
        assignment[abs(literal)] if literal > 0 else not assignment[abs(literal)]
        for literal in clause
    )


def violated_clauses(
    clauses: Iterable[Clause], assignment: Mapping[int, bool]
) -> Iterator[Clause]:
    return (
        clause for clause in clauses if not clause_is_satisfied(clause, assignment)
    )


def write_dimacs(
    path: Path,
    order: int,
    *,
    fixed_star_degree: int | None = None,
) -> tuple[int, int]:
    base_count = 2 * _binomial(order, 5)
    extra_count = order - 1 if fixed_star_degree is not None else 0
    clause_count = base_count + extra_count
    variables = variable_count(order)

    clauses: Iterable[Clause] = ramsey55_clauses(order)
    if fixed_star_degree is not None:
        clauses = _chain(clauses, fixed_star_clauses(order, fixed_star_degree))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {variables} {clause_count}\n")
        for clause in clauses:
            output.write(" ".join(map(str, clause)))
            output.write(" 0\n")
    return variables, clause_count


def _chain(first: Iterable[Clause], second: Iterable[Clause]) -> Iterator[Clause]:
    yield from first
    yield from second


def _binomial(n: int, k: int) -> int:
    if k < 0 or n < k:
        return 0
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result
