"""Executable checks for the three-vertex Ramsey excess identity."""

from __future__ import annotations

from .graph import Graph


def doubled_local_excess(graph: Graph, vertex: int) -> int:
    """Twice the local contribution at ``vertex`` for ambient graph order."""

    if not 0 <= vertex < graph.order:
        raise IndexError("vertex outside graph")
    neighbours = graph.adjacency[vertex]
    universe = (1 << graph.order) - 1
    nonneighbours = universe & ~(neighbours | (1 << vertex))

    def induced_edges(vertices: int) -> int:
        return sum(
            (graph.adjacency[v] & vertices).bit_count()
            for v in range(graph.order)
            if vertices & (1 << v)
        ) // 2

    degree = neighbours.bit_count()
    return (
        2 * induced_edges(nonneighbours)
        - 2 * induced_edges(neighbours)
        - degree * (graph.order - 2 * degree)
    )


def verify_global_excess_identity(graph: Graph) -> bool:
    """Check that all doubled local contributions sum to zero."""

    return sum(doubled_local_excess(graph, v) for v in range(graph.order)) == 0
