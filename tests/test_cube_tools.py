from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "solve_external_cubes", ROOT / "tools" / "solve_external_cubes.py"
)
assert SPEC is not None and SPEC.loader is not None
EXTERNAL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXTERNAL
SPEC.loader.exec_module(EXTERNAL)


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MERGE = load_tool("merge_cube_results")
ADOPT = load_tool("adopt_cartesian_refinement")
PROJECT = load_tool("project_cube_results")
COVER = load_tool("verify_cube_cover")
AUDIT = load_tool("verify_adaptive_cube_covers")
MATERIALIZED_PROVER = load_tool("prove_materialized_cubes")
MATERIALIZED_AUDIT = load_tool("audit_materialized_cube_proofs")
BINARY_COVER = load_tool("certify_binary_cube_cover")
MATERIALIZED_FRONTIER = load_tool("export_materialized_proof_frontier")
BINARY_REFINEMENT = load_tool("audit_binary_cube_refinement")


class ExternalCubeToolTests(unittest.TestCase):
    def test_render_cnf_appends_cube_as_units(self) -> None:
        rendered = EXTERNAL.render_cnf("c example", "1 -2 0", 3, 1, [2, -3])
        self.assertEqual(
            rendered,
            "c example\np cnf 3 3\n1 -2 0\n2 0\n-3 0\n",
        )

    def test_parse_complete_model(self) -> None:
        self.assertEqual(EXTERNAL.parse_model("s SATISFIABLE\nv 1 -2 3 0\n", 3), "101")

    def test_parse_rejects_incomplete_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "complete model"):
            EXTERNAL.parse_model("v 1 -2 0\n", 3)


class ResultMergeTests(unittest.TestCase):
    def test_second_pass_replaces_only_unknown_rows(self) -> None:
        primary = [MERGE.Row(20, 1.0, ""), MERGE.Row(0, 2.0, "")]
        secondary = [MERGE.Row(20, 3.0, "")]
        self.assertEqual([row.status for row in MERGE.merge_results(primary, secondary)], [20, 20])

    def test_projects_results_by_exact_cube(self) -> None:
        source_cubes = [[1, -2], [1, 2], [-1]]
        source_results = [
            MERGE.Row(20, 1.0, ""),
            MERGE.Row(0, 2.0, ""),
            MERGE.Row(20, 3.0, ""),
        ]
        projected = PROJECT.project_results(
            source_cubes, source_results, [[-1], [1, 2]]
        )
        self.assertEqual([row.seconds for row in projected], [3.0, 2.0])

    def test_projection_rejects_missing_cube(self) -> None:
        with self.assertRaisesRegex(ValueError, "absent"):
            PROJECT.project_results([[1]], [MERGE.Row(20, 1.0, "")], [[-1]])


class CartesianAdoptionTests(unittest.TestCase):
    def test_adopts_only_groups_at_threshold(self) -> None:
        state = {"round": 2, "closed": 5, "frontier": [[7], [-7]]}
        assignments = [[-1, -2], [-1, 2], [1, -2], [1, 2]]
        cubes = [[7] + assignment for assignment in assignments]
        cubes += [[-7] + assignment for assignment in assignments]
        statuses = [20, 20, 20, 0, 20, 20, 0, 0]
        updated, adopted, integrated = ADOPT.refine_state(
            state, cubes, statuses, [1, 2], 1
        )
        self.assertEqual(adopted, [0])
        self.assertEqual(integrated, 3)
        self.assertEqual(updated["round"], 3)
        self.assertEqual(updated["closed"], 8)
        self.assertEqual(updated["frontier"], [[7, 1, 2], [-7]])

    def test_rejects_incomplete_or_reordered_split(self) -> None:
        state = {"round": 0, "closed": 0, "frontier": [[]]}
        cubes = [[-1, -2], [1, -2], [-1, 2], [1, 2]]
        with self.assertRaisesRegex(ValueError, "complete Cartesian"):
            ADOPT.refine_state(state, cubes, [20, 20, 20, 20], [1, 2], 1)

    def test_selected_refinement_preserves_unselected_parents(self) -> None:
        state = {"round": 4, "closed": 10, "frontier": [[7], [-7], [8]]}
        assignments = [[-1], [1]]
        cubes = [[-7] + assignment for assignment in assignments]
        updated, adopted, integrated = ADOPT.refine_selected_state(
            state, cubes, [20, 0], [1], 1, [1]
        )
        self.assertEqual(adopted, [1])
        self.assertEqual(integrated, 1)
        self.assertEqual(updated["frontier"], [[7], [-7, 1], [8]])


