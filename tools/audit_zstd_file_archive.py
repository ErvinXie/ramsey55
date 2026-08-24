#!/usr/bin/env python3
"""Independently audit and optionally restore one zstd file archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, BinaryIO


ARCHIVE_SCHEMA = "ramsey55.zstd-file-archive.v1"
AUDIT_SCHEMA = "ramsey55.zstd-file-archive-audit.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 23), b""):
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


def validate_record(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"missing or malformed {label} record")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise ValueError(f"invalid {label} path")
    if not isinstance(record.get("bytes"), int) or record["bytes"] < 0:
        raise ValueError(f"invalid {label} byte count")
    if not valid_sha256(record.get("sha256")):
        raise ValueError(f"invalid {label} SHA-256")
    return record


def checked_artifact(record: object, label: str) -> tuple[Path, dict[str, Any]]:
    checked = validate_record(record, label)
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


def decompress_identity(
    zstd: Path, compressed: Path, output: BinaryIO | None = None
) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    process = subprocess.Popen(
        [str(zstd), "-q", "-f", "-d", "-c", str(compressed)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    try:
        for block in iter(lambda: process.stdout.read(1 << 23), b""):
            total += len(block)
            digest.update(block)
            if output is not None:
                output.write(block)
        _, error = process.communicate()
    except BaseException:
        process.kill()
        process.wait()
        raise
    if process.returncode:
        raise RuntimeError(
            "zstd decompression failed: "
            + error.decode("utf-8", errors="replace").strip()
        )
    return total, digest.hexdigest()


def audit(
    manifest_path: Path,
    zstd_override: Path | None = None,
    restore: bool = False,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise ValueError(f"missing archive manifest: {manifest_path}")
    document = load_document(manifest_path)
    if document.get("schema") != ARCHIVE_SCHEMA:
        raise ValueError("unexpected archive schema")

    source = validate_record(document.get("source"), "source")
    source_path = Path(source["path"])
    compressed_path, compressed = checked_artifact(
        document.get("compressed"), "compressed"
    )
    if source_path.is_symlink() and not source_path.exists():
        raise ValueError(f"source artifact mismatch: {source_path}")
    source_present = source_path.exists()
    if source_present:
        if not source_path.is_file() or source_path.stat().st_size != source["bytes"]:
            raise ValueError(f"source artifact mismatch: {source_path}")
        if file_sha256(source_path) != source["sha256"]:
            raise ValueError(f"source artifact mismatch: {source_path}")
    if restore and source_present:
        raise FileExistsError(f"refusing to overwrite source: {source_path}")
    if not source_path.parent.is_dir():
        raise ValueError(f"source parent does not exist: {source_path.parent}")

    provenance_labels = [
        label
        for label in ("recovery_manifest", "race_selection", "provenance")
        if label in document
    ]
    if len(provenance_labels) != 1:
        raise ValueError("archive must contain exactly one provenance record")
    provenance_label = provenance_labels[0]
    provenance_path, provenance = checked_artifact(
        document[provenance_label], provenance_label.replace("_", " ")
    )

    compression = document.get("compression")
    if not isinstance(compression, dict) or compression.get("format") != "zstd":
        raise ValueError("invalid compression record")
    if not isinstance(compression.get("level"), int):
        raise ValueError("invalid compression level")
    executable = compression.get("executable")
    if (
        not isinstance(executable, dict)
        or not isinstance(executable.get("path"), str)
        or not executable["path"]
        or not valid_sha256(executable.get("sha256"))
        or not isinstance(executable.get("version"), str)
        or not executable["version"]
    ):
        raise ValueError("invalid zstd executable record")
    zstd = zstd_override or Path(executable["path"])
    if not zstd.is_file() or not os.access(zstd, os.X_OK):
        raise ValueError(f"missing zstd executable: {zstd}")
    if file_sha256(zstd) != executable["sha256"]:
        raise ValueError("zstd executable hash mismatch")
    version = subprocess.run(
        [str(zstd), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout.strip()
    if version != executable.get("version"):
        raise ValueError("zstd version mismatch")

    verification = document.get("verification")
    if (
        not isinstance(verification, dict)
        or verification.get("verified") is not True
        or verification.get("zstd_test") is not True
        or verification.get("decompressed_bytes") != source["bytes"]
        or verification.get("decompressed_sha256") != source["sha256"]
    ):
        raise ValueError("invalid archive verification record")
    subprocess.run(
        [str(zstd), "-q", "-f", "-t", str(compressed_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    temporary = source_path.with_name(source_path.name + ".restore.tmp")
    if restore and temporary.exists():
        raise FileExistsError(f"refusing existing restore temporary: {temporary}")
    restored = False
    try:
        if restore:
            with temporary.open("xb") as output:
                decompressed_bytes, decompressed_sha256 = decompress_identity(
                    zstd, compressed_path, output
                )
                output.flush()
                os.fsync(output.fileno())
        else:
            decompressed_bytes, decompressed_sha256 = decompress_identity(
                zstd, compressed_path
            )
        if (
            decompressed_bytes != source["bytes"]
            or decompressed_sha256 != source["sha256"]
        ):
            raise ValueError("decompressed stream does not match source record")
        if restore:
            os.replace(temporary, source_path)
            restored = True
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "schema": AUDIT_SCHEMA,
        "manifest": file_record(manifest_path),
        "source": source,
        "source_present_before": source_present,
        "compressed": compressed,
        "provenance": {
            "kind": provenance_label,
            **file_record(provenance_path),
        },
        "zstd": {
            "path": str(zstd),
            "sha256": executable["sha256"],
            "version": version,
        },
        "decompressed_bytes": decompressed_bytes,
        "decompressed_sha256": decompressed_sha256,
        "restored": restored,
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--zstd", type=Path)
    parser.add_argument("--restore", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            audit(arguments.manifest, arguments.zstd, arguments.restore),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
