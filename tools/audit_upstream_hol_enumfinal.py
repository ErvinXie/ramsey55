#!/usr/bin/env python3
"""Audit the generated, built, and freshly loaded HOL4 enumf theory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "ramsey55.upstream-hol-enumfinal-audit.v1"
ENUMERATION_SCHEMA = "ramsey55.upstream-hol-enumeration-artifacts.v1"
THEORY_SUFFIXES = (
    "Script.sml",
    "Theory.sml",
    "Theory.sig",
    "Theory.dat",
    "Theory.ui",
    "Theory.uo",
)
EXPECTED_THEOREMS = (
    ("R355", 5, 3, 5, True),
    ("R356", 6, 3, 5, True),
    ("R357", 7, 3, 5, True),
    ("R358", 8, 3, 5, True),
    ("R359", 9, 3, 5, True),
    ("R3510", 10, 3, 5, True),
    ("R3511", 11, 3, 5, True),
    ("R3512", 12, 3, 5, True),
    ("R3513", 13, 3, 5, True),
    ("R3514", 14, 3, 5, False),
    ("R444", 4, 4, 4, True),
    ("R445", 5, 4, 4, True),
    ("R446", 6, 4, 4, True),
    ("R447", 7, 4, 4, True),
    ("R448", 8, 4, 4, True),
    ("R449", 9, 4, 4, True),
    ("R4410", 10, 4, 4, True),
    ("R4411", 11, 4, 4, True),
    ("R4412", 12, 4, 4, True),
    ("R4413", 13, 4, 4, True),
    ("R4414", 14, 4, 4, True),
    ("R4415", 15, 4, 4, True),
    ("R4416", 16, 4, 4, True),
    ("R4417", 17, 4, 4, True),
    ("R4418", 18, 4, 4, False),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def require_exit_zero(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"^\s*Exit status:\s*(\d+)\s*$", text, re.MULTILINE)
    if matches != ["0"]:
        raise ValueError(f"expected one GNU-time exit status 0: {path}")


def require_clean_log(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    forbidden = (
        "Static Errors",
        "uncaught exception",
        "RAMSEY55_ENUMF_KERNEL_AUDIT_FAIL",
        "error:",
    )
    lowered = text.lower()
    for token in forbidden:
        if token.lower() in lowered:
            raise ValueError(f"forbidden failure marker {token!r} in {path}")
    return text


def read_enumeration_manifest(path: Path, upstream_root: Path) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    summary = manifest.get("summary", {})
    if manifest.get("schema") != ENUMERATION_SCHEMA:
        raise ValueError("unexpected enumeration audit schema")
    if manifest.get("directory") != str((upstream_root / "src/enump").resolve()):
        raise ValueError("enumeration audit directory mismatch")
    if (
        summary.get("complete") is not True
        or summary.get("scripts") != 1239
        or summary.get("complete_five_artifact_theories") != 1239
        or len(manifest.get("records", [])) != 1239
    ):
        raise ValueError("enumeration audit is not complete")
    return manifest


def validate_generated_script(
    final_directory: Path, enumeration_manifest: dict[str, object]
) -> tuple[Path, Path, Path]:
    open_template = final_directory / "open_template"
    script_template = final_directory / "ramseyEnumScript_template"
    generated_script = final_directory / "ramseyEnumScript.sml"
    for path in (open_template, script_template, generated_script):
        artifact(path)
    words = open_template.read_text(encoding="utf-8").split()
    if not words or words[0] != "open" or len(words[1:]) != len(set(words[1:])):
        raise ValueError("invalid enumf open_template")
    expected = {
        record["theory"] + "Theory" for record in enumeration_manifest["records"]
    }
    if set(words[1:]) != expected:
        raise ValueError("enumf open_template theory set mismatch")
    expected_script = open_template.read_bytes() + script_template.read_bytes()
    if generated_script.read_bytes() != expected_script:
        raise ValueError("generated enumf script is not the exact template concatenation")
    return open_template, script_template, generated_script


def require_build_markers(text: str, expected_memory_mb: int) -> None:
    memory = re.findall(r"^RAMSEY55_ENUMF_MEMORY_MB\s+(\d+)\s*$", text, re.MULTILINE)
    if memory != [str(expected_memory_mb)]:
        raise ValueError("build memory marker does not match expected limit")


def require_buildheap_log(path: Path) -> None:
    text = require_clean_log(path)
    required = (
        'Created theory "ramseyEnum"',
        'Exporting theory "ramseyEnum" ... done.',
        'Theory "ramseyEnum" took ',
    )
    if any(text.count(marker) != 1 for marker in required):
        raise ValueError("enumf buildheap log lacks exact theory success markers")
    for name, _, _, _, _ in EXPECTED_THEOREMS:
        marker = f'Saved theorem _____ "{name}"'
        if text.count(marker) != 1:
            raise ValueError(f"enumf buildheap log lacks one theorem marker: {name}")


def require_load_markers(text: str, expected_memory_mb: int) -> None:
    memory = re.findall(
        r"^RAMSEY55_ENUMF_LOAD_MEMORY_MB\s+(\d+)\s*$", text, re.MULTILINE
    )
    if memory != [str(expected_memory_mb)]:
        raise ValueError("load memory marker does not match expected limit")
    suffix = "F EXACT_BASE_HYPOTHESES (COVER|NO_COVER) NO_FALSE_HYP"
    observed = [
        (name, int(size), int(bluen), int(redn), cover == "COVER")
        for name, size, bluen, redn, cover in re.findall(
            rf"^RAMSEY55_ENUMF_LOAD\s+(R\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+{suffix}$",
            text,
            re.MULTILINE,
        )
    ]
    if observed != list(EXPECTED_THEOREMS):
        raise ValueError("fresh-load theorem markers are not exact and ordered")
    final_marker = f"RAMSEY55_ENUMF_KERNEL_LOAD_{len(EXPECTED_THEOREMS)}_OK"
    last_marker = (
        f"RAMSEY55_ENUMF_LOAD {EXPECTED_THEOREMS[-1][0]} "
        f"{EXPECTED_THEOREMS[-1][1]} {EXPECTED_THEOREMS[-1][2]} "
        f"{EXPECTED_THEOREMS[-1][3]} F EXACT_BASE_HYPOTHESES NO_COVER "
        "NO_FALSE_HYP"
    )
    if text.count(final_marker) != 1 or text.find(final_marker) < text.find(last_marker):
        raise ValueError(f"expected one final fresh-load marker: {final_marker}")


def audit(
    enumeration_audit: Path,
    upstream_root: Path,
    build_log: Path,
    build_time_log: Path,
    load_log: Path,
    load_time_log: Path,
    expected_memory_mb: int,
    evidence: list[Path] | None = None,
) -> dict[str, object]:
    if expected_memory_mb <= 0:
        raise ValueError("expected memory must be positive")
    upstream_root = upstream_root.resolve()
    enumeration_audit = enumeration_audit.resolve()
    enumeration_manifest = read_enumeration_manifest(enumeration_audit, upstream_root)
    final_directory = upstream_root / "src/enumf"
    open_template, script_template, generated_script = validate_generated_script(
        final_directory, enumeration_manifest
    )
    build_text = require_clean_log(build_log)
    load_text = require_clean_log(load_log)
    require_build_markers(build_text, expected_memory_mb)
    require_load_markers(load_text, expected_memory_mb)
    require_exit_zero(build_time_log)
    require_exit_zero(load_time_log)

    files = {
        suffix: artifact(final_directory / f"ramseyEnum{suffix}")
        for suffix in THEORY_SUFFIXES
    }
    buildheap_log = final_directory / "buildheap/buildheap_ramseyEnumScript"
    require_buildheap_log(buildheap_log)

    return {
        "schema": SCHEMA,
        "claim": (
            "the hash-bound 1,239-theory enumeration manifest generated the exact "
            "enumf import/script pair; HOL4 built all 25 listed final Ramsey "
            "theorems, and a fresh HOL4 session loaded each with conclusion F, "
            "the exact base hypotheses, and the expected intermediate cover "
            "hypothesis; the two terminal theorems have no cover hypothesis"
        ),
        "verified": True,
        "auditor": artifact(Path(__file__)),
        "upstream_root": str(upstream_root),
        "enumeration_audit": artifact(enumeration_audit),
        "enumeration_audit_schema": ENUMERATION_SCHEMA,
        "enumeration_theories": 1239,
        "final_directory": str(final_directory.resolve()),
        "generated_inputs": {
            "open_template": artifact(open_template),
            "script_template": artifact(script_template),
            "generated_script": artifact(generated_script),
        },
        "files": files,
        "buildheap_log": artifact(buildheap_log),
        "build_log": artifact(build_log),
        "build_time_log": artifact(build_time_log),
        "load_log": artifact(load_log),
        "load_time_log": artifact(load_time_log),
        "evidence": [artifact(path.resolve()) for path in evidence or []],
        "summary": {
            "enumeration_theories": 1239,
            "complete_final_theory_artifacts": len(THEORY_SUFFIXES),
            "saved_final_theorems": len(EXPECTED_THEOREMS),
            "fresh_loaded_exact_shape_theorems": len(EXPECTED_THEOREMS),
            "fresh_loaded_theorems_without_false_hypothesis": len(EXPECTED_THEOREMS),
            "build_and_load_memory_limit_mb": expected_memory_mb,
        },
        "theorems": [
            {
                "name": name,
                "order": size,
                "blue_clique_order": bluen,
                "red_clique_order": redn,
                "fresh_loaded_conclusion": "F",
                "fresh_loaded_exact_hypotheses": (
                    [
                        "edge symmetry",
                        f"C{bluen}{redn}{size}b",
                        f"C{bluen}{redn}{size}r",
                    ]
                    + ([f"G{bluen}{redn}{size}"] if has_cover else [])
                ),
                "fresh_loaded_has_cover_hypothesis": has_cover,
                "fresh_loaded_contains_false_hypothesis": False,
            }
            for name, size, bluen, redn, has_cover in EXPECTED_THEOREMS
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("enumeration_audit", type=Path)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--build-log", type=Path, required=True)
    parser.add_argument("--build-time-log", type=Path, required=True)
    parser.add_argument("--load-log", type=Path, required=True)
    parser.add_argument("--load-time-log", type=Path, required=True)
    parser.add_argument("--expected-memory-mb", type=int, required=True)
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"refusing to overwrite {arguments.output}")
    try:
        document = audit(
            arguments.enumeration_audit,
            arguments.upstream_root,
            arguments.build_log,
            arguments.build_time_log,
            arguments.load_log,
            arguments.load_time_log,
            arguments.expected_memory_mb,
            arguments.evidence,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"audited {document['summary']['fresh_loaded_exact_shape_theorems']} "
        "fresh-loaded HOL4 enumf theorems"
    )


if __name__ == "__main__":
    main()
