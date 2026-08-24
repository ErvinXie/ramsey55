#!/usr/bin/env python3
"""Compose and independently verify one replayed CaDiCaL DFS checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


SCHEMA = "ramsey55.cadical-dfs-checkpoint-finalization.v1"
PROMOTION_SCHEMA = "ramsey55.checked-binary-drat-fragment-promotion.v1"
REPLAY_SCHEMAS = {
    "ramsey55.cadical-dfs-prefix-replay.v1",
    "ramsey55.cadical-dfs-prefix-replay.v2",
}
RACE_SELECTION_SCHEMA = "ramsey55.cadical-dfs-race-selection.v3"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def scan_binary_drat(path: Path) -> dict[str, int]:
    """Validate clause framing and count empty additions/deletions."""
    additions = deletions = empty_additions = empty_deletions = 0
    pending = b""
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            clauses = (pending + block).split(b"\0")
            pending = clauses.pop()
            for clause in clauses:
                if not clause or clause[0] not in (ord("a"), ord("d")):
                    raise ValueError(f"invalid binary DRAT framing in {path}")
                if clause[0] == ord("a"):
                    additions += 1
                    empty_additions += len(clause) == 1
                else:
                    deletions += 1
                    empty_deletions += len(clause) == 1
    if pending:
        raise ValueError(f"unterminated binary DRAT clause in {path}")
    return {
        "additions": additions,
        "deletions": deletions,
        "empty_additions": empty_additions,
        "empty_deletions": empty_deletions,
    }


def read_producer_log(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        fields = raw.split("\t", 1)
        if len(fields) != 2 or not fields[0] or fields[0] in records:
            raise ValueError(f"invalid producer log row {line_number}: {path}")
        records[fields[0]] = fields[1]
    required = {
        "proof_fragment": "1",
        "root_index": "all",
        "status": "20",
        "cubes": "1",
    }
    for key, expected in required.items():
        if records.get(key) != expected:
            raise ValueError(f"producer log {path} lacks {key}={expected}")
    for key in ("attempts", "splits", "maximum_extra_depth"):
        if key not in records or int(records[key]) < 0:
            raise ValueError(f"producer log {path} has invalid {key}")
    return records


def validate_file_record(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"finalization manifest lacks {label} file record")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise ValueError(f"finalization manifest has invalid {label} path")
    digest = record.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"finalization manifest has invalid {label} hash")
    if not isinstance(record.get("size"), int) or record["size"] < 0:
        raise ValueError(f"finalization manifest has invalid {label} size")
    return record


def read_finalized_child(
    path: Path, proof_record: dict[str, Any]
) -> dict[str, Any] | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(document, dict) or document.get("schema") not in (
        SCHEMA,
        PROMOTION_SCHEMA,
    ):
        raise ValueError(f"unexpected child finalization manifest schema: {path}")
    if document.get("checker_verified") is not True:
        raise ValueError(f"child finalization manifest is not checker-verified: {path}")
    output = validate_file_record(document.get("output_fragment"), "output_fragment")
    if output.get("contains_empty_addition") is not False:
        raise ValueError(
            f"child finalization manifest does not certify a no-empty fragment: {path}"
        )
    if (
        output["sha256"] != proof_record["sha256"]
        or output["size"] != proof_record["size"]
    ):
        raise ValueError(
            f"child proof does not match finalization manifest output: {path}"
        )
    standalone = validate_file_record(
        document.get("standalone_proof"), "standalone_proof"
    )
    if standalone.get("appended_empty_clause") is not True:
        raise ValueError(
            f"child finalization manifest lacks standalone empty-clause marker: {path}"
        )
    common_records = ("cnf", "checker", "checker_log")
    schema_records = (
        ("replay_manifest", "prefix")
        if document["schema"] == SCHEMA
        else ("source_composition_manifest", "source_composition_audit")
    )
    for label in (*common_records, *schema_records):
        validate_file_record(document.get(label), label)
    if document["schema"] == SCHEMA and (
        not isinstance(document.get("children"), list) or not document["children"]
    ):
        raise ValueError(f"child finalization manifest has no children: {path}")
    return {
        **file_record(path),
        "schema": document["schema"],
        "checker_verified": True,
        "output_fragment_sha256": output["sha256"],
        "output_fragment_size": output["size"],
    }


def read_completed_forest_selection(
    path: Path,
    proof_record: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    """Validate one completed race that covers the whole replay frontier."""
    from select_cadical_dfs_race import inspect_race, read_roots

    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("schema") != RACE_SELECTION_SCHEMA
    ):
        raise ValueError(f"unexpected forest race-selection schema: {path}")
    source_record = validate_file_record(document.get("source_root"), "source_root")
    source_path = Path(source_record["path"])
    if not source_path.is_file():
        raise ValueError(f"forest race source does not exist: {source_path}")
    actual_source = file_record(source_path)
    if (
        actual_source["sha256"] != source_record["sha256"]
        or actual_source["size"] != source_record["size"]
    ):
        raise ValueError("forest race source file does not match its record")
    if source_record["sha256"] != replay.get("output_sha256"):
        raise ValueError("forest race source does not match the replayed frontier")
    roots = read_roots(source_path)
    if document.get("root_count") != len(roots):
        raise ValueError("forest race root count does not match its source")
    if document.get("root_count") != replay.get("output_count"):
        raise ValueError("forest race does not cover the complete replayed frontier")

    races = document.get("races")
    if not isinstance(races, list) or not races:
        raise ValueError("forest race-selection manifest has no races")
    inspected: list[dict[str, Any]] = []
    for index, race in enumerate(races):
        if not isinstance(race, dict):
            raise ValueError(f"forest race {index} is not an object")
        race_proof = validate_file_record(race.get("proof"), f"race {index} proof")
        snapshot = validate_file_record(race.get("snapshot"), f"race {index} snapshot")
        producer = validate_file_record(
            race.get("producer_log"), f"race {index} producer_log"
        )
        checked = inspect_race(
            roots,
            Path(race_proof["path"]),
            Path(snapshot["path"]),
            Path(producer["path"]),
        )
        if checked != race:
            raise ValueError(f"forest race {index} does not replay exactly")
        inspected.append(checked)

    chosen_index = min(
        range(len(inspected)),
        key=lambda index: (
            not inspected[index]["completed"],
            inspected[index]["frontier_count"],
            inspected[index]["proof"]["size"],
            index,
        ),
    )
    if document.get("chosen_index") != chosen_index:
        raise ValueError("forest race chosen index violates the selection policy")
    chosen = inspected[chosen_index]
    if document.get("chosen_completed") is not True or not chosen["completed"]:
        raise ValueError("forest continuation is not complete")
    if chosen["frontier_count"] != 0 or any(chosen["root_frontier_counts"]):
        raise ValueError("completed forest continuation has a nonempty frontier")
    if document.get("chosen_proof_sha256") != chosen["proof"]["sha256"]:
        raise ValueError("forest chosen proof hash is inconsistent")
    if (
        chosen["proof"]["sha256"] != proof_record["sha256"]
        or chosen["proof"]["size"] != proof_record["size"]
        or Path(chosen["proof"]["path"]).resolve()
        != Path(proof_record["path"]).resolve()
    ):
        raise ValueError("forest continuation proof is not the selected proof")
    return {
        **file_record(path),
        "schema": RACE_SELECTION_SCHEMA,
        "root_count": len(roots),
        "chosen_index": chosen_index,
        "chosen_proof_sha256": chosen["proof"]["sha256"],
        "chosen_completed": True,
    }


def load_replay_manifest(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") not in REPLAY_SCHEMAS:
        raise ValueError("unexpected DFS replay manifest schema")
    return document


def atomic_json(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def copy_fragments(
    output: Path,
    fragments: list[Path],
    append_empty: bool,
    drop_deletions: bool = False,
) -> None:
    with output.open("wb") as target:
        for fragment in fragments:
            if not drop_deletions:
                with fragment.open("rb") as source:
                    shutil.copyfileobj(source, target, length=1 << 23)
                continue
            pending = b""
            with fragment.open("rb") as source:
                for block in iter(lambda: source.read(1 << 23), b""):
                    clauses = (pending + block).split(b"\0")
                    pending = clauses.pop()
                    for clause in clauses:
                        if not clause or clause[0] not in (ord("a"), ord("d")):
                            raise ValueError(
                                f"invalid binary DRAT framing in {fragment}"
                            )
                        if clause[0] == ord("a"):
                            target.write(clause)
                            target.write(b"\0")
            if pending:
                raise ValueError(f"unterminated binary DRAT clause in {fragment}")
        if append_empty:
            target.write(b"a\0")


def combine_scans(
    scans: list[dict[str, int]], drop_deletions: bool, append_empty: bool
) -> dict[str, int]:
    combined = {
        key: sum(scan[key] for scan in scans)
        for key in (
            "additions",
            "deletions",
            "empty_additions",
            "empty_deletions",
        )
    }
    if drop_deletions:
        combined["deletions"] = 0
        combined["empty_deletions"] = 0
    if append_empty:
        combined["additions"] += 1
        combined["empty_additions"] += 1
    return combined


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("replay_manifest", type=Path)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("output_fragment", type=Path)
    parser.add_argument("standalone_proof", type=Path)
    parser.add_argument("checker_log", type=Path)
    evidence_group = parser.add_mutually_exclusive_group(required=True)
    evidence_group.add_argument(
        "--child",
        action="append",
        nargs=2,
        metavar=("PROOF", "EVIDENCE"),
        help=(
            "ordered no-empty child proof and either its producer log or a "
            "checker-verified child finalization manifest"
        ),
    )
    evidence_group.add_argument(
        "--forest-continuation",
        nargs=2,
        metavar=("PROOF", "RACE_SELECTION"),
        help=(
            "one no-empty proof selected from a completed DFS race over the "
            "entire replayed frontier"
        ),
    )
    parser.add_argument(
        "--checker", type=Path, default=Path(".tools/src/drat-trim/drat-trim")
    )
    parser.add_argument(
        "--checker-option",
        action="append",
        default=[],
        help="option appended to the checker command and recorded in the manifest",
    )
    parser.add_argument(
        "--drop-deletions",
        action="store_true",
        help=(
            "omit every binary DRAT deletion while composing, producing a "
            "monotone addition-only proof"
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()

    inputs = [
        arguments.cnf,
        arguments.replay_manifest,
        arguments.prefix,
        arguments.checker,
    ]
    child_pairs = [(Path(proof), Path(log)) for proof, log in (arguments.child or [])]
    forest_continuation = (
        tuple(Path(value) for value in arguments.forest_continuation)
        if arguments.forest_continuation is not None
        else None
    )
    if forest_continuation is not None:
        child_pairs = [forest_continuation]
    inputs.extend(path for pair in child_pairs for path in pair)
    for path in inputs:
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    outputs = [
        arguments.output_fragment,
        arguments.standalone_proof,
        arguments.checker_log,
        arguments.manifest,
    ]
    if any(path.exists() for path in outputs):
        parser.error("refusing to overwrite an output")
    temporaries = [path.with_suffix(path.suffix + ".tmp") for path in outputs[:-1]]
    if any(path.exists() for path in temporaries):
        parser.error("refusing to overwrite a temporary output")

    replay = load_replay_manifest(arguments.replay_manifest)
    if replay.get("proof_prefix_sha256") != file_sha256(arguments.prefix):
        raise ValueError("prefix hash does not match the DFS replay manifest")
    if forest_continuation is None and replay.get("output_count") != len(child_pairs):
        raise ValueError("child count does not match the replayed frontier")
    if forest_continuation is not None and (
        not isinstance(replay.get("output_count"), int) or replay["output_count"] < 1
    ):
        raise ValueError("forest continuation requires a nonempty replayed frontier")

    prefix_scan = scan_binary_drat(arguments.prefix)
    if prefix_scan["empty_additions"]:
        raise ValueError("proof prefix contains an embedded empty clause")
    children: list[dict[str, Any]] = []
    child_scans: list[dict[str, int]] = []
    for index, (proof, evidence) in enumerate(child_pairs):
        proof_scan = scan_binary_drat(proof)
        if proof_scan["empty_additions"]:
            raise ValueError(f"child proof {index} contains an embedded empty clause")
        proof_record = file_record(proof)
        child = {
            "index": index,
            "proof": {**proof_record, "binary_drat": proof_scan},
        }
        if forest_continuation is not None:
            child["frontier_start"] = 0
            child["frontier_count"] = replay["output_count"]
            child["race_selection_manifest"] = read_completed_forest_selection(
                evidence, proof_record, replay
            )
        else:
            finalized = read_finalized_child(evidence, proof_record)
            child["frontier_start"] = index
            child["frontier_count"] = 1
            if finalized is None:
                telemetry = read_producer_log(evidence)
                child["producer_log"] = {
                    **file_record(evidence),
                    "telemetry": telemetry,
                }
            else:
                child["finalization_manifest"] = finalized
        children.append(child)
        child_scans.append(proof_scan)

    component_scans = [prefix_scan, *child_scans]
    fragment_scan = combine_scans(
        component_scans, arguments.drop_deletions, append_empty=False
    )
    standalone_scan = combine_scans(
        component_scans, arguments.drop_deletions, append_empty=True
    )

    fragment_temporary, standalone_temporary, checker_log_temporary = temporaries
    try:
        copy_fragments(
            fragment_temporary,
            [arguments.prefix] + [proof for proof, _ in child_pairs],
            append_empty=False,
            drop_deletions=arguments.drop_deletions,
        )
        copy_fragments(
            standalone_temporary,
            [fragment_temporary],
            append_empty=True,
            drop_deletions=False,
        )
        completed = subprocess.run(
            [
                str(arguments.checker),
                str(arguments.cnf),
                str(standalone_temporary),
                *arguments.checker_option,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        checker_log_temporary.write_text(completed.stdout, encoding="utf-8")
        if completed.returncode or "s VERIFIED" not in completed.stdout:
            checker_log_temporary.replace(arguments.checker_log)
            raise RuntimeError(
                "proof checker rejected the standalone composition; "
                f"see {arguments.checker_log} (exit {completed.returncode})"
            )
        fragment_temporary.replace(arguments.output_fragment)
        standalone_temporary.replace(arguments.standalone_proof)
        checker_log_temporary.replace(arguments.checker_log)
    finally:
        for path in (fragment_temporary, standalone_temporary, checker_log_temporary):
            if path.exists():
                path.unlink()

    document = {
        "schema": SCHEMA,
        "cnf": file_record(arguments.cnf),
        "replay_manifest": file_record(arguments.replay_manifest),
        "prefix": {
            **file_record(arguments.prefix),
            "binary_drat": prefix_scan,
        },
        "composition": {
            "drop_deletions": arguments.drop_deletions,
            "frontier_cover": "forest" if forest_continuation is not None else "roots",
        },
        "children": children,
        "output_fragment": {
            **file_record(arguments.output_fragment),
            "binary_drat": fragment_scan,
            "contains_empty_addition": False,
        },
        "standalone_proof": {
            **file_record(arguments.standalone_proof),
            "binary_drat": standalone_scan,
            "appended_empty_clause": True,
        },
        "checker": file_record(arguments.checker),
        "checker_options": arguments.checker_option,
        "checker_log": file_record(arguments.checker_log),
        "checker_verified": True,
    }
    atomic_json(arguments.manifest, document)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
