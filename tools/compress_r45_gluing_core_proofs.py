#!/usr/bin/env python3
"""Losslessly compress and independently rehash checked gluing core proofs."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


CORE_SCHEMA = "ramsey55.r45-gluing-core-proofs.v1"
SCHEMA = "ramsey55.r45-gluing-compressed-core-proofs.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_core(root: Path, record: object) -> Path:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise TypeError("missing or malformed core artifact record")
    relative = Path(record["path"])
    if relative.is_absolute() or relative.name != str(relative):
        raise ValueError("core artifact path must be a basename")
    path = root / relative
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or file_sha256(path) != record.get("sha256")
    ):
        raise ValueError(f"core artifact mismatch: {path}")
    return path


def artifact(path: Path) -> dict[str, object]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def decompressed_identity(zstd: Path, path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    process = subprocess.Popen(
        [str(zstd), "-q", "-d", "-c", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    for block in iter(lambda: process.stdout.read(1 << 20), b""):
        digest.update(block)
        total += len(block)
    _, error = process.communicate()
    if process.returncode:
        raise RuntimeError(
            f"zstd decompression failed for {path}: "
            f"{error.decode('utf-8', errors='replace').strip()}"
        )
    return total, digest.hexdigest()


def compress(
    core_manifest_path: Path,
    output_dir: Path,
    zstd: Path,
    level: int,
    jobs: int,
) -> dict[str, object]:
    if not 1 <= level <= 19:
        raise ValueError("compression level must be between 1 and 19")
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    if not zstd.is_file():
        raise ValueError(f"missing zstd executable: {zstd}")

    core_manifest = json.loads(core_manifest_path.read_text(encoding="utf-8"))
    summary = core_manifest.get("summary")
    records = core_manifest.get("results")
    if (
        core_manifest.get("schema") != CORE_SCHEMA
        or not isinstance(summary, dict)
        or summary.get("complete_for_listed_formulas") is not True
        or not isinstance(records, list)
        or not records
        or summary.get("formulas") != len(records)
        or summary.get("verified_unsat") != len(records)
    ):
        raise ValueError("checked core manifest is incomplete")

    core_root = core_manifest_path.parent
    tasks: list[tuple[int, Path]] = []
    pair_indices: set[int] = set()
    for record in records:
        if not isinstance(record, dict) or record.get("status") != "VERIFIED_UNSAT":
            raise ValueError("core result is not VERIFIED_UNSAT")
        pair_index = int(record["pair_index"])
        if pair_index in pair_indices:
            raise ValueError(f"duplicate pair index: {pair_index}")
        pair_indices.add(pair_index)
        tasks.append((pair_index, checked_core(core_root, record.get("core_proof"))))

    version = subprocess.run(
        [str(zstd), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout.strip()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent)
    )
    try:
        def worker(task: tuple[int, Path]) -> dict[str, object]:
            pair_index, core = task
            compressed = temporary / f"{core.name}.zst"
            completed = subprocess.run(
                [
                    str(zstd),
                    f"-{level}",
                    "-T1",
                    "-q",
                    "-o",
                    str(compressed),
                    str(core),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if completed.returncode or not compressed.is_file():
                raise RuntimeError(f"zstd compression failed for pair {pair_index}")
            decompressed_bytes, decompressed_sha256 = decompressed_identity(
                zstd, compressed
            )
            core_bytes = core.stat().st_size
            core_sha256 = file_sha256(core)
            if decompressed_bytes != core_bytes or decompressed_sha256 != core_sha256:
                raise RuntimeError(
                    f"pair {pair_index}: decompressed artifact does not match core"
                )
            result = {
                "pair_index": pair_index,
                **artifact(compressed),
                "core_bytes": core_bytes,
                "core_sha256": core_sha256,
            }
            print(
                f"compressed pair {pair_index}: "
                f"{core_bytes} -> {result['bytes']}",
                flush=True,
            )
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(worker, tasks))

        source_bytes = int(summary["source_proof_bytes"])
        core_bytes = sum(int(result["core_bytes"]) for result in results)
        compressed_bytes = sum(int(result["bytes"]) for result in results)
        if core_bytes != summary.get("core_proof_bytes"):
            raise ValueError("core byte total does not match manifest summary")
        document = {
            "schema": SCHEMA,
            "claim": "losslessly compressed checked core proofs for listed formulas only",
            "core_manifest": {
                "path": str(core_manifest_path),
                "sha256": file_sha256(core_manifest_path),
                "schema": CORE_SCHEMA,
            },
            "compression": {
                "format": "zstd",
                "level": level,
                "threads_per_file": 1,
                "executable": str(zstd),
                "executable_sha256": file_sha256(zstd),
                "version": version,
            },
            "results": results,
            "summary": {
                "formulas": len(results),
                "complete_for_listed_formulas": True,
                "source_proof_bytes": source_bytes,
                "core_bytes": core_bytes,
                "compressed_bytes": compressed_bytes,
                "compressed_to_core_ratio": round(compressed_bytes / core_bytes, 9),
                "compressed_to_source_ratio": round(
                    compressed_bytes / source_bytes, 9
                ),
            },
        }
        manifest = temporary / "manifest.json"
        manifest.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.rename(output_dir)
        return document
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("core_manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--zstd", type=Path, required=True)
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1)
    arguments = parser.parse_args()
    document = compress(
        arguments.core_manifest,
        arguments.output_dir,
        arguments.zstd,
        arguments.level,
        arguments.jobs,
    )
    print(json.dumps(document["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
