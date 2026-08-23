#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 UPSTREAM_ROOT ENUMERATION_AUDIT_MANIFEST" >&2
  exit 2
fi

upstream_root=$1
audit_manifest=$2
enum_directory=$upstream_root/src/enump
final_directory=$upstream_root/src/enumf
final_script=$final_directory/ramseyEnumScript.sml
open_template=$final_directory/open_template

if [[ ! -x $upstream_root/HOL/bin/hol ]]; then
  echo "missing HOL executable under $upstream_root" >&2
  exit 2
fi
if [[ ! -f $audit_manifest ]]; then
  echo "missing enumeration audit manifest: $audit_manifest" >&2
  exit 2
fi
if [[ -e $final_script || -e $open_template ]]; then
  echo "refusing to overwrite an existing enumf generated file" >&2
  exit 2
fi

python3 - "$audit_manifest" "$enum_directory" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_directory = str(Path(sys.argv[2]).resolve())
if manifest.get("schema") != "ramsey55.upstream-hol-enumeration-artifacts.v1":
    raise SystemExit("unexpected enumeration audit schema")
if manifest.get("directory") != expected_directory:
    raise SystemExit("enumeration audit directory mismatch")
summary = manifest.get("summary", {})
if (
    summary.get("complete") is not True
    or summary.get("scripts") != 1239
    or summary.get("complete_five_artifact_theories") != 1239
):
    raise SystemExit("enumeration audit does not certify all 1,239 theories")
PY

cd "$upstream_root/src"
printf '%s\n' \
  'load "enump"; open enump;' \
  'write_enumfinalscript ();' |
  ../HOL/bin/hol --maxheap=50000

if [[ ! -s $open_template || ! -s $final_script ]]; then
  echo "HOL did not create both expected enumf files" >&2
  exit 1
fi

python3 - "$audit_manifest" "$open_template" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {record["theory"] + "Theory" for record in manifest["records"]}
words = Path(sys.argv[2]).read_text(encoding="utf-8").split()
if not words or words[0] != "open":
    raise SystemExit("enumf open_template does not start with 'open'")
observed = set(words[1:])
if len(words[1:]) != len(observed):
    raise SystemExit("enumf open_template contains duplicate theories")
if observed != expected:
    raise SystemExit("enumf open_template theory set does not match audit")
print(f"generated enumf script with {len(observed)} audited theory imports")
PY
