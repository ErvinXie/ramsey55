#!/usr/bin/env python3
"""Audit a hierarchical, independently checkable fixed-pair UNSAT bundle.

The bundle joins four existing certificate layers:

* a binary certificate showing that the initial cubes cover every assignment;
* a proof-forest snapshot showing that its terminal leaves cover every root;
* materialized DRAT proofs plus a binary-refinement chain for closed leaves; and
* initial open-leaf proofs, one explicit refinement, and a second proof chain.

No solver result is trusted here.  Every retained DRAT proof is replayed by the
supplied checker and every cover/refinement relation is reconstructed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools.audit_materialized_proof_chain import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        audit_proof_manifest,
        verify_frontier,
        verify_refinement,
    )
    from tools.certify_binary_cube_cover import (
        SCHEMA as COVER_SCHEMA,
        replay as replay_cover,
    )
    from tools.prove_materialized_cubes import (
        SCHEMA as PROOF_SCHEMA,
        file_sha256,
    )
    from tools.solve_external_cubes import read_cnf
    from tools.verify_cube_cover import read_cubes as read_cover_cubes
else:
    from audit_materialized_proof_chain import (
        AUDIT_SCHEMA as CHAIN_AUDIT_SCHEMA,
        audit_proof_manifest,
        verify_frontier,
        verify_refinement,
    )
    from certify_binary_cube_cover import (
        SCHEMA as COVER_SCHEMA,
        replay as replay_cover,
    )
    from prove_materialized_cubes import SCHEMA as PROOF_SCHEMA, file_sha256
    from solve_external_cubes import read_cnf
    from verify_cube_cover import read_cubes as read_cover_cubes


BUNDLE_SCHEMA = "ramsey55.fixed-pair-proof-bundle.v1"
AUDIT_SCHEMA = "ramsey55.fixed-pair-proof-bundle-audit.v1"
FOREST_SCHEMA = "ramsey55.proof-forest-snapshot.v1"


def load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"expected JSON object: {path}")
    return document


def required_path(document: dict[str, Any], key: str) -> Path:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"bundle field {key!r} must be a nonempty path")
    path = Path(value)
    if not path.is_file() and not path.is_dir():
        raise ValueError(f"bundle path does not exist: {path}")
    return path


def cube_binding(path: Path, count: int) -> dict[str, Any]:
    return {"path": str(path), "sha256": file_sha256(path), "count": count}


def validate_cube_binding(
    actual: dict[str, Any], expected: dict[str, Any], label: str
) -> None:
    """Require identical cube bytes and cardinality, independent of path spelling."""

    if (
        actual.get("sha256") != expected.get("sha256")
        or int(actual.get("count", -1)) != int(expected.get("count", -2))
    ):
        raise ValueError(f"{label} cube binding mismatch")


def validate_proof_binding(
    document: dict[str, Any],
    formula: dict[str, Any],
    cubes: dict[str, Any],
    label: str,
) -> None:
    if document.get("schema") != PROOF_SCHEMA:
        raise ValueError(f"unexpected {label} proof schema")
    if document.get("formula") != formula:
        raise ValueError(f"{label} formula binding mismatch")
    validate_cube_binding(document["cubes"], cubes, label)


def parse_json_output(completed: subprocess.CompletedProcess[str], label: str) -> dict:
    if completed.returncode:
        raise RuntimeError(f"{label} failed:\n{completed.stdout[-4000:]}")
    candidates = [
        line for line in completed.stdout.splitlines() if line.startswith("{")
    ]
    if not candidates:
        raise RuntimeError(f"{label} emitted no JSON summary")
    result = json.loads(candidates[-1])
    if not isinstance(result, dict):
        raise RuntimeError(f"{label} emitted a non-object JSON summary")
    return result


def run_json_tool(arguments: list[str], label: str) -> dict[str, Any]:
    return parse_json_output(
        subprocess.run(
            [sys.executable, *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        ),
        label,
    )


def audit_initial_cover(
    forest_manifest: Path, cover_certificate: Path
) -> dict[str, Any]:
    forest = load_json(forest_manifest)
    if forest.get("schema") != FOREST_SCHEMA:
        raise ValueError("unexpected proof-forest schema")
    source = forest["source_cubes"]
    source_path = Path(source["path"])
    if file_sha256(source_path) != source["sha256"]:
        raise ValueError("proof-forest source cube hash mismatch")
    cubes = read_cover_cubes(source_path)
    if len(cubes) != int(source["count"]):
        raise ValueError("proof-forest source cube count mismatch")

    certificate = load_json(cover_certificate)
    if certificate.get("schema") != COVER_SCHEMA:
        raise ValueError("unexpected initial-cover certificate schema")
    if (
        certificate.get("input_sha256") != source["sha256"]
        or int(certificate.get("cube_count", -1)) != len(cubes)
    ):
        raise ValueError("initial cover is not bound to the forest roots")
    steps = certificate.get("steps")
    if not isinstance(steps, list) or len(steps) != int(
        certificate.get("step_count", -1)
    ):
        raise ValueError("initial-cover step count mismatch")
    residual = replay_cover(cubes, steps)
    recorded = {
        frozenset(map(int, cube)) for cube in certificate.get("residual", [])
    }
    if residual != recorded:
        raise ValueError("initial-cover residual family mismatch")
    if certificate.get("covered") is not True or frozenset() not in residual:
        raise ValueError("initial cubes do not cover the empty cube")
    return {
        "certificate": str(cover_certificate),
        "certificate_sha256": file_sha256(cover_certificate),
        "cubes": len(cubes),
        "steps": len(steps),
        "residual": len(residual),
        "covered": True,
    }


def audit_chain(
    seed_manifest: Path,
    workdir: Path,
    first_round: int,
    checker: Path,
    jobs: int,
    tool: Path,
    state: Path | None = None,
) -> dict[str, Any]:
    command = [
        str(tool),
        str(seed_manifest),
        str(workdir),
        "--first-round",
        str(first_round),
        "--checker",
        str(checker),
        "--jobs",
        str(jobs),
    ]
    if state is not None:
        command.extend(("--state", str(state)))
    result = run_json_tool(
        command,
        f"materialized proof-chain audit for {workdir}",
    )
    if result.get("schema") != CHAIN_AUDIT_SCHEMA:
        raise ValueError(f"unexpected proof-chain audit schema for {workdir}")
    return result


def chain_specs(section: dict[str, Any], label: str) -> list[dict[str, Any]]:
    raw = section.get("segments")
    if raw is None:
        raw = [section]
    if not isinstance(raw, list) or not raw or any(
        not isinstance(item, dict) for item in raw
    ):
        raise ValueError(f"bundle {label} segments must be a nonempty object list")
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        seed = required_path(item, "seed_manifest")
        workdir = required_path(item, "chain_workdir")
        first_round = int(item["first_round"])
        if first_round < 0:
            raise ValueError(f"{label} segment {index} has a negative first round")
        state_value = item.get("state")
        state = None
        if state_value is not None:
            if not isinstance(state_value, str) or not state_value:
                raise ValueError(f"{label} segment {index} has an invalid state path")
            state = Path(state_value)
            if not state.is_file():
                raise ValueError(f"bundle path does not exist: {state}")
        specs.append(
            {
                "seed_manifest": seed,
                "chain_workdir": workdir,
                "first_round": first_round,
                "state": state,
            }
        )
    return specs


def validate_chain_adjacency(
    previous: dict[str, Any], next_seed: Path, label: str
) -> str:
    if file_sha256(next_seed) == previous.get("final_manifest_sha256"):
        return "identical terminal manifest"
    previous_manifest = Path(previous["final_manifest"])
    previous_document = load_json(previous_manifest)
    next_document = load_json(next_seed)
    if (
        previous_document.get("schema") == PROOF_SCHEMA
        and next_document.get("schema") == PROOF_SCHEMA
        and previous_document.get("formula") == next_document.get("formula")
        and previous_document.get("cubes") == next_document.get("cubes")
    ):
        return "independently replayed exact-cube retry"
    raise ValueError(f"{label} proof-chain segment boundary mismatch")


def audit_chain_segments(
    specs: list[dict[str, Any]],
    label: str,
    checker: Path,
    jobs: int,
    tool: Path,
) -> dict[str, Any]:
    audited: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        seed = spec["seed_manifest"]
        if audited:
            boundary = validate_chain_adjacency(audited[-1], seed, label)
            if int(spec["first_round"]) != int(audited[-1]["final_round"]):
                raise ValueError(f"{label} proof-chain segment round mismatch")
        else:
            boundary = "initial seed"
        result = audit_chain(
            seed,
            spec["chain_workdir"],
            spec["first_round"],
            checker,
            jobs,
            tool,
            spec["state"],
        )
        result["boundary_from_previous"] = boundary
        audited.append(result)
        if index + 1 < len(specs) and result.get("complete_unsat"):
            raise ValueError(f"{label} has a segment after a complete proof chain")
    return {
        "segment_count": len(audited),
        "segments": audited,
        "complete_unsat": bool(audited[-1]["complete_unsat"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.jobs <= 0:
        parser.error("--jobs must be positive")
    if not arguments.bundle.is_file() or not arguments.checker.is_file():
        parser.error("bundle or checker does not exist")
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite audit manifest {arguments.manifest}")

    bundle = load_json(arguments.bundle)
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("unexpected fixed-pair proof-bundle schema")
    closed_spec = bundle.get("closed")
    open_spec = bundle.get("open")
    if not isinstance(closed_spec, dict) or not isinstance(open_spec, dict):
        raise ValueError("bundle closed/open sections must be objects")

    formula_path = required_path(bundle, "formula")
    forest_manifest = required_path(bundle, "forest_manifest")
    initial_cover = required_path(bundle, "initial_cover")
    closed_segments = chain_specs(closed_spec, "closed")
    closed_seed = closed_segments[0]["seed_manifest"]
    open_initial = required_path(open_spec, "initial_manifest")
    open_frontier = required_path(open_spec, "frontier_manifest")
    open_refinement = required_path(open_spec, "refinement_manifest")
    open_segments = chain_specs(open_spec, "open")
    open_seed = open_segments[0]["seed_manifest"]

    _, _, variables, clauses = read_cnf(formula_path)
    formula = {
        "path": str(formula_path),
        "sha256": file_sha256(formula_path),
        "variables": variables,
        "clauses": clauses,
    }
    forest = load_json(forest_manifest)
    if forest.get("schema") != FOREST_SCHEMA:
        raise ValueError("unexpected proof-forest schema")
    forest_root = forest_manifest.parent
    closed_cubes_path = forest_root / forest["closed"]["path"]
    open_cubes_path = forest_root / forest["open"]["path"]
    closed_cubes = cube_binding(
        closed_cubes_path, int(forest["closed"]["count"])
    )
    open_cubes = cube_binding(open_cubes_path, int(forest["open"]["count"]))
    validate_cube_binding(closed_cubes, forest["closed"], "proof forest closed")
    validate_cube_binding(open_cubes, forest["open"], "proof forest open")

    root = Path(__file__).resolve().parents[1]
    forest_audit = run_json_tool(
        [str(root / "tools" / "audit_proof_forest.py"), str(forest_manifest)],
        "proof-forest audit",
    )
    if forest_audit.get("all_root_refinements_cover") is not True:
        raise ValueError("proof forest does not cover every initial root")
    cover_audit = audit_initial_cover(forest_manifest, initial_cover)

    closed_document = load_json(closed_seed)
    open_document = load_json(open_initial)
    open_seed_document = load_json(open_seed)
    validate_proof_binding(closed_document, formula, closed_cubes, "closed seed")
    validate_proof_binding(open_document, formula, open_cubes, "open initial")

    audit_tool = root / "tools" / "audit_materialized_cube_proofs.py"
    open_initial_audit = audit_proof_manifest(
        open_initial, arguments.checker, arguments.jobs, audit_tool
    )
    frontier_document = load_json(open_frontier)
    parents_path = Path(frontier_document["output"])
    unknown_indices, unknown = verify_frontier(
        open_initial, open_document, parents_path, open_frontier
    )
    refinement_document = load_json(open_refinement)
    children_path = Path(refinement_document["children"]["path"])
    refine_results_path = Path(refinement_document["results"]["path"])
    refined = verify_refinement(
        parents_path, children_path, refine_results_path, open_refinement
    )
    if refined != len(unknown):
        raise ValueError("manual open refinement does not cover the UNKNOWN frontier")
    validate_proof_binding(
        open_seed_document,
        formula,
        cube_binding(children_path, 2 * refined),
        "open chain seed",
    )

    chain_tool = root / "tools" / "audit_materialized_proof_chain.py"
    closed_chain = audit_chain_segments(
        closed_segments, "closed", arguments.checker, arguments.jobs, chain_tool
    )
    open_chain = audit_chain_segments(
        open_segments, "open", arguments.checker, arguments.jobs, chain_tool
    )
    fixed_pair_unsat = bool(
        closed_chain["complete_unsat"] and open_chain["complete_unsat"]
    )
    result = {
        "schema": AUDIT_SCHEMA,
        "bundle": str(arguments.bundle),
        "bundle_sha256": file_sha256(arguments.bundle),
        "formula": formula,
        "checker": {
            "path": str(arguments.checker),
            "sha256": file_sha256(arguments.checker),
        },
        "initial_cover": cover_audit,
        "proof_forest": {
            "manifest": str(forest_manifest),
            "manifest_sha256": file_sha256(forest_manifest),
            "audit": forest_audit,
        },
        "closed": {
            "leaf_count": int(forest["closed"]["count"]),
            "seed_manifest": str(closed_seed),
            "seed_manifest_sha256": file_sha256(closed_seed),
            "chain": closed_chain,
        },
        "open": {
            "leaf_count": int(forest["open"]["count"]),
            "initial_manifest": str(open_initial),
            "initial_manifest_sha256": file_sha256(open_initial),
            "initial_audit": open_initial_audit,
            "unknown_indices": unknown_indices,
            "frontier_manifest": str(open_frontier),
            "frontier_manifest_sha256": file_sha256(open_frontier),
            "refinement_manifest": str(open_refinement),
            "refinement_manifest_sha256": file_sha256(open_refinement),
            "refined_parents": refined,
            "seed_manifest": str(open_seed),
            "seed_manifest_sha256": file_sha256(open_seed),
            "chain": open_chain,
        },
        "fixed_pair_unsat": fixed_pair_unsat,
    }
    if not fixed_pair_unsat and not arguments.allow_partial:
        raise ValueError("fixed-pair bundle remains incomplete")
    if arguments.manifest is not None:
        arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
        temporary = arguments.manifest.with_suffix(arguments.manifest.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(arguments.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
