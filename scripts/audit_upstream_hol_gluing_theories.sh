#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 8 ]]; then
  echo "usage: $0 UPSTREAM_ROOT PBL THEORY_DIR LABEL BUILD_LOG BUILD_TIME MEMORY_MB OUTPUT_PREFIX" >&2
  exit 2
fi

upstream_root=$1
problem_list=$2
theory_directory=$3
label=$4
build_log=$5
build_time_log=$6
memory_mb=$7
output_prefix=$8
repository_root=$(cd "$(dirname "$0")/.." && pwd -P)

if [[ ! $label =~ ^GLUE[0-9]+$ ]]; then
  echo "LABEL must match GLUE followed by decimal digits" >&2
  exit 2
fi
if [[ ! $memory_mb =~ ^[1-9][0-9]*$ ]]; then
  echo "MEMORY_MB must be a positive integer" >&2
  exit 2
fi
if [[ ! -x $upstream_root/HOL/bin/hol || ! -x $upstream_root/HOL/bin/genscriptdep ]]; then
  echo "missing HOL executables under $upstream_root" >&2
  exit 2
fi
for input_path in "$problem_list" "$build_log" "$build_time_log"; do
  if [[ ! -s $input_path ]]; then
    echo "missing or empty input: $input_path" >&2
    exit 2
  fi
done
if [[ ! -d $theory_directory || ! -s $theory_directory/Holmakefile ]]; then
  echo "missing theory directory or Holmakefile: $theory_directory" >&2
  exit 2
fi

upstream_root=$(cd "$upstream_root" && pwd -P)
problem_list=$(cd "$(dirname "$problem_list")" && pwd -P)/$(basename "$problem_list")
theory_directory=$(cd "$theory_directory" && pwd -P)
build_log=$(cd "$(dirname "$build_log")" && pwd -P)/$(basename "$build_log")
build_time_log=$(cd "$(dirname "$build_time_log")" && pwd -P)/$(basename "$build_time_log")
output_parent=$(cd "$(dirname "$output_prefix")" && pwd -P)
output_prefix=$output_parent/$(basename "$output_prefix")
load_log=$output_prefix-load.log
load_time_log=$output_prefix-load.time.log
audit_json=$output_prefix-audit.json

for output_path in "$load_log" "$load_time_log" "$audit_json"; do
  if [[ -e $output_path ]]; then
    echo "refusing to overwrite: $output_path" >&2
    exit 2
  fi
done

while read -r left right extra; do
  if [[ ! $left =~ ^[1-9][0-9]*$ || ! $right =~ ^[1-9][0-9]*$ || -n ${extra:-} ]]; then
    echo "invalid problem-list row: $left $right ${extra:-}" >&2
    exit 2
  fi
  name=r45_${left}_${right}
  for suffix in Script.sml Theory.sml Theory.sig Theory.dat; do
    if [[ ! -s $theory_directory/$name$suffix ]]; then
      echo "missing core theory artifact: $theory_directory/$name$suffix" >&2
      exit 2
    fi
  done
  ui=$theory_directory/${name}Theory.ui
  uo=$theory_directory/${name}Theory.uo
  if [[ ! -e $ui && ! -e $uo ]]; then
    ui_tmp=$ui.tmp.$$
    uo_tmp=$uo.tmp.$$
    (
      cd "$theory_directory"
      "$upstream_root/HOL/bin/genscriptdep" "${name}Theory.sig" > "$ui_tmp"
      "$upstream_root/HOL/bin/genscriptdep" "${name}Theory.sml" > "$uo_tmp"
    )
    printf '%s\n' \
      "$theory_directory/${name}Theory" \
      "$theory_directory/${name}Theory.sig" >> "$ui_tmp"
    printf '%s\n' \
      "$theory_directory/${name}Theory" \
      "$theory_directory/${name}Theory.sml" >> "$uo_tmp"
    mv "$ui_tmp" "$ui"
    mv "$uo_tmp" "$uo"
  elif [[ ! -s $ui || ! -s $uo ]]; then
    echo "partial dependency pair for $name" >&2
    exit 2
  fi
done < "$problem_list"

(
  cd "$theory_directory"
  /usr/bin/time -v -o "$load_time_log" \
    env RAMSEY55_GLUE_LABEL="$label" RAMSEY55_GLUE_PBL="$problem_list" \
    "$upstream_root/HOL/bin/hol" --q \
    < "$repository_root/scripts/upstream_hol_gluing_load_audit.sml" \
    > "$load_log" 2>&1
)

python3 "$repository_root/tools/audit_upstream_hol_gluing_theories.py" \
  "$problem_list" \
  --theory-directory "$theory_directory" \
  --label "$label" \
  --build-log "$build_log" \
  --build-time-log "$build_time_log" \
  --load-log "$load_log" \
  --load-time-log "$load_time_log" \
  --expected-memory-mb "$memory_mb" \
  --evidence "$upstream_root/src/config" \
  --evidence "$upstream_root/src/dir.sml" \
  --evidence "$upstream_root/HOL/bin/hol" \
  --evidence "$upstream_root/HOL/src/HolSat/sat_solvers/minisat/minisat" \
  --evidence "$repository_root/scripts/run_upstream_hol_gluing_batch.sh" \
  --evidence "$repository_root/scripts/upstream_hol_gluing_batch.sml" \
  --evidence "$repository_root/scripts/audit_upstream_hol_gluing_theories.sh" \
  --evidence "$repository_root/scripts/upstream_hol_gluing_load_audit.sml" \
  --output "$audit_json"
