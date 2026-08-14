from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from ramsey55 import (
    ExtensionCertificate,
    ExtensionLeaf,
    ExtensionMultiplicityCertificate,
    ExtensionMultiplicityLeaf,
    Graph,
    attachment_violations,
    generate_extension_certificate,
    generate_extension_multiplicity_certificate,
    verify_extension_certificate,
    verify_extension_multiplicity_certificate,
)


class ExtensionCertificateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path("data/reference/r55_42some.g6")
        first = next(
            line.strip()
            for line in path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        )
        cls.graph = Graph.from_graph6(first)
        cls.certificate = generate_extension_certificate(cls.graph)
        cls.multiplicity_certificate = generate_extension_multiplicity_certificate(
            cls.graph, 2
        )

    def test_reference_graph_has_checked_cover(self) -> None:
        certificate = self.certificate
        self.assertEqual(certificate.branch_count + 1, certificate.leaf_count)
        self.assertLess(certificate.branch_count, 250)
        self.assertTrue(verify_extension_certificate(self.graph, certificate))

    def test_certificate_complements_with_graph(self) -> None:
        self.assertTrue(
            verify_extension_certificate(
                self.graph.complement(), self.certificate.complement()
            )
        )

    def test_corrupted_leaf_is_rejected(self) -> None:
        nodes = list(self.certificate.nodes)
        leaf_index = next(
            index for index, node in enumerate(nodes) if isinstance(node, ExtensionLeaf)
        )
        leaf = nodes[leaf_index]
        assert isinstance(leaf, ExtensionLeaf)
        nodes[leaf_index] = replace(leaf, color=not leaf.color)
        self.assertFalse(
            verify_extension_certificate(self.graph, ExtensionCertificate(tuple(nodes)))
        )

    def test_attachment_violation_on_small_graph(self) -> None:
        complete_four = Graph.from_edges(4, ((u, v) for v in range(4) for u in range(v)))
        self.assertEqual(attachment_violations(complete_four, 0b1111), ((0, 1, 2, 3),))
        self.assertEqual(attachment_violations(complete_four, 0b0111), ())

    def test_reference_graph_has_two_violation_cover(self) -> None:
        certificate = self.multiplicity_certificate
        self.assertEqual(certificate.multiplicity, 2)
        self.assertEqual(certificate.branch_count + 1, certificate.leaf_count)
        self.assertTrue(
            verify_extension_multiplicity_certificate(self.graph, certificate)
        )
        self.assertTrue(
            verify_extension_multiplicity_certificate(
                self.graph.complement(), certificate.complement()
            )
        )

    def test_duplicate_multiplicity_witness_is_rejected(self) -> None:
        certificate = self.multiplicity_certificate
        nodes = list(certificate.nodes)
        leaf_index = next(
            index
            for index, node in enumerate(nodes)
            if isinstance(node, ExtensionMultiplicityLeaf)
        )
        leaf = nodes[leaf_index]
        assert isinstance(leaf, ExtensionMultiplicityLeaf)
        nodes[leaf_index] = ExtensionMultiplicityLeaf(
            (leaf.witnesses[0], leaf.witnesses[0])
        )
        corrupted = ExtensionMultiplicityCertificate(2, tuple(nodes))
        self.assertFalse(
            verify_extension_multiplicity_certificate(self.graph, corrupted)
        )

    def test_near_miss_deletion_matches_representative_255(self) -> None:
        graph6_path = Path("data/reference/r55_42some.g6")
        records = [
            line.strip()
            for line in graph6_path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        representative = Graph.from_graph6(records[255])
        matrix_path = Path("data/reference/k43_near_miss_1.matrix")
        rows = [
            line.strip()
            for line in matrix_path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        near_miss = Graph.from_adjacency_matrix(rows)

        # Vertex i of the graph obtained by deleting near-miss vertex 0 maps
        # to permutation[i] in public representative 255. Two rounds of
        # joint colour refinement make this correspondence discrete; keeping
        # the explicit permutation makes the test independent of nauty.
        permutation = (
            31, 23, 9, 19, 8, 22, 0, 21, 18, 39, 12, 24, 14, 11,
            16, 5, 6, 37, 2, 33, 7, 13, 1, 15, 17, 36, 38, 26,
            34, 40, 20, 29, 25, 30, 35, 4, 32, 10, 27, 28, 41, 3,
        )
        self.assertEqual(sorted(permutation), list(range(42)))
        self.assertTrue(
            all(
                representative.has_edge(permutation[u], permutation[v])
                == near_miss.has_edge(u + 1, v + 1)
                for u in range(42)
                for v in range(42)
            )
        )

        attachment = sum(
            1 << permutation[vertex]
            for vertex in range(42)
            if near_miss.has_edge(0, vertex + 1)
        )
        self.assertEqual(
            attachment_violations(representative, attachment),
            ((10, 12, 26, 34), (10, 23, 26, 34)),
        )

    def test_low_multiplicity_attachments(self) -> None:
        graph6_path = Path("data/reference/r55_42some.g6")
        records = [
            line.strip()
            for line in graph6_path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        expected = {
            41: (131467062783, 2),
            255: (6410183167, 2),
            256: (21409014271, 4),
        }
        for index, (attachment, count) in expected.items():
            with self.subTest(index=index):
                graph = Graph.from_graph6(records[index])
                self.assertEqual(
                    len(attachment_violations(graph, attachment)), count
                )

    def test_representative_256_is_one_flip_from_255(self) -> None:
        graph6_path = Path("data/reference/r55_42some.g6")
        records = [
            line.strip()
            for line in graph6_path.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        source = Graph.from_graph6(records[255])
        target = Graph.from_graph6(records[256])
        self.assertTrue(source.has_edge(34, 38))
        flipped = Graph.from_edges(
            42,
            (
                (u, v)
                for v in range(1, 42)
                for u in range(v)
                if source.has_edge(u, v) and (u, v) != (34, 38)
            ),
        )
        permutation = (
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
            16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30,
            31, 32, 34, 35, 23, 36, 37, 38, 33, 39, 40, 41,
        )
        self.assertEqual(sorted(permutation), list(range(42)))
        self.assertTrue(
            all(
                target.has_edge(permutation[u], permutation[v])
                == flipped.has_edge(u, v)
                for u in range(42)
                for v in range(42)
            )
        )
        source_attachment = 6410183167
        target_attachment = sum(
            1 << permutation[vertex]
            for vertex in range(42)
            if source_attachment & (1 << vertex)
        )
        self.assertEqual(target_attachment, 21409014271)
        self.assertEqual(
            len(attachment_violations(source, source_attachment)), 2
        )
        self.assertEqual(
            len(attachment_violations(flipped, source_attachment)), 4
        )


if __name__ == "__main__":
    unittest.main()
