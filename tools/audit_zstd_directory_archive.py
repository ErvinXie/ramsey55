#!/usr/bin/env python3
"""Independently audit a GNU-tar directory archive compressed with zstd."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, BinaryIO


ARCHIVE_SCHEMA = "ramsey55.zstd-directory-archive.v1"
AUDIT_SCHEMA = "ramsey55.zstd-directory-archive-audit.v1"
COPY_BLOCK_BYTES = 1 << 23


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(COPY_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_file_record(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"missing or malformed {label} record")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise ValueError(f"invalid {label} path")
    if not isinstance(record.get("bytes"), int) or record["bytes"] < 0:
        raise ValueError(f"invalid {label} byte count")
    if not valid_sha256(record.get("sha256")):
        raise ValueError(f"invalid {label} SHA-256")
    return record


def checked_file(record: object, label: str) -> tuple[Path, dict[str, Any]]:
    checked = validate_file_record(record, label)
    path = Path(checked["path"])
    if not path.is_file() or path.stat().st_size != checked["bytes"]:
        raise ValueError(f"{label} artifact mismatch: {path}")
    if file_sha256(path) != checked["sha256"]:
        raise ValueError(f"{label} artifact mismatch: {path}")
    return path, checked


def load_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid archive JSON: {path}") from error
    if not isinstance(document, dict):
        raise ValueError("archive manifest is not a JSON object")
    return document


def executable_version(path: Path) -> str:
    return subprocess.run(
        [str(path), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout.strip()


def checked_executable(record: object, override: Path | None, label: str) -> tuple[Path, dict[str, Any], str]:
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("path"), str)
        or not record["path"]
        or not valid_sha256(record.get("sha256"))
        or not isinstance(record.get("version"), str)
        or not record["version"]
    ):
        raise ValueError(f"invalid {label} executable record")
    path = override or Path(record["path"])
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f"missing {label} executable: {path}")
    if file_sha256(path) != record["sha256"]:
        raise ValueError(f"{label} executable hash mismatch")
    version = executable_version(path)
    if version != record["version"]:
        raise ValueError(f"{label} version mismatch")
    if label == "tar" and "GNU tar" not in version:
        raise ValueError("directory archives require GNU tar")
    return path, record, version


def directory_stats(path: Path) -> dict[str, int]:
    """Return lstat-based counts without following symbolic links."""
    counts = {
        "entries": 0,
        "directories": 0,
        "regular_files": 0,
        "symbolic_links": 0,
        "other_entries": 0,
        "apparent_bytes": 0,
        "allocated_bytes": 0,
    }
    pending = [path]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                stat = entry.stat(follow_symlinks=False)
                counts["entries"] += 1
                counts["allocated_bytes"] += stat.st_blocks * 512
                if entry.is_symlink():
                    counts["symbolic_links"] += 1
                elif entry.is_dir(follow_symlinks=False):
                    counts["directories"] += 1
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    counts["regular_files"] += 1
                    counts["apparent_bytes"] += stat.st_size
                else:
                    counts["other_entries"] += 1
    return counts


def validate_source_record(record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("missing or malformed source record")
    path = record.get("path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("invalid source path")
    if record.get("basename") != Path(path).name or not record.get("basename"):
        raise ValueError("invalid source basename")
    for field in (
        "entries",
        "directories",
        "regular_files",
        "symbolic_links",
        "other_entries",
        "apparent_bytes",
        "allocated_bytes",
    ):
        if not isinstance(record.get(field), int) or record[field] < 0:
            raise ValueError(f"invalid source {field}")
    return record


def _error_text(stream: BinaryIO) -> str:
    stream.seek(0)
    return stream.read().decode("utf-8", errors="replace").strip()


def inspect_tar_payload(
    zstd: Path, tar: Path, archive: Path
) -> tuple[int, str]:
    """Hash the decompressed stream while GNU tar parses every member."""
    digest = hashlib.sha256()
    total = 0
    with tempfile.TemporaryFile() as zstd_error, tempfile.TemporaryFile() as tar_error:
        decompressor = subprocess.Popen(
            [str(zstd), "-q", "-f", "-d", "-c", str(archive)],
            stdout=subprocess.PIPE,
            stderr=zstd_error,
        )
        assert decompressor.stdout is not None
        listing = subprocess.Popen(
            [str(tar), "--list", "--file=-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=tar_error,
        )
        assert listing.stdin is not None
        try:
            for block in iter(lambda: decompressor.stdout.read(COPY_BLOCK_BYTES), b""):
                total += len(block)
                digest.update(block)
                listing.stdin.write(block)
            decompressor.stdout.close()
            listing.stdin.close()
            listing_returncode = listing.wait()
            decompressor_returncode = decompressor.wait()
        except BaseException:
            listing.kill()
            decompressor.kill()
            listing.wait()
            decompressor.wait()
            raise
        if decompressor_returncode:
            raise RuntimeError("zstd decompression failed: " + _error_text(zstd_error))
        if listing_returncode:
            raise RuntimeError("tar listing failed: " + _error_text(tar_error))
    return total, digest.hexdigest()


def compare_archive_to_source(
    zstd: Path, tar: Path, archive: Path, source: Path
) -> None:
    """Have GNU tar independently compare archive data and metadata to source."""
    with tempfile.TemporaryFile() as zstd_error, tempfile.TemporaryFile() as tar_output:
        decompressor = subprocess.Popen(
            [str(zstd), "-q", "-f", "-d", "-c", str(archive)],
            stdout=subprocess.PIPE,
            stderr=zstd_error,
        )
        assert decompressor.stdout is not None
        comparison = subprocess.Popen(
            [
                str(tar),
                "--compare",
                "--file=-",
                "--numeric-owner",
                "--acls",
                "--xattrs",
                "--directory",
                str(source.parent),
            ],
            stdin=decompressor.stdout,
            stdout=tar_output,
            stderr=subprocess.STDOUT,
        )
        decompressor.stdout.close()
        comparison_returncode = comparison.wait()
        decompressor_returncode = decompressor.wait()
        if decompressor_returncode:
            raise RuntimeError("zstd decompression failed: " + _error_text(zstd_error))
        if comparison_returncode:
            raise ValueError("archive differs from source: " + _error_text(tar_output))


def audit(
    manifest_path: Path,
    zstd_override: Path | None = None,
    tar_override: Path | None = None,
    require_source: bool = False,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise ValueError(f"missing archive manifest: {manifest_path}")
    document = load_document(manifest_path)
    if document.get("schema") != ARCHIVE_SCHEMA:
        raise ValueError("unexpected archive schema")

    source = validate_source_record(document.get("source"))
    source_path = Path(source["path"])
    archive_path, archive = checked_file(document.get("archive"), "archive")
    _, provenance = checked_file(document.get("provenance"), "provenance")

    payload = document.get("payload")
    if (
        not isinstance(payload, dict)
        or payload.get("format") != "posix-tar"
        or not isinstance(payload.get("bytes"), int)
        or payload["bytes"] < 0
        or not valid_sha256(payload.get("sha256"))
        or payload.get("root") != source["basename"]
    ):
        raise ValueError("invalid tar payload record")

    compression = document.get("compression")
    if (
        not isinstance(compression, dict)
        or compression.get("format") != "zstd"
        or not isinstance(compression.get("level"), int)
        or not isinstance(compression.get("threads"), int)
        or compression["threads"] < 0
    ):
        raise ValueError("invalid compression record")
    zstd, zstd_record, zstd_version = checked_executable(
        compression.get("executable"), zstd_override, "zstd"
    )

    tar_record = document.get("tar")
    if not isinstance(tar_record, dict) or tar_record.get("format") != "gnu-tar":
        raise ValueError("invalid tar record")
    tar, tar_executable, tar_version = checked_executable(
        tar_record.get("executable"), tar_override, "tar"
    )

    verification = document.get("verification")
    if (
        not isinstance(verification, dict)
        or verification.get("zstd_test") is not True
        or verification.get("tar_list") is not True
        or verification.get("source_compare") is not True
        or verification.get("verified") is not True
    ):
        raise ValueError("invalid archive verification record")

    subprocess.run(
        [str(zstd), "-q", "-f", "-t", str(archive_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    payload_bytes, payload_sha256 = inspect_tar_payload(zstd, tar, archive_path)
    if payload_bytes != payload["bytes"] or payload_sha256 != payload["sha256"]:
        raise ValueError("decompressed tar payload mismatch")

    source_present = source_path.exists() or source_path.is_symlink()
    if require_source and not source_present:
        raise ValueError(f"source directory is required: {source_path}")
    source_stats_match = False
    source_compared = False
    if source_present:
        if source_path.is_symlink() or not source_path.is_dir():
            raise ValueError(f"source artifact mismatch: {source_path}")
        current_stats = directory_stats(source_path)
        expected_stats = {field: source[field] for field in current_stats}
        if current_stats != expected_stats:
            raise ValueError(f"source directory statistics mismatch: {source_path}")
        source_stats_match = True
        compare_archive_to_source(zstd, tar, archive_path, source_path)
        source_compared = True

    return {
        "schema": AUDIT_SCHEMA,
        "manifest": file_record(manifest_path),
        "source": source,
        "source_present": source_present,
        "source_stats_match": source_stats_match,
        "source_compared": source_compared,
        "archive": archive,
        "provenance": provenance,
        "payload": {
            "bytes": payload_bytes,
            "sha256": payload_sha256,
            "tar_list": True,
        },
        "zstd": {
            "path": str(zstd),
            "sha256": zstd_record["sha256"],
            "version": zstd_version,
            "test": True,
        },
        "tar": {
            "path": str(tar),
            "sha256": tar_executable["sha256"],
            "version": tar_version,
        },
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--zstd", type=Path)
    parser.add_argument("--tar", type=Path)
    parser.add_argument("--require-source", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            audit(
                arguments.manifest,
                arguments.zstd,
                arguments.tar,
                arguments.require_source,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
