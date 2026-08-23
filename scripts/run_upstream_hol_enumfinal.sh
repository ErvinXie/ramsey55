#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 UPSTREAM_ROOT ENUMERATION_AUDIT_MANIFEST MEMORY_MB OUTPUT_PREFIX" >&2
  exit 2
fi

upstream_root=$1
enumeration_audit=$2
memory_mb=$3
output_prefix=$4
repository_root=$(cd "$(dirname "$0")/.." && pwd -P)
final_directory=$upstream_root/src/enumf

if [[ ! $memory_mb =~ ^[1-9][0-9]*$ ]]; then
  echo "MEMORY_MB must be a positive integer" >&2
  exit 2
fi
if [[ ! -x $upstream_root/HOL/bin/Holmake || ! -x $upstream_root/HOL/bin/hol ]]; then
  echo "missing HOL executables under $upstream_root" >&2
  exit 2
fi
for input_path in "$enumeration_audit" "$upstream_root/src/config" \
                  "$final_directory/Holmakefile" \
                  "$final_directory/open_template" \
                  "$final_directory/ramseyEnumScript_template" \
                  "$final_directory/ramseyEnumScript.sml"; do
  if [[ ! -s $input_path ]]; then
    echo "missing or empty input: $input_path" >&2
    exit 2
  fi
done

upstream_root=$(cd "$upstream_root" && pwd -P)
enumeration_audit=$(cd "$(dirname "$enumeration_audit")" && pwd -P)/$(basename "$enumeration_audit")
final_directory=$upstream_root/src/enumf
output_parent=$(cd "$(dirname "$output_prefix")" && pwd -P)
output_prefix=$output_parent/$(basename "$output_prefix")
build_log=$output_prefix-build.log
build_time_log=$output_prefix-build.time.log
load_log=$output_prefix-load.log
load_time_log=$output_prefix-load.time.log
audit_json=$output_prefix-audit.json

for output_path in "$build_log" "$build_time_log" "$load_log" \
                   "$load_time_log" "$audit_json"; do
  if [[ -e $output_path ]]; then
    echo "refusing to overwrite: $output_path" >&2
    exit 2
  fi
done
for suffix in Theory.sml Theory.sig Theory.dat Theory.ui Theory.uo; do
  if [[ -e $final_directory/ramseyEnum$suffix ]]; then
    echo "refusing to reuse final theory artifact: $final_directory/ramseyEnum$suffix" >&2
    exit 2
  fi
done

python3 - "$enumeration_audit" "$upstream_root/src/enump" \
          "$final_directory/open_template" "$memory_mb" \
          "$upstream_root/src/config" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_directory = str(Path(sys.argv[2]).resolve())
if manifest.get("schema") != "ramsey55.upstream-hol-enumeration-artifacts.v1":
    raise SystemExit("unexpected enumeration audit schema")
summary = manifest.get("summary", {})
if (
    manifest.get("directory") != expected_directory
    or summary.get("complete") is not True
    or summary.get("scripts") != 1239
    or summary.get("complete_five_artifact_theories") != 1239
):
    raise SystemExit("enumeration audit does not certify all 1,239 theories")
expected = {record["theory"] + "Theory" for record in manifest["records"]}
words = Path(sys.argv[3]).read_text(encoding="utf-8").split()
if not words or words[0] != "open" or len(words[1:]) != len(set(words[1:])):
    raise SystemExit("invalid enumf open_template")
if set(words[1:]) != expected:
    raise SystemExit("enumf open_template does not match the enumeration audit")
requested_memory = int(sys.argv[4])
settings = {}
for line in Path(sys.argv[5]).read_text(encoding="utf-8").splitlines():
    fields = line.split()
    if len(fields) == 2:
        if fields[0] in settings:
            raise SystemExit(f"duplicate config key: {fields[0]}")
        settings[fields[0]] = fields[1]
if settings.get("memory") != str(requested_memory):
    raise SystemExit("upstream config memory does not match MEMORY_MB")
PY

(
  cd "$final_directory"
  printf 'RAMSEY55_ENUMF_MEMORY_MB %s\n' "$memory_mb" > "$build_log"
  /usr/bin/time -v -o "$build_time_log" \
    "$upstream_root/HOL/bin/Holmake" --no_prereqs -j 1 \
    >> "$build_log" 2>&1
)

(
  cd "$upstream_root/src"
  printf 'RAMSEY55_ENUMF_LOAD_MEMORY_MB %s\n' "$memory_mb" > "$load_log"
  /usr/bin/time -v -o "$load_time_log" \
    "$upstream_root/HOL/bin/hol" --maxheap="$memory_mb" --q \
    < "$repository_root/scripts/upstream_hol_enumfinal_load_audit.sml" \
    >> "$load_log" 2>&1
)

python3 "$repository_root/tools/audit_upstream_hol_enumfinal.py" \
  "$enumeration_audit" \
  --upstream-root "$upstream_root" \
  --build-log "$build_log" \
  --build-time-log "$build_time_log" \
  --load-log "$load_log" \
  --load-time-log "$load_time_log" \
  --expected-memory-mb "$memory_mb" \
  --evidence "$upstream_root/src/config" \
  --evidence "$upstream_root/src/dir.sml" \
  --evidence "$upstream_root/HOL/bin/Holmake" \
  --evidence "$upstream_root/HOL/bin/hol" \
  --evidence "$upstream_root/HOL/src/HolSat/sat_solvers/minisat/minisat" \
  --evidence "$repository_root/scripts/generate_upstream_hol_enumfinal.sh" \
  --evidence "$repository_root/scripts/run_upstream_hol_enumfinal.sh" \
  --evidence "$repository_root/scripts/upstream_hol_enumfinal_load_audit.sml" \
  --evidence "$repository_root/tools/audit_upstream_hol_enumfinal.py" \
  --output "$audit_json"
