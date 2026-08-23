#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 REPOSITORY DATA_ROOT DIRECTORY_REL PREFIX BASE_CNF REPLAY_MANIFEST PREFIX_PROOF CHOICE_INDEX FIXED_CHILD_COUNT [FIXED_PROOF FIXED_EVIDENCE ...] CANDIDATE_PROOF CANDIDATE_MANIFEST [CANDIDATE_PROOF CANDIDATE_MANIFEST ...]" >&2
  exit 2
}

if [[ $# -lt 11 ]]; then
  usage
fi

repository=$1
data_root=$2
directory_rel=$3
prefix=$4
base_cnf=$5
replay=$6
prefix_proof=$7
choice_index=$8
fixed_count=$9
shift 9
poll_seconds=${RAMSEY55_POLL_SECONDS:-30}

if [[ ! $choice_index =~ ^[0-9]+$ || ! $fixed_count =~ ^[0-9]+$ ]]; then
  usage
fi
if (( choice_index > fixed_count )); then
  echo "CHOICE_INDEX must be between zero and FIXED_CHILD_COUNT" >&2
  exit 2
fi
if (( $# < fixed_count * 2 + 2 || ($# - fixed_count * 2) % 2 != 0 )); then
  usage
fi
if [[ ! $poll_seconds =~ ^[1-9][0-9]*$ ]]; then
  echo "RAMSEY55_POLL_SECONDS must be positive" >&2
  exit 2
fi

repository=${repository%/}
data_root=${data_root%/}
directory=$data_root/$directory_rel
selector=$repository/tools/select_finalized_drat_child.py
recursive=$repository/scripts/watch_recursive_cadical_dfs_checkpoint_finalization.sh
selection=$directory/$prefix-choice-v1.json

test -d "$repository"
test -d "$data_root"
test -d "$directory"
test -x "$selector"
test -x "$recursive"
test "$(jq -r '.output_count' "$replay")" -eq "$((fixed_count + 1))"

exec 8>"$selection.watcher.lock"
if ! flock -n 8; then
  echo "another choice watcher owns $selection.watcher.lock" >&2
  exit 3
fi

fixed=()
for ((index=0; index<fixed_count; index++)); do
  fixed+=("$1" "$2")
  shift 2
done
candidates=("$@")

for input in "$base_cnf" "$replay" "$prefix_proof" "${fixed[@]}" "${candidates[@]}"; do
  if [[ $input != /* ]]; then
    echo "explicit input paths must be absolute: $input" >&2
    exit 2
  fi
done

selector_arguments=()
while [[ $# -gt 0 ]]; do
  selector_arguments+=(--candidate "$1" "$2")
  shift 2
done

printf 'RAMSEY55_RECURSIVE_CHOICE_WATCHER_V1_START %s %s %s\n' \
  "$prefix" "${#selector_arguments[@]}" "$(date -Is)"
while :; do
  set +e
  python3 "$selector" "${selector_arguments[@]}" --output "$selection" \
    > "$selection.stdout.tmp" 2> "$selection.stderr.tmp"
  status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    rm -f "$selection.stdout.tmp" "$selection.stderr.tmp"
    break
  fi
  if [[ $status -ne 4 ]]; then
    cat "$selection.stderr.tmp" >&2
    exit "$status"
  fi
  rm -f "$selection.stdout.tmp" "$selection.stderr.tmp"
  sleep "$poll_seconds"
done

choice_proof=$(jq -er '.selected.proof.path' "$selection")
choice_evidence=$(jq -er '.selected.evidence.path' "$selection")
children=()
fixed_index=0
for ((index=0; index<fixed_count + 1; index++)); do
  if (( index == choice_index )); then
    children+=("$choice_proof" "$choice_evidence")
  else
    children+=("${fixed[fixed_index * 2]}" "${fixed[fixed_index * 2 + 1]}")
    fixed_index=$((fixed_index + 1))
  fi
done

printf 'RAMSEY55_RECURSIVE_CHOICE_SELECTED %s %s %s\n' \
  "$prefix" "$(jq -r '.selected_index' "$selection")" "$(date -Is)"
exec bash "$recursive" \
  "$repository" "$data_root" "$directory_rel" "$prefix" \
  "$base_cnf" "$replay" "$prefix_proof" "${children[@]}"
