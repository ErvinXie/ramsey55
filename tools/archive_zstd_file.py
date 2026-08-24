#!/usr/bin/env python3
"""Create a hash-bound, independently auditable zstd file archive."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from audit_zstd_file_archive import (
    ARCHIVE_SCHEMA,
    audit,
    decompress_identity,
    file_record,
    file_sha256,
)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_absolute_regular(path: Path, label: str) -> None:
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute: {path}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite manifest: {path}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"refusing existing manifest temporary: {temporary}")
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_archive(
    source: Path,
    provenance: Path,
    compressed: Path,
    manifest: Path,
    zstd: Path,
    level: int = 1,
) -> dict[str, Any]:
    require_absolute_regular(source, "source")
    require_absolute_regular(provenance, "provenance")
    require_absolute_regular(zstd, "zstd executable")
    for path, label in ((compressed, "compressed"), (manifest, "manifest")):
        if not path.is_absolute():
            raise ValueError(f"{label} path must be absolute: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"{label} parent does not exist: {path.parent}")
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"refusing to overwrite {label}: {path}")
    if not 1 <= level <= 19:
        raise ValueError("compression level must be in [1,19]")

    compressed_temporary = compressed.with_name(compressed.name + ".tmp")
    if compressed_temporary.exists() or compressed_temporary.is_symlink():
        raise FileExistsError(
            f"refusing existing compressed temporary: {compressed_temporary}"
        )

    source_record = file_record(source)
    provenance_record = file_record(provenance)
    zstd_sha256 = file_sha256(zstd)
    zstd_version = subprocess.run(
        [str(zstd), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout.strip()

    try:
        with compressed_temporary.open("xb") as output:
            completed = subprocess.run(
                [str(zstd), "-q", f"-{level}", "-T0", "-c", str(source)],
                stdout=output,
                stderr=subprocess.PIPE,
            )
            output.flush()
            os.fsync(output.fileno())
        if completed.returncode:
            raise RuntimeError(
                "zstd compression failed: "
                + completed.stderr.decode("utf-8", errors="replace").strip()
            )
        subprocess.run(
            [str(zstd), "-q", "-f", "-t", str(compressed_temporary)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        decompressed_bytes, decompressed_sha256 = decompress_identity(
            zstd, compressed_temporary
        )
        if (
            decompressed_bytes != source_record["bytes"]
            or decompressed_sha256 != source_record["sha256"]
        ):
            raise ValueError("compressed stream does not reproduce source")

        compressed_record = file_record(compressed_temporary)
        compressed_record["path"] = str(compressed)
        os.replace(compressed_temporary, compressed)
        fsync_directory(compressed.parent)

        document: dict[str, Any] = {
            "schema": ARCHIVE_SCHEMA,
            "source": source_record,
            "compressed": compressed_record,
            "provenance": provenance_record,
            "compression": {
                "format": "zstd",
                "level": level,
                "executable": {
                    "path": str(zstd),
                    "sha256": zstd_sha256,
                    "version": zstd_version,
                },
            },
            "verification": {
                "zstd_test": True,
                "decompressed_bytes": decompressed_bytes,
                "decompressed_sha256": decompressed_sha256,
                "verified": True,
            },
        }
        write_json_atomic(manifest, document)
        result = audit(manifest, zstd)
        if result.get("verified") is not True:
            raise ValueError("independent archive audit did not verify")
        return document
    except BaseException:
        if compressed_temporary.exists():
            compressed_temporary.unlink()
        if compressed.exists() and not manifest.exists():
            compressed.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--compressed", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--zstd", type=Path, default=Path("/usr/bin/zstd"))
    parser.add_argument("--level", type=int, default=1)
    arguments = parser.parse_args()
    compressed = arguments.compressed or Path(str(arguments.source) + ".zst")
    manifest = arguments.manifest or Path(str(compressed) + ".archive.json")
    document = create_archive(
        arguments.source,
        arguments.provenance,
        compressed,
        manifest,
        arguments.zstd,
        arguments.level,
    )
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
