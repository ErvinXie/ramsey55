"""Certificates that a Ramsey graph has no one-vertex extension.

For a graph ``G`` on ``n`` vertices, an attachment is an ``n``-bit mask.  Bit
``v`` is the colour of the edge from a new apex to vertex ``v``.  If four
vertices form a clique of colour ``c`` in ``G`` and all four attachment bits
are also ``c``, those vertices together with the apex form a monochromatic
``K5``.

An :class:`ExtensionCertificate` is a complete binary decision tree over the
attachment bits.  Every leaf names such a monochromatic ``K4`` whose four
bits have already been fixed to its colour.  Checking the tree is deliberately
much simpler than finding it, which makes the format suitable for mirroring
inside a proof assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .graph import Graph


@dataclass(frozen=True, slots=True)
class ExtensionLeaf:
    """A leaf covered by a monochromatic K4 of the given colour."""

    color: bool
    vertices: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class ExtensionBranch:
    """A branch on one attachment bit; children are earlier node indices."""

    vertex: int
    true_child: int
    false_child: int


ExtensionNode = ExtensionLeaf | ExtensionBranch


@dataclass(frozen=True, slots=True)
class ExtensionCertificate:
    """A postorder array of cover-tree nodes, with the root stored last."""

    nodes: tuple[ExtensionNode, ...]

    @property
    def root(self) -> int:
        if not self.nodes:
            raise ValueError("an extension certificate cannot be empty")
        return len(self.nodes) - 1

    @property
    def leaf_count(self) -> int:
        return sum(isinstance(node, ExtensionLeaf) for node in self.nodes)

    @property
    def branch_count(self) -> int:
        return sum(isinstance(node, ExtensionBranch) for node in self.nodes)

    def complement(self) -> ExtensionCertificate:
        """Transform a certificate for ``G`` into one for its complement."""

        complemented: list[ExtensionNode] = []

        def visit(node_index: int) -> int:
            node = self.nodes[node_index]
            result = len(complemented)
            if isinstance(node, ExtensionLeaf):
                complemented.append(ExtensionLeaf(not node.color, node.vertices))
                return result

            # Complementing the whole colouring also complements every apex
            # edge, so the true and false subtrees exchange roles.
            true_child = visit(node.false_child)
            false_child = visit(node.true_child)
            result = len(complemented)
            complemented.append(ExtensionBranch(node.vertex, true_child, false_child))
            return result

        root = visit(self.root)
        if root != len(complemented) - 1:
            raise AssertionError("complemented certificate root is not last")
        return ExtensionCertificate(tuple(complemented))


@dataclass(frozen=True, slots=True)
class ExtensionMultiplicityLeaf:
    """A leaf carrying several distinct monochromatic-K4 witnesses."""

    witnesses: tuple[ExtensionLeaf, ...]


ExtensionMultiplicityNode = ExtensionMultiplicityLeaf | ExtensionBranch


@dataclass(frozen=True, slots=True)
class ExtensionMultiplicityCertificate:
    """A decision tree proving a lower bound on apex violations."""

    multiplicity: int
    nodes: tuple[ExtensionMultiplicityNode, ...]

    def __post_init__(self) -> None:
        if self.multiplicity < 1:
            raise ValueError("certificate multiplicity must be positive")

    @property
    def root(self) -> int:
        if not self.nodes:
            raise ValueError("an extension certificate cannot be empty")
        return len(self.nodes) - 1

    @property
    def leaf_count(self) -> int:
        return sum(
            isinstance(node, ExtensionMultiplicityLeaf) for node in self.nodes
        )

    @property
    def branch_count(self) -> int:
        return sum(isinstance(node, ExtensionBranch) for node in self.nodes)

    def complement(self) -> ExtensionMultiplicityCertificate:
        """Transform a multiplicity certificate under colour complementation."""

        complemented: list[ExtensionMultiplicityNode] = []

        def visit(node_index: int) -> int:
            node = self.nodes[node_index]
            if isinstance(node, ExtensionMultiplicityLeaf):
                result = len(complemented)
                complemented.append(
                    ExtensionMultiplicityLeaf(
                        tuple(
                            ExtensionLeaf(not witness.color, witness.vertices)
                            for witness in node.witnesses
                        )
                    )
                )
                return result

            true_child = visit(node.false_child)
            false_child = visit(node.true_child)
            result = len(complemented)
            complemented.append(ExtensionBranch(node.vertex, true_child, false_child))
            return result

        root = visit(self.root)
        if root != len(complemented) - 1:
            raise AssertionError("complemented certificate root is not last")
        return ExtensionMultiplicityCertificate(
            self.multiplicity, tuple(complemented)
        )


class ExtensionMultiplicityCounterexample(ValueError):
    """An attachment refuting a proposed lower bound on violations."""

    def __init__(self, attachment: tuple[bool, ...], violation_count: int) -> None:
        self.attachment = attachment
        self.violation_count = violation_count
        super().__init__(
            f"attachment has only {violation_count} monochromatic K5s: "
            f"{attachment}"
        )


def _monochromatic_four_clauses(graph: Graph) -> tuple[tuple[bool, int], ...]:
    """Return pairs ``(colour, vertex_mask)`` for all monochromatic K4s."""

    return tuple((True, mask) for mask in graph.clique_masks(4)) + tuple(
        (False, mask) for mask in graph.complement().clique_masks(4)
    )


def generate_extension_certificate(graph: Graph) -> ExtensionCertificate:
    """Find a complete decision-tree proof that ``graph`` cannot be extended.

    A ``ValueError`` is raised if the search instead finds a valid attachment.
    The branching heuristic is deterministic, so the serialized result is
    reproducible across runs and Python hash seeds.
    """

    clauses = _monochromatic_four_clauses(graph)
    order = graph.order
    nodes: list[ExtensionNode] = []

    def append_leaf(color: bool, mask: int) -> int:
        vertices = tuple(v for v in range(order) if mask & (1 << v))
        if len(vertices) != 4:
            raise AssertionError("a monochromatic-four mask must have four bits")
        node_index = len(nodes)
        nodes.append(ExtensionLeaf(color, vertices))  # type: ignore[arg-type]
        return node_index

    def search(true_mask: int, false_mask: int) -> int:
        assigned = true_mask | false_mask
        unresolved: list[tuple[int, bool, int]] = []

        for color, mask in clauses:
            # A K4 is already harmless if at least one apex edge has the
            # opposite colour.  Otherwise its unassigned vertices remain a
            # clause that must eventually receive an opposite-colour bit.
            if mask & (false_mask if color else true_mask):
                continue
            remaining = mask & ~assigned
            if remaining == 0:
                return append_leaf(color, mask)
            unresolved.append((remaining.bit_count(), color, remaining))

        if not unresolved:
            attachment = tuple(
                bool(true_mask & (1 << vertex)) for vertex in range(order)
            )
            raise ValueError(
                "graph has a Ramsey-free one-vertex extension with attachment "
                f"{attachment}"
            )

        shortest = min(length for length, _, _ in unresolved)
        scores = [0] * order
        for length, _, remaining in unresolved:
            if length > shortest + 1:
                continue
            while remaining:
                bit = remaining & -remaining
                remaining -= bit
                scores[bit.bit_length() - 1] += 1

        vertex = max(range(order), key=scores.__getitem__)
        bit = 1 << vertex
        true_child = search(true_mask | bit, false_mask)
        false_child = search(true_mask, false_mask | bit)
        node_index = len(nodes)
        nodes.append(ExtensionBranch(vertex, true_child, false_child))
        return node_index

    root = search(0, 0)
    if root != len(nodes) - 1:
        raise AssertionError("certificate generator did not store the root last")
    return ExtensionCertificate(tuple(nodes))


def generate_extension_multiplicity_certificate(
    graph: Graph, multiplicity: int = 2
) -> ExtensionMultiplicityCertificate:
    """Prove that every apex attachment creates several monochromatic K5s.

    The witnesses at a leaf have distinct old four-vertex sets, so they name
    distinct five-sets after the common apex is added. A ``ValueError`` carries
    an attachment with fewer violations if the requested bound is false.
    """

    if multiplicity < 1:
        raise ValueError("multiplicity must be positive")

    clauses = _monochromatic_four_clauses(graph)
    order = graph.order
    nodes: list[ExtensionMultiplicityNode] = []

    def append_leaf(witnesses: list[tuple[bool, int]]) -> int:
        selected = tuple(
            ExtensionLeaf(
                color,
                tuple(vertex for vertex in range(order) if mask & (1 << vertex)),
            )
            for color, mask in witnesses[:multiplicity]
        )
        if any(len(witness.vertices) != 4 for witness in selected):
            raise AssertionError("a monochromatic-four mask must have four bits")
        node_index = len(nodes)
        nodes.append(ExtensionMultiplicityLeaf(selected))
        return node_index

    def search(true_mask: int, false_mask: int) -> int:
        assigned = true_mask | false_mask
        violated: list[tuple[bool, int]] = []
        unresolved: list[tuple[int, int]] = []

        for color, mask in clauses:
            if mask & (false_mask if color else true_mask):
                continue
            remaining = mask & ~assigned
            if remaining == 0:
                violated.append((color, mask))
                if len(violated) >= multiplicity:
                    return append_leaf(violated)
            else:
                unresolved.append((remaining.bit_count(), remaining))

        if not unresolved:
            attachment = tuple(
                bool(true_mask & (1 << vertex)) for vertex in range(order)
            )
            raise ExtensionMultiplicityCounterexample(attachment, len(violated))

        shortest = min(length for length, _ in unresolved)
        scores = [0] * order
        for length, remaining in unresolved:
            if length > shortest + 1:
                continue
            while remaining:
                bit = remaining & -remaining
                remaining -= bit
                scores[bit.bit_length() - 1] += 1

        vertex = max(range(order), key=scores.__getitem__)
        bit = 1 << vertex
        true_child = search(true_mask | bit, false_mask)
        false_child = search(true_mask, false_mask | bit)
        node_index = len(nodes)
        nodes.append(ExtensionBranch(vertex, true_child, false_child))
        return node_index

    root = search(0, 0)
    if root != len(nodes) - 1:
        raise AssertionError("certificate generator did not store the root last")
    return ExtensionMultiplicityCertificate(multiplicity, tuple(nodes))


def verify_extension_certificate(
    graph: Graph, certificate: ExtensionCertificate
) -> bool:
    """Check a decision-tree proof independently of the search procedure."""

    if not certificate.nodes:
        return False

    order = graph.order

    def verify(node_index: int, true_mask: int, false_mask: int) -> bool:
        if not 0 <= node_index < len(certificate.nodes):
            return False
        node = certificate.nodes[node_index]

        if isinstance(node, ExtensionLeaf):
            vertices = node.vertices
            if not (
                len(vertices) == 4
                and tuple(sorted(vertices)) == vertices
                and len(set(vertices)) == 4
                and all(0 <= vertex < order for vertex in vertices)
            ):
                return False
            if any(
                graph.has_edge(u, v) != node.color
                for u, v in combinations(vertices, 2)
            ):
                return False
            assigned_color = true_mask if node.color else false_mask
            return all(assigned_color & (1 << vertex) for vertex in vertices)

        if not (
            0 <= node.vertex < order
            and not ((true_mask | false_mask) & (1 << node.vertex))
            and 0 <= node.true_child < node_index
            and 0 <= node.false_child < node_index
        ):
            return False
        bit = 1 << node.vertex
        return verify(node.true_child, true_mask | bit, false_mask) and verify(
            node.false_child, true_mask, false_mask | bit
        )

    return verify(certificate.root, 0, 0)


def verify_extension_multiplicity_certificate(
    graph: Graph, certificate: ExtensionMultiplicityCertificate
) -> bool:
    """Independently check a lower bound on every attachment's violations."""

    if not certificate.nodes or certificate.multiplicity < 1:
        return False

    order = graph.order

    def valid_witness(
        witness: ExtensionLeaf, true_mask: int, false_mask: int
    ) -> bool:
        vertices = witness.vertices
        if not (
            len(vertices) == 4
            and tuple(sorted(vertices)) == vertices
            and len(set(vertices)) == 4
            and all(0 <= vertex < order for vertex in vertices)
        ):
            return False
        if any(
            graph.has_edge(u, v) != witness.color
            for u, v in combinations(vertices, 2)
        ):
            return False
        assigned_color = true_mask if witness.color else false_mask
        return all(assigned_color & (1 << vertex) for vertex in vertices)

    def verify(node_index: int, true_mask: int, false_mask: int) -> bool:
        if not 0 <= node_index < len(certificate.nodes):
            return False
        node = certificate.nodes[node_index]

        if isinstance(node, ExtensionMultiplicityLeaf):
            if len(node.witnesses) < certificate.multiplicity:
                return False
            selected = node.witnesses[: certificate.multiplicity]
            if len({witness.vertices for witness in selected}) != len(selected):
                return False
            return all(
                valid_witness(witness, true_mask, false_mask)
                for witness in selected
            )

        if not (
            0 <= node.vertex < order
            and not ((true_mask | false_mask) & (1 << node.vertex))
            and 0 <= node.true_child < node_index
            and 0 <= node.false_child < node_index
        ):
            return False
        bit = 1 << node.vertex
        return verify(node.true_child, true_mask | bit, false_mask) and verify(
            node.false_child, true_mask, false_mask | bit
        )

    return verify(certificate.root, 0, 0)


def attachment_violations(graph: Graph, true_mask: int) -> tuple[tuple[int, ...], ...]:
    """List monochromatic K5s containing the new apex for one attachment."""

    universe = (1 << graph.order) - 1
    if true_mask < 0 or true_mask & ~universe:
        raise ValueError("attachment mask exceeds graph order")
    false_mask = universe ^ true_mask
    violations: list[tuple[int, ...]] = []
    for color, mask in _monochromatic_four_clauses(graph):
        if mask & ~(true_mask if color else false_mask) == 0:
            violations.append(
                tuple(v for v in range(graph.order) if mask & (1 << v))
            )
    return tuple(violations)
