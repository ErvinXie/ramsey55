from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
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
MATERIALIZED_COMPOSE = load_tool("compose_materialized_cube_proofs")
MATERIALIZED_PORTFOLIO = load_tool("compose_materialized_cube_portfolio")
MATERIALIZED_CHAIN = load_tool("run_materialized_proof_chain")
MATERIALIZED_CHAIN_AUDIT = load_tool("audit_materialized_proof_chain")
FIXED_PAIR_BUNDLE = load_tool("audit_fixed_pair_proof_bundle")
ORDER45_FIXED_PROOFS = load_tool("audit_order45_fixed_pair_proofs")
MATERIALIZE_CNF_CUBE = load_tool("materialize_cnf_cube")
STRATA_LEAF_PROOFS = load_tool("audit_order45_strata_leaf_proofs")
STRATA_PROOF_BUNDLE = load_tool("audit_order45_strata_proof_bundle")
CARTESIAN_CUBES = load_tool("generate_cartesian_cubes")
SCREEN_VARIABLES = load_tool("screen_cube_variables")


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

    def test_screen_variables_emits_parent_variable_polarity_order(self) -> None:
        self.assertEqual(
            SCREEN_VARIABLES.extend_cubes([[1], [-1, 2]], [3, 4]),
            [
                [1, -3],
                [1, 3],
                [1, -4],
                [1, 4],
                [-1, 2, -3],
                [-1, 2, 3],
                [-1, 2, -4],
                [-1, 2, 4],
            ],
        )

    def test_screen_variables_rejects_an_assigned_variable(self) -> None:
        with self.assertRaisesRegex(ValueError, "already assigns"):
            SCREEN_VARIABLES.extend_cubes([[1, -2]], [2, 3])


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

    def test_materialized_retry_replaces_only_ordered_unknown_rows(self) -> None:
        primary = [
            {"cube": [1], "status": 20},
            {"cube": [-1, 2], "status": 0},
            {"cube": [-1, -2], "status": 0},
        ]
        secondary = [
            {"cube": [-1, 2], "status": 20},
            {"cube": [-1, -2], "status": 0},
        ]
        self.assertEqual(
            MATERIALIZED_COMPOSE.ordered_unknown_replacements(primary, secondary),
            [1, 2],
        )
        with self.assertRaisesRegex(ValueError, "ordered UNKNOWN"):
            MATERIALIZED_COMPOSE.ordered_unknown_replacements(
                primary, [{"cube": [1], "status": 20}]
            )

    def test_long_retry_selects_only_double_unknown_siblings(self) -> None:
        cubes = [[1], [-1], [2], [-2], [3], [-3]]
        results = [
            {"status": 20},
            {"status": 0},
            {"status": 0},
            {"status": 0},
            {"status": 20},
            {"status": 20},
        ]
        self.assertEqual(
            MATERIALIZED_CHAIN.double_unknown_cubes(cubes, results), [[2], [-2]]
        )

    def test_materialized_retry_cube_file_uses_assumption_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "retry.icnf"
            MATERIALIZED_CHAIN.write_icnf(path, [[1, -2], [-1, 3]])
            self.assertEqual(path.read_text(), "a 1 -2 0\na -1 3 0\n")

    def test_materialized_chain_detects_frontier_growth(self) -> None:
        self.assertFalse(MATERIALIZED_CHAIN.frontier_grew(4, {"unknown": 4}))
        self.assertFalse(MATERIALIZED_CHAIN.frontier_grew(4, {"unknown": 3}))
        self.assertTrue(MATERIALIZED_CHAIN.frontier_grew(4, {"unknown": 5}))
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            MATERIALIZED_CHAIN.frontier_grew(-1, {"unknown": 0})

    def test_materialized_composition_binds_cross_solver_override(self) -> None:
        kissat = {"path": "kissat", "sha256": "1" * 64, "arguments": []}
        cadical = {"path": "cadical", "sha256": "2" * 64, "arguments": []}
        result: dict[str, object] = {"status": 20}
        MATERIALIZED_COMPOSE.bind_effective_solver(result, cadical, kissat)
        self.assertEqual(result["solver"], cadical)
        MATERIALIZED_COMPOSE.bind_effective_solver(result, cadical, cadical)
        self.assertNotIn("solver", result)

    def test_materialized_portfolio_selects_smallest_verified_proof(self) -> None:
        documents = [
            {
                "results": [
                    {"status": 0},
                    {"status": 20, "proof_bytes": 50},
                    {"status": 20, "proof_bytes": 30},
                ]
            },
            {
                "results": [
                    {"status": 20, "proof_bytes": 40},
                    {"status": 20, "proof_bytes": 20},
                    {"status": 0},
                ]
            },
        ]
        self.assertEqual(MATERIALIZED_PORTFOLIO.selected_sources(documents), [1, 1, 0])
        documents[1]["results"][2] = {"status": 10}
        with self.assertRaisesRegex(ValueError, "SAT result"):
            MATERIALIZED_PORTFOLIO.selected_sources(documents)


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

    def test_checked_proof_publication_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "scratch.drat"
            destination = root / "retained.drat"
            source.write_bytes(b"proof")
            MATERIALIZED_PROVER.publish_proof(source, destination)
            self.assertEqual(destination.read_bytes(), b"proof")
            self.assertFalse(source.exists())
            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                MATERIALIZED_PROVER.publish_proof(destination, destination)

    def test_completed_results_does_not_wait_in_input_order(self) -> None:
        gate = threading.Event()

        def worker(index: int) -> int:
            if index == 0:
                if not gate.wait(timeout=5):
                    raise RuntimeError("test worker timed out")
            return index

        with MATERIALIZED_PROVER.concurrent.futures.ThreadPoolExecutor(
            2
        ) as executor:
            results = MATERIALIZED_PROVER.completed_results(
                executor, worker, range(2)
            )
            try:
                first = next(results)
            finally:
                gate.set()
            self.assertEqual(first, 1)
            self.assertEqual(next(results), 0)
            with self.assertRaises(StopIteration):
                next(results)

    def test_completed_results_checkpoints_success_before_failure(self) -> None:
        def worker(index: int) -> int:
            if index == 0:
                raise RuntimeError("expected worker failure")
            return index

        with MATERIALIZED_PROVER.concurrent.futures.ThreadPoolExecutor(
            2
        ) as executor:
            results = MATERIALIZED_PROVER.completed_results(
                executor, worker, range(2)
            )
            self.assertEqual(next(results), 1)
            with self.assertRaisesRegex(RuntimeError, "expected worker failure"):
                next(results)

    def test_complete_chain_seed_is_audited_before_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            formula = root / "formula.cnf"
            seed = root / "seed.json"
            refiner = root / "refiner"
            solver = root / "solver"
            checker = root / "checker"
            workdir = root / "chain"
            formula.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            seed.write_text(
                json.dumps(
                    {"summary": {"sat": 0, "complete_unsat": True}}
                ),
                encoding="utf-8",
            )
            for binary in (refiner, solver, checker):
                binary.write_text("placeholder\n", encoding="ascii")

            calls: list[tuple[list[str], Path]] = []
            original_argv = sys.argv
            original_run_logged = MATERIALIZED_CHAIN.run_logged

            def fake_run_logged(command: list[str], log: Path) -> int:
                calls.append((command, log))
                return 0

            MATERIALIZED_CHAIN.run_logged = fake_run_logged
            sys.argv = [
                "run_materialized_proof_chain.py",
                str(formula),
                str(seed),
                str(workdir),
                "--refiner",
                str(refiner),
                "--solver",
                str(solver),
                "--checker",
                str(checker),
            ]
            try:
                self.assertEqual(MATERIALIZED_CHAIN.main(), 20)
            finally:
                MATERIALIZED_CHAIN.run_logged = original_run_logged
                sys.argv = original_argv

            self.assertEqual(len(calls), 1)
            self.assertIn("audit_materialized_cube_proofs.py", calls[0][0][1])
            self.assertEqual(calls[0][1].name, "r0000-seed-audit.log")
            state = json.loads((workdir / "state.json").read_text())
            self.assertTrue(state["complete"])

    def test_artifact_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "artifact"):
            MATERIALIZED_AUDIT.artifact(Path("/tmp/proofs"), "../proof.drat")

    def test_tool_bindings_reject_a_different_checker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            solver = root / "solver"
            checker = root / "checker"
            wrong = root / "wrong"
            solver.write_bytes(b"solver")
            checker.write_bytes(b"checker")
            wrong.write_bytes(b"wrong")
            document = {
                "solver": {
                    "path": str(solver),
                    "sha256": MATERIALIZED_PROVER.file_sha256(solver),
                },
                "checker": {
                    "path": str(checker),
                    "sha256": MATERIALIZED_PROVER.file_sha256(checker),
                },
            }
            MATERIALIZED_AUDIT.validate_tool_bindings(document, checker)
            with self.assertRaisesRegex(ValueError, "supplied checker"):
                MATERIALIZED_AUDIT.validate_tool_bindings(document, wrong)

    def test_leaf_auditor_validates_cross_solver_override(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            solver = Path(raw) / "cadical"
            solver.write_bytes(b"solver")
            entry = {
                "path": str(solver),
                "sha256": MATERIALIZED_PROVER.file_sha256(solver),
            }
            MATERIALIZED_AUDIT.validate_binary_binding(entry, "cube 0 solver")
            entry["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "cube 0 solver binary"):
                MATERIALIZED_AUDIT.validate_binary_binding(entry, "cube 0 solver")

    def test_compaction_metadata_binds_its_log(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            log = root / "cube.compact.log"
            log.write_text("s VERIFIED\n")
            result = {
                "compaction": {
                    "method": "drat-trim -C -l",
                    "retained": True,
                    "source_proof_bytes": 123,
                    "source_proof_sha256": "a" * 64,
                    "log": log.name,
                    "log_sha256": MATERIALIZED_PROVER.file_sha256(log),
                }
            }
            MATERIALIZED_AUDIT.validate_compaction(root, result, 0)
            log.write_text("tampered\n")
            with self.assertRaisesRegex(ValueError, "log hash"):
                MATERIALIZED_AUDIT.validate_compaction(root, result, 0)

    def test_chain_refinement_manifest_is_rebuilt_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            parents = root / "parents.icnf"
            children = root / "children.icnf"
            results = root / "refine.tsv"
            manifest = root / "refinement.json"
            parents.write_text("a 1 0\n")
            children.write_text("a 1 2 0\na 1 -2 0\n")
            results.write_text(
                "cube\tstatus\tsplit\tseconds\tmodel\n0\t0\t2\t0.1\t\n"
            )
            expected = {
                "schema": BINARY_REFINEMENT.SCHEMA,
                "parents": {
                    "path": str(parents),
                    "sha256": BINARY_REFINEMENT.file_sha256(parents),
                    "count": 1,
                },
                "children": {
                    "path": str(children),
                    "sha256": BINARY_REFINEMENT.file_sha256(children),
                    "count": 2,
                },
                "results": {
                    "path": str(results),
                    "sha256": BINARY_REFINEMENT.file_sha256(results),
                },
                "splits": [2],
                "complete_binary_refinement": True,
            }
            manifest.write_text(json.dumps(expected))
            self.assertEqual(
                MATERIALIZED_CHAIN_AUDIT.verify_refinement(
                    parents, children, results, manifest
                ),
                1,
            )
            expected["splits"] = [-2]
            manifest.write_text(json.dumps(expected))
            with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                MATERIALIZED_CHAIN_AUDIT.verify_refinement(
                    parents, children, results, manifest
                )

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

    def test_fixed_pair_bundle_matches_cube_content_not_path_spelling(self) -> None:
        expected = {"path": "forest/closed.icnf", "sha256": "a" * 64, "count": 7}
        actual = {"path": "proofs/cubes.icnf", "sha256": "a" * 64, "count": 7}
        FIXED_PAIR_BUNDLE.validate_cube_binding(actual, expected, "closed")
        actual["count"] = 6
        with self.assertRaisesRegex(ValueError, "closed cube binding mismatch"):
            FIXED_PAIR_BUNDLE.validate_cube_binding(actual, expected, "closed")

    def test_fixed_pair_bundle_replays_initial_binary_cover(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cubes = root / "roots.icnf"
            cubes.write_text("a -1 0\na 1 0\n", encoding="ascii")
            forest = root / "forest.json"
            forest.write_text(
                json.dumps(
                    {
                        "schema": FIXED_PAIR_BUNDLE.FOREST_SCHEMA,
                        "source_cubes": {
                            "path": str(cubes),
                            "sha256": MATERIALIZED_PROVER.file_sha256(cubes),
                            "count": 2,
                        },
                    }
                )
            )
            source = BINARY_COVER.read_cubes(cubes)
            steps, residual = BINARY_COVER.merge_certificate(source)
            certificate = root / "cover.json"
            certificate.write_text(
                json.dumps(
                    {
                        "schema": BINARY_COVER.SCHEMA,
                        "input": str(cubes),
                        "input_sha256": MATERIALIZED_PROVER.file_sha256(cubes),
                        "cube_count": 2,
                        "steps": steps,
                        "step_count": len(steps),
                        "residual": [BINARY_COVER.ordered(cube) for cube in residual],
                        "covered": True,
                    }
                )
            )
            audited = FIXED_PAIR_BUNDLE.audit_initial_cover(forest, certificate)
            self.assertTrue(audited["covered"])
            self.assertEqual(audited["steps"], 1)
            tampered = json.loads(certificate.read_text())
            tampered["input_sha256"] = "0" * 64
            certificate.write_text(json.dumps(tampered))
            with self.assertRaisesRegex(ValueError, "not bound"):
                FIXED_PAIR_BUNDLE.audit_initial_cover(forest, certificate)

    def test_fixed_pair_bundle_binds_chain_segment_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            seed = root / "seed.json"
            seed.write_text("next segment\n")
            previous = {
                "final_manifest_sha256": MATERIALIZED_PROVER.file_sha256(seed)
            }
            self.assertEqual(
                FIXED_PAIR_BUNDLE.validate_chain_adjacency(previous, seed, "closed"),
                "identical terminal manifest",
            )

            formula = {"path": "formula.cnf", "sha256": "f" * 64}
            cubes = {"path": "cubes.icnf", "sha256": "c" * 64, "count": 2}
            old = root / "old.json"
            old.write_text(
                json.dumps(
                    {
                        "schema": MATERIALIZED_PROVER.SCHEMA,
                        "formula": formula,
                        "cubes": cubes,
                        "attempt": 1,
                    }
                )
            )
            retry = root / "retry.json"
            retry.write_text(
                json.dumps(
                    {
                        "schema": MATERIALIZED_PROVER.SCHEMA,
                        "formula": formula,
                        "cubes": cubes,
                        "attempt": 2,
                    }
                )
            )
            replacement = {
                "final_manifest": str(old),
                "final_manifest_sha256": MATERIALIZED_PROVER.file_sha256(old),
            }
            self.assertEqual(
                FIXED_PAIR_BUNDLE.validate_chain_adjacency(
                    replacement, retry, "closed"
                ),
                "independently replayed exact-cube retry",
            )
            changed = json.loads(retry.read_text())
            changed["cubes"]["sha256"] = "0" * 64
            retry.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "segment boundary mismatch"):
                FIXED_PAIR_BUNDLE.validate_chain_adjacency(
                    replacement, retry, "closed"
                )

    def test_strata_bundle_binds_formula_manifest_and_forest_roots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            formula = root / "d20.cnf"
            formula.write_text("p cnf 4 1\n1 -2 0\n", encoding="ascii")
            cubes = [
                {"edges_h": 1, "edges_j": 2, "literals": [1, -2]},
                {"edges_h": 2, "edges_j": 1, "literals": [-1, 2]},
            ]
            formula_manifest = root / "formula-manifest.json"
            formula_manifest.write_text(
                json.dumps(
                    {
                        "schema": STRATA_LEAF_PROOFS.FORMULA_SCHEMA,
                        "order": 45,
                        "files": [
                            {
                                "degree": 20,
                                "path": formula.name,
                                "variables": 4,
                                "clauses": 1,
                                "sha256": MATERIALIZED_PROVER.file_sha256(formula),
                                "cubes": cubes,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source = root / "roots.icnf"

            def write_source(rows: list[list[int]]) -> None:
                source.write_text(
                    "\n".join(
                        [
                            "c manifest_sha256 "
                            + MATERIALIZED_PROVER.file_sha256(formula_manifest),
                            "c cnf_sha256 "
                            + MATERIALIZED_PROVER.file_sha256(formula),
                            "c degree 20",
                            *(
                                f"{index} {' '.join(map(str, cube))} 0"
                                for index, cube in enumerate(rows)
                            ),
                        ]
                    )
                    + "\n",
                    encoding="ascii",
                )

            write_source([[1, -2], [-1, 2]])
            forest_manifest = root / "forest.json"

            def write_forest() -> None:
                forest_manifest.write_text(
                    json.dumps(
                        {
                            "schema": STRATA_PROOF_BUNDLE.FOREST_SCHEMA,
                            "source_cubes": {
                                "path": str(source),
                                "sha256": MATERIALIZED_PROVER.file_sha256(source),
                                "count": 2,
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            write_forest()
            _, _, binding = STRATA_PROOF_BUNDLE.formula_and_forest_bindings(
                formula_manifest, formula, 20, forest_manifest
            )
            self.assertEqual(binding["source_cube_count"], 2)

            write_source([[-1, 2], [1, -2]])
            write_forest()
            with self.assertRaisesRegex(ValueError, "roots differ"):
                STRATA_PROOF_BUNDLE.formula_and_forest_bindings(
                    formula_manifest, formula, 20, forest_manifest
                )

    def test_strata_bundle_rejects_unbound_root_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            formula = root / "d20.cnf"
            formula.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            formula_manifest = root / "formula-manifest.json"
            formula_manifest.write_text(
                json.dumps(
                    {
                        "schema": STRATA_LEAF_PROOFS.FORMULA_SCHEMA,
                        "files": [
                            {
                                "degree": 20,
                                "variables": 1,
                                "clauses": 1,
                                "sha256": MATERIALIZED_PROVER.file_sha256(formula),
                                "cubes": [{"literals": [1]}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source = root / "roots.icnf"
            source.write_text(
                "c manifest_sha256 "
                + MATERIALIZED_PROVER.file_sha256(formula_manifest)
                + "\nc cnf_sha256 "
                + MATERIALIZED_PROVER.file_sha256(formula)
                + "\nc degree 21\n0 1 0\n",
                encoding="ascii",
            )
            forest_manifest = root / "forest.json"
            forest_manifest.write_text(
                json.dumps(
                    {
                        "schema": STRATA_PROOF_BUNDLE.FOREST_SCHEMA,
                        "source_cubes": {
                            "path": str(source),
                            "sha256": MATERIALIZED_PROVER.file_sha256(source),
                            "count": 1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "metadata mismatch"):
                STRATA_PROOF_BUNDLE.formula_and_forest_bindings(
                    formula_manifest, formula, 20, forest_manifest
                )


if __name__ == "__main__":
    unittest.main()
