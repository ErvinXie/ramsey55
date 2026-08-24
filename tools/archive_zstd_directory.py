#!/usr/bin/env python3
"""Create a hash-bound, independently audited zstd directory archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, BinaryIO

from audit_zstd_directory_archive import (
    ARCHIVE_SCHEMA,
    COPY_BLOCK_BYTES,
    audit,
    directory_stats,
    executable_version,
    file_record,
    file_sha256,
)


CREATE_FLAGS = [
    "--numeric-owner",
    "--acls",
    "--xattrs",
    "--sparse",
    "--atime-preserve=system",
]


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


def require_absolute_directory(path: Path, label: str) -> None:
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute: {path}")
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be a directory and not a symlink: {path}")
    if path.resolve(strict=True) != path:
        raise ValueError(f"{label} path has symbolic-link components: {path}")


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite JSON output: {path}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"refusing existing JSON temporary: {temporary}")
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


def _error_text(stream: BinaryIO) -> str:
    stream.seek(0)
    return stream.read().decode("utf-8", errors="replace").strip()


def compress_directory(
    source: Path,
    temporary_archive: Path,
    zstd: Path,
    tar: Path,
    level: int,
    threads: int,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with temporary_archive.open("xb") as output, tempfile.TemporaryFile() as tar_error, tempfile.TemporaryFile() as zstd_error:
        producer = subprocess.Popen(
            [
                str(tar),
                "--create",
                "--file=-",
                *CREATE_FLAGS,
                "--directory",
                str(source.parent),
                "--",
                source.name,
            ],
            stdout=subprocess.PIPE,
            stderr=tar_error,
        )
        assert producer.stdout is not None
        compressor = subprocess.Popen(
            [str(zstd), "-q", f"-{level}", f"-T{threads}", "-c"],
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=zstd_error,
        )
        assert compressor.stdin is not None
        try:
            for block in iter(lambda: producer.stdout.read(COPY_BLOCK_BYTES), b""):
                total += len(block)
                digest.update(block)
                compressor.stdin.write(block)
            producer.stdout.close()
            compressor.stdin.close()
            producer_returncode = producer.wait()
            compressor_returncode = compressor.wait()
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            producer.kill()
            compressor.kill()
            producer.wait()
            compressor.wait()
            raise
        if producer_returncode:
            raise RuntimeError("tar creation failed: " + _error_text(tar_error))
        if compressor_returncode:
            raise RuntimeError("zstd compression failed: " + _error_text(zstd_error))
    return total, digest.hexdigest()


def create_archive(
    source: Path,
    provenance: Path,
    archive: Path,
    manifest: Path,
    audit_path: Path,
    zstd: Path,
    tar: Path,
    level: int = 1,
    threads: int = 0,
) -> dict[str, Any]:
    require_absolute_directory(source, "source")
    require_absolute_regular(provenance, "provenance")
    require_absolute_regular(zstd, "zstd executable")
    require_absolute_regular(tar, "tar executable")
    if "GNU tar" not in executable_version(tar):
        raise ValueError("directory archives require GNU tar")
    if not 1 <= level <= 19:
        raise ValueError("compression level must be in [1,19]")
    if not 0 <= threads <= 256:
        raise ValueError("compression threads must be in [0,256]")

    for path, label in (
        (archive, "archive"),
        (manifest, "manifest"),
        (audit_path, "audit"),
    ):
        if not path.is_absolute():
            raise ValueError(f"{label} path must be absolute: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"{label} parent does not exist: {path.parent}")
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"refusing to overwrite {label}: {path}")
        try:
            path.resolve().relative_to(source)
        except ValueError:
            pass
        else:
            raise ValueError(f"{label} must be outside source: {path}")

    temporary_archive = archive.with_name(archive.name + ".tmp")
    if temporary_archive.exists() or temporary_archive.is_symlink():
        raise FileExistsError(f"refusing existing archive temporary: {temporary_archive}")

    source_stats = directory_stats(source)
    zstd_version = executable_version(zstd)
    tar_version = executable_version(tar)
    archive_published = False
    manifest_published = False
    try:
        payload_bytes, payload_sha256 = compress_directory(
            source, temporary_archive, zstd, tar, level, threads
        )
        subprocess.run(
            [str(zstd), "-q", "-f", "-t", str(temporary_archive)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        archive_record = file_record(temporary_archive)
        archive_record["path"] = str(archive)
        os.replace(temporary_archive, archive)
        archive_published = True
        fsync_directory(archive.parent)

        document: dict[str, Any] = {
            "schema": ARCHIVE_SCHEMA,
            "source": {
                "path": str(source),
                "basename": source.name,
                **source_stats,
            },
            "archive": archive_record,
            "provenance": file_record(provenance),
            "payload": {
                "format": "posix-tar",
                "root": source.name,
                "bytes": payload_bytes,
                "sha256": payload_sha256,
            },
            "compression": {
                "format": "zstd",
                "level": level,
                "threads": threads,
                "executable": {
                    "path": str(zstd),
                    "sha256": file_sha256(zstd),
                    "version": zstd_version,
                },
            },
            "tar": {
                "format": "gnu-tar",
                "create_flags": CREATE_FLAGS,
                "executable": {
                    "path": str(tar),
                    "sha256": file_sha256(tar),
                    "version": tar_version,
                },
            },
            "verification": {
                "zstd_test": True,
                "tar_list": True,
                "source_compare": True,
                "verified": True,
            },
        }
        write_json_atomic(manifest, document)
        manifest_published = True
        audited = audit(manifest, zstd, tar, require_source=True)
        if not audited.get("verified") or not audited.get("source_compared"):
            raise ValueError("independent directory archive audit did not verify")
        write_json_atomic(audit_path, audited)
        return {"manifest": document, "audit": audited}
    except BaseException:
        if temporary_archive.exists():
            temporary_archive.unlink()
        if audit_path.exists():
            audit_path.unlink()
        if manifest_published and manifest.exists():
            manifest.unlink()
        if archive_published and archive.exists():
            archive.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("provenance", type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--zstd", type=Path, default=Path("/usr/bin/zstd"))
    parser.add_argument("--tar", type=Path, default=Path("/usr/bin/tar"))
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--threads", type=int, default=0)
    arguments = parser.parse_args()
    print(
        json.dumps(
            create_archive(
                arguments.source,
                arguments.provenance,
                arguments.archive,
                arguments.manifest,
                arguments.audit,
                arguments.zstd,
                arguments.tar,
                arguments.level,
                arguments.threads,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
