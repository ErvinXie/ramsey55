#!/usr/bin/env python3
"""Audit the complete generated HOL4 enumeration artifact family."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "ramsey55.upstream-hol-enumeration-artifacts.v1"
SCRIPT_SUFFIX = "Script.sml"
THEORY_SUFFIXES = (
    "Theory.sml",
    "Theory.sig",
    "Theory.dat",
    "Theory.ui",
    "Theory.uo",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path, *, relative_to: Path | None = None) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    recorded_path = path.relative_to(relative_to) if relative_to else path
    return {
        "path": str(recorded_path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def audit(
    directory: Path,
    expected_count: int,
    evidence: list[Path] | None = None,
) -> dict[str, object]:
    if expected_count <= 0:
        raise ValueError("expected count must be positive")
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"missing enumeration directory: {directory}")

    scripts = sorted(directory.glob(f"ramseyEnum*{SCRIPT_SUFFIX}"))
    if len(scripts) != expected_count:
        raise ValueError(
            f"expected {expected_count} enumeration scripts, found {len(scripts)}"
        )

    expected_bases = {script.name[: -len(SCRIPT_SUFFIX)] for script in scripts}
    observed_bases: dict[str, set[str]] = {suffix: set() for suffix in THEORY_SUFFIXES}
    for suffix in THEORY_SUFFIXES:
        observed_bases[suffix] = {
            path.name[: -len(suffix)]
            for path in directory.glob(f"ramseyEnum*{suffix}")
        }
        missing = sorted(expected_bases - observed_bases[suffix])
        extra = sorted(observed_bases[suffix] - expected_bases)
        if missing or extra:
            raise ValueError(
                f"{suffix} set mismatch: missing={missing[:5]}, extra={extra[:5]}"
            )

    records = []
    for script in scripts:
        base = script.name[: -len(SCRIPT_SUFFIX)]
        theories = {
            suffix: artifact(directory / f"{base}{suffix}", relative_to=directory)
            for suffix in THEORY_SUFFIXES
        }
        records.append(
            {
                "theory": base,
                "script": artifact(script, relative_to=directory),
                "artifacts": theories,
            }
        )

    evidence_records = [artifact(path.resolve()) for path in evidence or []]
    return {
        "schema": SCHEMA,
        "claim": (
            "complete nonempty generated artifact coverage for the listed HOL4 "
            "enumeration scripts; final enumf and gluing stages are separate"
        ),
        "directory": str(directory),
        "expected_scripts": expected_count,
        "records": records,
        "evidence": evidence_records,
        "summary": {
            "scripts": len(records),
            "complete_five_artifact_theories": len(records),
            "complete": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-count", type=int, default=1239)
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    try:
        document = audit(
            arguments.directory, arguments.expected_count, arguments.evidence
        )
    except ValueError as error:
        parser.error(str(error))
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"audited {document['summary']['scripts']} complete enumeration theories; "
        f"wrote {arguments.output}"
    )


if __name__ == "__main__":
    main()
