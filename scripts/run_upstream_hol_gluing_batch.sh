#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 6 ]]; then
  echo "usage: $0 UPSTREAM_ROOT PBL THEORY_DIR LABEL EXPECTED_COUNT OUTPUT_PREFIX" >&2
  exit 2
fi

upstream_root=$1
problem_list=$2
theory_directory=$3
label=$4
expected_count=$5
output_prefix=$6
repository_root=$(cd "$(dirname "$0")/.." && pwd -P)

if [[ ! $label =~ ^GLUE[0-9]+$ ]]; then
  echo "LABEL must match GLUE followed by decimal digits" >&2
  exit 2
fi
if [[ ! $expected_count =~ ^[1-9][0-9]*$ ]]; then
  echo "EXPECTED_COUNT must be a positive integer" >&2
  exit 2
fi
if [[ ! -x $upstream_root/HOL/bin/hol ]]; then
  echo "missing HOL executable under $upstream_root" >&2
  exit 2
fi
if [[ ! -s $problem_list ]]; then
  echo "missing or empty problem list: $problem_list" >&2
  exit 2
fi
if [[ -e $theory_directory ]]; then
  echo "refusing to reuse theory directory: $theory_directory" >&2
  exit 2
fi

upstream_root=$(cd "$upstream_root" && pwd -P)
problem_list=$(cd "$(dirname "$problem_list")" && pwd -P)/$(basename "$problem_list")
theory_parent=$(cd "$(dirname "$theory_directory")" && pwd -P)
theory_directory=$theory_parent/$(basename "$theory_directory")
output_parent=$(cd "$(dirname "$output_prefix")" && pwd -P)
output_prefix=$output_parent/$(basename "$output_prefix")
build_log=$output_prefix-build.log
build_time_log=$output_prefix-build.time.log
temporary_directory=$output_prefix-tmp

for output_path in "$build_log" "$build_time_log" "$temporary_directory"; do
  if [[ -e $output_path ]]; then
    echo "refusing to overwrite: $output_path" >&2
    exit 2
  fi
done
mkdir "$temporary_directory"

cd "$upstream_root/src"
TMPDIR="$temporary_directory" \
/usr/bin/time -v -o "$build_time_log" \
  env RAMSEY55_GLUE_LABEL="$label" \
      RAMSEY55_GLUE_PBL="$problem_list" \
      RAMSEY55_GLUE_THEORY_DIR="$theory_directory" \
      RAMSEY55_GLUE_EXPECTED_COUNT="$expected_count" \
  "$upstream_root/HOL/bin/hol" --q \
  < "$repository_root/scripts/upstream_hol_gluing_batch.sml" \
  > "$build_log" 2>&1

final_marker=RAMSEY55_${label}_KERNEL_FULL_${expected_count}_OK
marker_count=$(grep -F -c "$final_marker" "$build_log" || true)
if [[ $marker_count -ne 1 ]]; then
  echo "HOL run did not emit exactly one final marker: $final_marker" >&2
  exit 1
fi
