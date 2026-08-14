#!/usr/bin/env python3
"""Export hash-bound edge-stratum manifest cubes for an assumption solver."""

from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("manifest",type=Path)
    parser.add_argument("degree",type=int); parser.add_argument("output",type=Path)
    args=parser.parse_args(); raw=args.manifest.read_bytes(); doc=json.loads(raw)
    if doc.get("schema") != "ramsey55.order45-edge-strata.v1": raise ValueError("bad schema")
    record=next((r for r in doc["files"] if r["degree"]==args.degree),None)
    if record is None: raise ValueError("degree missing")
    lines=[f"c manifest_sha256 {hashlib.sha256(raw).hexdigest()}",
           f"c cnf_sha256 {record['sha256']}",f"c degree {args.degree}"]
    for index,cube in enumerate(record["cubes"]):
        lines.append(" ".join(map(str,(index,*cube["literals"],0))))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text("\n".join(lines)+"\n",encoding="ascii")
    print(f"exported {len(record['cubes'])} cubes for d{args.degree}")

if __name__ == "__main__": main()
