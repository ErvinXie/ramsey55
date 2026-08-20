#!/usr/bin/env python3
"""Relocate a hash-linked materialized-proof artifact tree in place."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "ramsey55.materialized-proof-tree-relocation.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def replace_prefix(value: Any, old_root: str, new_root: str) -> tuple[Any, int]:
    if isinstance(value, str):
        replaced = value.replace(old_root, new_root)
        return replaced, replaced != value
    if isinstance(value, list):
        output = []
        changes = 0
        for item in value:
            replacement, count = replace_prefix(item, old_root, new_root)
            output.append(replacement)
            changes += count
        return output, changes
    if isinstance(value, dict):
        output = {}
        changes = 0
        for key, item in value.items():
            replacement, count = replace_prefix(item, old_root, new_root)
            output[key] = replacement
            changes += count
        return output, changes
    return value, 0


def within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def path_for_hash(document: dict[str, Any], hash_key: str) -> str | None:
    if hash_key == "sha256":
        candidate = document.get("path")
        return candidate if isinstance(candidate, str) else None
    if not hash_key.endswith("_sha256"):
        return None
    stem = hash_key[: -len("_sha256")]
    for key in (stem, stem + "_path"):
        candidate = document.get(key)
        if isinstance(candidate, str):
            return candidate
    return None


def update_hash_bindings(value: Any, root: Path) -> int:
    if isinstance(value, list):
        return sum(update_hash_bindings(item, root) for item in value)
    if not isinstance(value, dict):
        return 0
    changes = sum(update_hash_bindings(item, root) for item in value.values())
    for key in list(value):
        target_string = path_for_hash(value, key)
        if target_string is None:
            continue
        target = Path(target_string)
        if not target.is_absolute() or not within(target, root):
            continue
        if not target.is_file():
            raise ValueError(f"hash-bound relocated file does not exist: {target}")
        expected = file_sha256(target)
        if value[key] != expected:
            value[key] = expected
            changes += 1
    return changes


def relocate_tree(old_root: str, root: Path) -> dict[str, Any]:
    root = root.resolve()
    old_root = old_root.rstrip("/")
    new_root = str(root)
    if not old_root or old_root == new_root or not root.is_dir():
        raise ValueError("old and new roots must be distinct existing directories")
    paths = sorted(root.rglob("*.json"))
    path_replacements = 0
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        relocated, changes = replace_prefix(document, old_root, new_root)
        if changes:
            atomic_json(path, relocated)
            path_replacements += changes

    hash_updates = 0
    passes = 0
    for passes in range(1, len(paths) + 2):
        pass_updates = 0
        for path in paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            changes = update_hash_bindings(document, root)
            if changes:
                atomic_json(path, document)
                pass_updates += changes
        hash_updates += pass_updates
        if not pass_updates:
            break
    else:
        raise RuntimeError("relocated hash bindings did not converge")

    remaining = [
        str(path)
        for path in paths
        if old_root in path.read_text(encoding="utf-8")
    ]
    if remaining:
        raise ValueError(f"old root remains in JSON documents: {remaining[:5]}")
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if update_hash_bindings(document, root):
            raise RuntimeError(f"unstable relocated hash binding: {path}")
    return {
        "schema": SCHEMA,
        "old_root": old_root,
        "new_root": new_root,
        "json_documents": len(paths),
        "path_replacements": path_replacements,
        "hash_updates": hash_updates,
        "convergence_passes": passes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_root")
    parser.add_argument("new_root", type=Path)
    parser.add_argument("--manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.manifest is not None and arguments.manifest.exists():
        parser.error(f"refusing to overwrite {arguments.manifest}")
    result = relocate_tree(arguments.old_root, arguments.new_root)
    if arguments.manifest is not None:
        atomic_json(arguments.manifest, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
