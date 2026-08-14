"""Deterministic normalization for the two order-45 degree branches.

This module handles the graph-theoretic symmetry step after the standard
Ramsey degree window ``20 <= d(v) <= 24`` has been established.  It does not
claim to prove that window; the final formal proof must connect it to
``R(4,5) = 25``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .graph import Graph


ORDER45_BRANCH_DEGREES = (20, 22)
ORDER45_EXCESS_WITNESS_DEGREES = (20, 21, 22)


def doubled_order45_local_excess_constant(degree: int) -> int:
    """Twice the edge-independent part of the local excess contribution."""

    return (44 - degree) * (43 - degree) - degree * (45 - 2 * degree)


def order45_excess_minimum_edge_sum(degree: int) -> int:
    """Minimum ``e(H)+e(J)`` when the local contribution is nonpositive."""

    if degree not in range(20, 25):
        raise ValueError("order-45 Ramsey degree must be between 20 and 24")
    constant = doubled_order45_local_excess_constant(degree)
    return (constant + 1) // 2


@dataclass(frozen=True, slots=True)
class NormalizedOrder45Graph:
    """An order-45 graph in one of the two canonical fixed-star branches."""

    graph: Graph
    source_vertex: int
    complemented: bool
    degree: int


def relabel_with_star_at_zero(graph: Graph, vertex: int) -> Graph:
    """Relabel ``vertex`` to 0, followed by its neighbours, then nonneighbours."""

    if not 0 <= vertex < graph.order:
        raise IndexError("vertex outside graph")
    neighbours = [
        other
        for other in range(graph.order)
        if other != vertex and graph.has_edge(vertex, other)
    ]
    nonneighbours = [
        other
        for other in range(graph.order)
        if other != vertex and not graph.has_edge(vertex, other)
    ]
    old_vertices = [vertex, *neighbours, *nonneighbours]
    new_vertex = {old: new for new, old in enumerate(old_vertices)}
    return Graph.from_edges(
        graph.order,
        (
            (new_vertex[u], new_vertex[v])
            for v in range(1, graph.order)
            for u in range(v)
            if graph.has_edge(u, v)
        ),
    )


def normalize_order45_degree_branch(graph: Graph) -> NormalizedOrder45Graph:
    """Normalize a degree-window order-45 graph to branch 20 or 22.

    The handshake identity makes the sum of the 45 degrees even, so not all
    degrees can be odd.  An even degree in the window is 20, 22, or 24.  In
    the last case colour complementation changes that degree to 20.  Finally,
    a deterministic relabelling gives exactly the fixed-star convention used
    by the CNF generator.
    """

    if graph.order != 45:
        raise ValueError("order-45 normalization requires exactly 45 vertices")
    degrees = graph.degrees
    if any(degree < 20 or degree > 24 for degree in degrees):
        raise ValueError("graph does not satisfy the Ramsey(5,5,45) degree window")
    if sum(degrees) != 2 * graph.size or sum(degrees) % 2:
        raise AssertionError("undirected graph violates the handshake identity")

    even_vertices = [
        vertex for vertex, degree in enumerate(degrees) if degree % 2 == 0
    ]
    if not even_vertices:
        raise AssertionError("45 odd degrees cannot have an even sum")

    source_vertex = even_vertices[0]
    degree = degrees[source_vertex]
    complemented = degree == 24
    normalized_source = graph.complement() if complemented else graph
    normalized_degree = normalized_source.degrees[source_vertex]
    if normalized_degree not in ORDER45_BRANCH_DEGREES:
        raise AssertionError("even degree did not normalize to branch 20 or 22")

    normalized = relabel_with_star_at_zero(normalized_source, source_vertex)
    if normalized.degrees[0] != normalized_degree:
        raise AssertionError("star relabelling changed the distinguished degree")
    if any(not normalized.has_edge(0, vertex) for vertex in range(1, normalized_degree + 1)):
        raise AssertionError("canonical neighbours are not an initial interval")
    if any(normalized.has_edge(0, vertex) for vertex in range(normalized_degree + 1, 45)):
        raise AssertionError("canonical nonneighbours are not a final interval")
    return NormalizedOrder45Graph(
        normalized,
        source_vertex,
        complemented,
        normalized_degree,
    )