class CubeCoverTests(unittest.TestCase):
    def test_reduces_adaptive_binary_tree(self) -> None:
        cubes = [
            frozenset((1, 2)),
            frozenset((1, -2)),
            frozenset((-1, 3)),
            frozenset((-1, -3)),
        ]
        covered, steps, residual = COVER.reduce_cover(cubes)
        self.assertTrue(covered)
        self.assertEqual(len(steps), 3)
        self.assertIn(frozenset(), residual)
        self.assertTrue(COVER.cover_by_dpll(cubes)[0])

    def test_rejects_incomplete_cover(self) -> None:
        cubes = [frozenset((1, 2)), frozenset((1, -2)), frozenset((-1, 3))]
        covered, _, residual = COVER.reduce_cover(cubes)
        self.assertFalse(covered)
        self.assertNotIn(frozenset(), residual)
        dpll_covered, _, witness = COVER.cover_by_dpll(cubes)
        self.assertFalse(dpll_covered)
        self.assertIsNotNone(witness)

    def test_absorption_is_sound(self) -> None:
        cubes = [frozenset((1,)), frozenset((1, 2)), frozenset((-1,))]
        covered, steps, _ = COVER.reduce_cover(cubes)
        self.assertTrue(covered)
        self.assertIn("merge", [step["kind"] for step in steps])

    def test_fast_sibling_certificate_replays(self) -> None:
        cubes = [
            frozenset((1, 2)),
            frozenset((1, -2)),
            frozenset((-1, 3)),
            frozenset((-1, -3)),
        ]
        steps, residual = BINARY_COVER.merge_certificate(cubes)
        self.assertIn(frozenset(), residual)
        self.assertEqual(BINARY_COVER.replay(cubes, steps), residual)

    def test_fast_sibling_certificate_rejects_incomplete_cover(self) -> None:
        cubes = [frozenset((1, 2)), frozenset((1, -2)), frozenset((-1, 3))]
        _, residual = BINARY_COVER.merge_certificate(cubes)
        self.assertNotIn(frozenset(), residual)


class AdaptiveCoverAuditTests(unittest.TestCase):
    def test_classifies_header_only_cuber_unsat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "r001-0123456789abcdefabcd.cubes"
            cubes.write_text("", encoding="ascii")
            cubes.with_suffix(".log").write_text(
                "status\t20\nvariables\t10162\ncubes\t0\n", encoding="ascii"
            )
            cubes.with_suffix(".tsv").write_text(
                "cube\tstatus\tseconds\tmodel\n", encoding="ascii"
            )
            entry = AUDIT.verify(cubes, root)
        self.assertEqual(entry["kind"], "trusted-cuber-unsat")
        self.assertEqual(entry["cube_count"], 0)

    def test_rejects_unexplained_empty_cube_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cubes = root / "r001-0123456789abcdefabcd.cubes"
            cubes.write_text("", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "companion"):
                AUDIT.verify(cubes, root)


class MaterializedProofToolTests(unittest.TestCase):
    def test_cube_hash_binds_order_and_sign(self) -> None:
        digest = MATERIALIZED_PROVER.cube_sha256([1, -2])
        self.assertEqual(digest, MATERIALIZED_PROVER.cube_sha256([1, -2]))
        self.assertNotEqual(digest, MATERIALIZED_PROVER.cube_sha256([-2, 1]))
        self.assertNotEqual(digest, MATERIALIZED_PROVER.cube_sha256([1, 2]))

    def test_artifact_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "artifact"):
            MATERIALIZED_AUDIT.artifact(Path("/tmp/proofs"), "../proof.drat")

    def test_exports_only_hash_bound_unknown_results(self) -> None:
        cubes = [[1], [-1, 2], [-1, -2]]
        results = []
        for index, (cube, status) in enumerate(zip(cubes, (20, 0, 20))):
            results.append(
                {
                    "index": index,
                    "cube": cube,
                    "cube_sha256": MATERIALIZED_PROVER.cube_sha256(cube),
                    "status": status,
                }
            )
        indices, unknown = MATERIALIZED_FRONTIER.export_unknown(
            {"results": results}, cubes
        )
        self.assertEqual(indices, [1])
        self.assertEqual(unknown, [[-1, 2]])

    def test_audits_ordered_complementary_refinement(self) -> None:
        parents = ((1,), (-1, 2))
        children = ((1, 3), (1, -3), (-1, 2, -4), (-1, 2, 4))
        BINARY_REFINEMENT.audit(parents, children, (3, -4))

    def test_rejects_reordered_refinement_children(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive child"):
            BINARY_REFINEMENT.audit(((1,),), ((1, -2), (1, 2)), (2,))


if __name__ == "__main__":
    unittest.main()
