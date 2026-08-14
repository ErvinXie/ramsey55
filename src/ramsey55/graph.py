"""Small undirected graphs represented by adjacency bitsets.

The implementation deliberately depends only on the Python standard library.
It is an executable cross-check, not the final formal proof kernel. The same
definitions and certificate predicates are mirrored in Lean under formal/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence


@dataclass(frozen=True, slots=True)
class Graph:
    """A loop-free undirected graph on vertices 0 through order - 1."""

    adjacency: tuple[int, ...]

    def __post_init__(self) -> None:
        n = len(self.adjacency)
        universe = (1 << n) - 1
        for vertex, neighbors in enumerate(self.adjacency):
            if neighbors < 0 or neighbors & ~universe:
                raise ValueError(f"adjacency row {vertex} exceeds graph order")
            if neighbors & (1 << vertex):
                raise ValueError(f"loop at vertex {vertex}")
        for u, neighbors in enumerate(self.adjacency):
            for v in range(u + 1, n):
                if bool(neighbors & (1 << v)) != bool(
                    self.adjacency[v] & (1 << u)
                ):
                    raise ValueError(f"asymmetric edge ({u}, {v})")

    @property
    def order(self) -> int:
        return len(self.adjacency)

    @property
    def size(self) -> int:
        return sum(row.bit_count() for row in self.adjacency) // 2

    @property
    def degrees(self) -> tuple[int, ...]:
        return tuple(row.bit_count() for row in self.adjacency)

    def has_edge(self, u: int, v: int) -> bool:
        if not 0 <= u < self.order or not 0 <= v < self.order:
            raise IndexError("vertex outside graph")
        return bool(self.adjacency[u] & (1 << v))

    def complement(self) -> Graph:
        universe = (1 << self.order) - 1
        return Graph(
            tuple(
                universe & ~(neighbors | (1 << vertex))
                for vertex, neighbors in enumerate(self.adjacency)
            )
        )

    def clique_masks(self, size: int) -> Iterator[int]:
        """Yield every clique of the requested size exactly once."""

        if size < 0:
            raise ValueError("clique size must be nonnegative")
        if size == 0:
            yield 0
            return
        if size > self.order:
            return

        def search(candidates: int, remaining: int, chosen: int) -> Iterator[int]:
            while candidates.bit_count() >= remaining:
                vertex_bit = candidates & -candidates
                candidates ^= vertex_bit
                if remaining == 1:
                    yield chosen | vertex_bit
                    continue
                vertex = vertex_bit.bit_length() - 1
                yield from search(
                    candidates & self.adjacency[vertex],
                    remaining - 1,
                    chosen | vertex_bit,
                )

        yield from search((1 << self.order) - 1, size, 0)

    def cliques(self, size: int) -> tuple[tuple[int, ...], ...]:
        return tuple(
            tuple(v for v in range(self.order) if mask & (1 << v))
            for mask in self.clique_masks(size)
        )

    def is_ramsey_55_graph(self) -> bool:
        """Whether the graph has neither a 5-clique nor a 5-independent set."""

        return next(self.clique_masks(5), None) is None and next(
            self.complement().clique_masks(5), None
        ) is None

    def upper_triangle_bits(self) -> tuple[int, ...]:
        """Canonical labelled representation, useful for exact deduplication."""

        return tuple(
            int(self.has_edge(u, v))
            for v in range(1, self.order)
            for u in range(v)
        )

    def to_graph6(self) -> str:
        """Encode the graph in graph6 format."""

        if self.order <= 62:
            header = [self.order]
        elif self.order <= 258047:
            header = [63, self.order >> 12, self.order >> 6, self.order]
        elif self.order < 1 << 36:
            header = [63, 63]
            header.extend(self.order >> shift for shift in range(30, -1, -6))
        else:
            raise ValueError("graph6 supports fewer than 2^36 vertices")

        bits = list(self.upper_triangle_bits())
        bits.extend([0] * (-len(bits) % 6))
        payload = [
            sum(bits[offset + index] << (5 - index) for index in range(6))
            for offset in range(0, len(bits), 6)
        ]
        return "".join(chr((value & 63) + 63) for value in header + payload)

    @classmethod
    def from_edges(cls, order: int, edges: Iterable[tuple[int, int]]) -> Graph:
        adjacency = [0] * order
        for u, v in edges:
            if not 0 <= u < order or not 0 <= v < order:
                raise ValueError(f"edge ({u}, {v}) outside graph")
            if u == v:
                raise ValueError(f"loop at vertex {u}")
            adjacency[u] |= 1 << v
            adjacency[v] |= 1 << u
        return cls(tuple(adjacency))

    @classmethod
    def from_adjacency_matrix(cls, rows: Sequence[str]) -> Graph:
        order = len(rows)
        if any(len(row) != order for row in rows):
            raise ValueError("adjacency matrix must be square")
        if any(set(row) - {"0", "1"} for row in rows):
            raise ValueError("adjacency matrix must contain only 0 and 1")
        adjacency = tuple(
            sum((1 << v) for v, value in enumerate(row) if value == "1")
            for row in rows
        )
        return cls(adjacency)

    @classmethod
    def from_graph6(cls, encoded: str) -> Graph:
        """Decode the graph6 format, including all three order headers."""

        data = encoded.strip()
        if data.startswith(">>graph6<<"):
            data = data[len(">>graph6<<") :]
        if not data:
            raise ValueError("empty graph6 string")

        values = [ord(char) - 63 for char in data]
        if any(value < 0 or value > 63 for value in values):
            raise ValueError("invalid graph6 character")

        if values[0] <= 62:
            order = values[0]
            offset = 1
        elif len(values) >= 4 and values[1] <= 62:
            order = (values[1] << 12) | (values[2] << 6) | values[3]
            offset = 4
        elif len(values) >= 8:
            order = 0
            for value in values[2:8]:
                order = (order << 6) | value
            offset = 8
        else:
            raise ValueError("truncated graph6 order header")

        edge_count = order * (order - 1) // 2
        required_words = (edge_count + 5) // 6
        if len(values) - offset != required_words:
            raise ValueError(
                f"graph6 payload has {len(values) - offset} words; "
                f"expected {required_words}"
            )

        bits: list[int] = []
        for value in values[offset:]:
            bits.extend((value >> shift) & 1 for shift in range(5, -1, -1))

        edges: list[tuple[int, int]] = []
        index = 0
        for v in range(1, order):
            for u in range(v):
                if bits[index]:
                    edges.append((u, v))
                index += 1
        return cls.from_edges(order, edges)
