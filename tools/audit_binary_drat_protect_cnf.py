#!/usr/bin/env python3
"""Independently audit a protected-CNF binary DRAT composition.

The production composer identifies protected clauses with a short hash.  This
auditor deliberately does not import that implementation and instead retains
the exact canonical literal tuples from the CNF.  It reconstructs the expected
output byte stream from the source fragments, checks every manifest count and
hash, and optionally binds or reruns the proof checker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, BinaryIO


AUDIT_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition-audit.v1"
COMPOSITION_SCHEMA = "ramsey55.binary-drat-protected-cnf-composition.v1"
COUNT_KEYS = (
    "additions",
    "retained_deletions",
    "dropped_protected_deletions",
    "empty_additions",
    "empty_deletions",
)
MAX_DRAT_VARIABLE = 2_147_483_647


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def validate_file_record(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"manifest lacks {label} file record")
    if not isinstance(value.get("path"), str) or not value["path"]:
        raise ValueError(f"manifest has invalid {label} path")
    digest = value.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"manifest has invalid {label} hash")
    if not isinstance(value.get("size"), int) or value["size"] < 0:
        raise ValueError(f"manifest has invalid {label} size")
    return value


def resolve_path(root: Path, recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else root / path


def check_regular_file(
    value: Any, label: str, root: Path
) -> tuple[dict[str, Any], Path]:
    record = validate_file_record(value, label)
    path = resolve_path(root, record["path"])
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if path.stat().st_size != record["size"]:
        raise ValueError(f"{label} size mismatch: {path}")
    return record, path


def parse_nonnegative(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"invalid {label}") from error
    if parsed < 0:
        raise ValueError(f"negative {label}")
    return parsed


def read_cnf(path: Path) -> tuple[set[tuple[int, ...]], int, int, str]:
    """Parse DIMACS and retain exact sorted clauses rather than fingerprints."""
    variables: int | None = None
    declared_clauses: int | None = None
    clauses: set[tuple[int, ...]] = set()
    clause: list[int] = []
    clause_count = 0
    digest = hashlib.sha256()
    with path.open("rb") as raw:
        for raw_line_number, raw_line in enumerate(raw, 1):
            digest.update(raw_line)
            try:
                line = raw_line.decode("ascii")
            except UnicodeDecodeError as error:
                raise ValueError(
                    f"non-ASCII CNF at line {raw_line_number}: {path}"
                ) from error
            stripped = line.strip()
            if not stripped or stripped.startswith("c"):
                continue
            fields = stripped.split()
            if fields[0] == "p":
                if variables is not None or clause or len(fields) != 4:
                    raise ValueError(f"invalid CNF header at line {raw_line_number}")
                if fields[1] != "cnf":
                    raise ValueError(
                        f"unsupported DIMACS kind at line {raw_line_number}"
                    )
                variables = parse_nonnegative(fields[2], "CNF variable count")
                declared_clauses = parse_nonnegative(fields[3], "CNF clause count")
                if variables > 2_147_483_647:
                    raise ValueError("DIMACS variable count is outside int32 range")
                continue
            if variables is None:
                raise ValueError(f"CNF clause precedes header at line {raw_line_number}")
            for field in fields:
                try:
                    literal = int(field)
                except ValueError as error:
                    raise ValueError(
                        f"invalid CNF literal at line {raw_line_number}"
                    ) from error
                if literal:
                    if abs(literal) > variables:
                        raise ValueError(
                            f"CNF literal outside header at line {raw_line_number}"
                        )
                    clause.append(literal)
                else:
                    clauses.add(tuple(sorted(clause)))
                    clause_count += 1
                    clause = []
    if variables is None or declared_clauses is None:
        raise ValueError("CNF header is missing")
    if clause:
        raise ValueError("unterminated final CNF clause")
    if clause_count != declared_clauses:
        raise ValueError(
            f"CNF clause count {clause_count} does not match header "
            f"{declared_clauses}"
        )
    return clauses, variables, clause_count, digest.hexdigest()


def decode_clause(raw: bytes, label: str) -> tuple[bool, tuple[int, ...]]:
    if not raw or raw[0] not in (ord("a"), ord("d")):
        raise ValueError(f"invalid binary DRAT clause marker in {label}")
    literals: list[int] = []
    encoded = 0
    shift = 0
    for byte in raw[1:]:
        encoded |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            if shift > 35:
                raise ValueError(f"oversized binary DRAT literal in {label}")
            continue
        variable = encoded >> 1
        if variable == 0 or variable > MAX_DRAT_VARIABLE:
            raise ValueError(
                f"binary DRAT literal outside signed int32 range in {label}"
            )
        literals.append(-variable if encoded & 1 else variable)
        encoded = 0
        shift = 0
    if shift:
        raise ValueError(f"unterminated binary DRAT literal in {label}")
    return raw[0] == ord("a"), tuple(literals)


def clauses(stream: BinaryIO, label: str):
    pending = b""
    while True:
        block = stream.read(1 << 23)
        if not block:
            break
        framed = (pending + block).split(b"\0")
        pending = framed.pop()
        yield block, framed
    if pending:
        raise ValueError(f"unterminated binary DRAT clause in {label}")


def zero_counts() -> dict[str, int]:
    return {key: 0 for key in COUNT_KEYS}


def validate_counts(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(COUNT_KEYS):
        raise ValueError(f"invalid {label} composition counts")
    if not all(isinstance(value[key], int) and value[key] >= 0 for key in COUNT_KEYS):
        raise ValueError(f"invalid {label} composition count value")
    return value


def audit_fragment(
    path: Path,
    protected: set[tuple[int, ...]],
    expected_output: Any,
) -> tuple[dict[str, int], str, int]:
    counts = zero_counts()
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block, framed in clauses(stream, str(path)):
            digest.update(block)
            size += len(block)
            for raw in framed:
                addition, literals = decode_clause(raw, str(path))
                if addition:
                    if not literals:
                        raise ValueError(f"source fragment has empty addition: {path}")
                    counts["additions"] += 1
                    expected_output.update(raw)
                    expected_output.update(b"\0")
                elif tuple(sorted(literals)) in protected:
                    counts["dropped_protected_deletions"] += 1
                else:
                    counts["retained_deletions"] += 1
                    counts["empty_deletions"] += not literals
                    expected_output.update(raw)
                    expected_output.update(b"\0")
    return counts, digest.hexdigest(), size


def sum_counts(parts: list[dict[str, int]], append_empty: bool) -> dict[str, int]:
    total = zero_counts()
    for part in parts:
        for key in COUNT_KEYS:
            total[key] += part[key]
    if append_empty:
        total["additions"] += 1
        total["empty_additions"] += 1
    return total


def exact_verified_line(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return any(line.strip("\r") == "s VERIFIED" for line in text.splitlines())


def audit(
    manifest_path: Path,
    root: Path,
    checker_log_path: Path | None,
    checker_path: Path | None,
    rerun_checker: bool,
) -> dict[str, Any]:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != COMPOSITION_SCHEMA:
        raise ValueError("unexpected composition manifest schema")
    if document.get("clause_fingerprint") != (
        "blake2b-128(sorted signed int32 literals)"
    ):
        raise ValueError("unexpected producer fingerprint declaration")
    if not isinstance(document.get("append_empty"), bool):
        raise ValueError("manifest has invalid append_empty policy")

    cnf_record, cnf_path = check_regular_file(document.get("cnf"), "cnf", root)
    protected, variables, cnf_clauses, cnf_sha256 = read_cnf(cnf_path)
    if cnf_sha256 != cnf_record["sha256"]:
        raise ValueError(f"cnf hash mismatch: {cnf_path}")
    if document.get("cnf_variables") != variables:
        raise ValueError("manifest CNF variable count mismatch")
    if document.get("cnf_clauses") != cnf_clauses:
        raise ValueError("manifest CNF clause count mismatch")
    if document.get("unique_protected_clause_fingerprints") != len(protected):
        raise ValueError("manifest unique protected clause count mismatch")

    expected_output = hashlib.sha256()
    fragments = document.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        raise ValueError("manifest has no source fragments")
    fragment_counts: list[dict[str, int]] = []
    for index, value in enumerate(fragments):
        record, path = check_regular_file(value, f"fragment {index}", root)
        recorded_counts = validate_counts(
            record.get("composition_counts"), f"fragment {index}"
        )
        observed_counts, observed_hash, observed_size = audit_fragment(
            path, protected, expected_output
        )
        if observed_hash != record["sha256"]:
            raise ValueError(f"fragment {index} hash mismatch: {path}")
        if observed_size != record["size"]:
            raise ValueError(f"fragment {index} size changed while reading: {path}")
        if observed_counts != recorded_counts:
            raise ValueError(f"fragment {index} composition counts mismatch")
        fragment_counts.append(observed_counts)

    append_empty = document["append_empty"]
    if append_empty:
        expected_output.update(b"a\0")
    expected_counts = sum_counts(fragment_counts, append_empty)
    if validate_counts(document.get("composition_counts"), "total") != expected_counts:
        raise ValueError("total composition counts mismatch")

    output_record, output_path = check_regular_file(
        document.get("output"), "output", root
    )
    # Every source clause was decoded above while constructing the expected
    # output digest.  A second clause-by-clause output decode adds no evidence:
    # equality with that digest already binds the complete byte stream,
    # including its framing, counts, and final empty clause.  Hash the output
    # in large blocks so multi-gigabyte audits do not repeat the expensive
    # Python literal decoder.
    output_sha256 = file_sha256(output_path)
    if output_sha256 != output_record["sha256"]:
        raise ValueError(f"output hash mismatch: {output_path}")
    if output_sha256 != expected_output.hexdigest():
        raise ValueError("output is not the exact protected-CNF composition")
    if append_empty:
        if expected_counts["empty_additions"] != 1:
            raise ValueError("output does not end in exactly one appended empty addition")
    elif expected_counts["empty_additions"]:
        raise ValueError("output unexpectedly contains an empty addition")

    checker_log: dict[str, Any] | None = None
    if checker_log_path is not None:
        if not checker_log_path.is_file():
            raise ValueError(f"checker log does not exist: {checker_log_path}")
        if not exact_verified_line(checker_log_path):
            raise ValueError("checker log lacks an exact s VERIFIED line")
        checker_log = file_record(checker_log_path)
        checker_log["verified"] = True

    checker: dict[str, Any] | None = None
    if checker_path is not None:
        if not checker_path.is_file():
            raise ValueError(f"checker does not exist: {checker_path}")
        checker = file_record(checker_path)

    checker_rerun: dict[str, Any] | None = None
    if rerun_checker:
        if checker_path is None:
            raise ValueError("--rerun-checker requires --checker")
        completed = subprocess.run(
            [str(checker_path), str(cnf_path), str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode or not any(
            line.strip("\r") == "s VERIFIED" for line in completed.stdout.splitlines()
        ):
            raise RuntimeError(
                f"checker rerun rejected output (exit {completed.returncode})"
            )
        checker_rerun = {
            "returncode": completed.returncode,
            "verified": True,
            "output_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
        }

    return {
        "schema": AUDIT_SCHEMA,
        "manifest": file_record(manifest_path),
        "cnf": cnf_record,
        "cnf_exact_unique_clauses": len(protected),
        "fragments": len(fragments),
        "composition_counts": expected_counts,
        "output": output_record,
        "checker": checker,
        "checker_log": checker_log,
        "checker_rerun": checker_rerun,
        "structurally_verified": True,
        "checker_verified": checker_log is not None or checker_rerun is not None,
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="base directory for relative paths recorded in the manifest",
    )
    parser.add_argument("--checker-log", type=Path)
    parser.add_argument("--checker", type=Path)
    parser.add_argument("--rerun-checker", action="store_true")
    arguments = parser.parse_args()
    if not arguments.manifest.is_file():
        parser.error(f"manifest does not exist: {arguments.manifest}")
    report = audit(
        arguments.manifest,
        arguments.root,
        arguments.checker_log,
        arguments.checker,
        arguments.rerun_checker,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
