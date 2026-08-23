#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

usage() {
  echo "usage: $0 REPOSITORY DATA_ROOT DIRECTORY_REL PREFIX ROOT_COUNT" >&2
  exit 2
}

if [[ $# -ne 5 ]]; then
  usage
fi

repository=$1
data_root=$2
directory_rel=$3
prefix=$4
root_count=$5
poll_seconds=${RAMSEY55_POLL_SECONDS:-30}

if [[ ! $root_count =~ ^[1-9][0-9]*$ ]]; then
  echo "ROOT_COUNT must be positive" >&2
  exit 2
fi
if [[ ! $poll_seconds =~ ^[1-9][0-9]*$ ]]; then
  echo "RAMSEY55_POLL_SECONDS must be positive" >&2
  exit 2
fi
if [[ $directory_rel = /* || $directory_rel = *//* ]]; then
  echo "DIRECTORY_REL must be a normalized relative path" >&2
  exit 2
fi
IFS=/ read -r -a directory_parts <<< "$directory_rel"
for part in "${directory_parts[@]}"; do
  if [[ -z $part || $part = . || $part = .. ]]; then
    echo "DIRECTORY_REL must be a normalized relative path" >&2
    exit 2
  fi
done
if [[ -z $prefix || $prefix = */* || $prefix != *-checkpoint1 ]]; then
  echo "PREFIX must be a checkpoint1 basename" >&2
  exit 2
fi

repository=${repository%/}
data_root=${data_root%/}
directory=$data_root/$directory_rel
base_cnf=$repository/build/order45-fixed-pairs/h0-j326185-nosym.cnf
checker=$repository/.tools/src/drat-trim/drat-trim
prefix_proof=$directory/${prefix%-checkpoint1}.drat
frontier=$directory/$prefix-frontier.json
final=$directory/$prefix-final-v1

test -d "$repository"
test -d "$data_root"
test -d "$directory"
test -s "$base_cnf"
test -x "$checker"
test -s "$prefix_proof"
test -s "$frontier"

exec 8>"$final.watcher.lock"
if ! flock -n 8; then
  echo "another finalizer watcher owns $final.watcher.lock" >&2
  exit 3
fi

cd "$data_root"
printf 'RAMSEY55_PREFIX_WATCHER_V2_START %s %s %s\n' \
  "$prefix" "$root_count" "$(date -Is)"

selections=()
chosen_proofs=()
chosen_logs=()
for ((index=0; index<root_count; index++)); do
  root=$(printf '%s-root%03d' "$prefix" "$index")
  selection=$directory/$root-race-selection-v1.json
  if [[ ! -e $selection ]]; then
    while :; do
      producer_logs=(
        "$directory/$root-seed"*.log
        "$directory/$root-longsolve"*.log
      )
      completed=()
      for producer_log in "${producer_logs[@]}"; do
        if grep -q $'^status\t20$' "$producer_log"; then
          completed+=("$producer_log")
        fi
      done
      if [[ ${#completed[@]} -gt 0 ]]; then
        break
      fi
      sleep "$poll_seconds"
    done

    selection_stem=${selection%.json}
    test ! -e "$selection_stem.log"
    test ! -e "$selection_stem.time"
    race_arguments=()
    for producer_log in "${completed[@]}"; do
      producer_stem=${producer_log%.log}
      test -s "$producer_stem.drat"
      test -s "$producer_stem.tsv"
      race_arguments+=(
        --race "$producer_stem.drat" "$producer_stem.tsv" "$producer_log"
      )
    done
    /usr/bin/time -v -o "$selection_stem.time" \
      python3 "$repository/tools/select_cadical_dfs_race.py" \
        "$directory/$root.icnf" "${race_arguments[@]}" \
        --manifest "$selection" > "$selection_stem.log" 2>&1
  fi

  jq -e '.schema == "ramsey55.cadical-dfs-race-selection.v3" and
         .chosen_completed == true and .root_count == 1' \
    "$selection" > /dev/null
  selections+=("$selection")
  proof=$(jq -r '.races[.chosen_index].proof.path' "$selection")
  producer=$(jq -r '.races[.chosen_index].producer_log.path' "$selection")
  [[ $proof = /* ]] || proof=$data_root/$proof
  [[ $producer = /* ]] || producer=$data_root/$producer
  test -s "$proof"
  test -s "$producer"
  chosen_proofs+=("$proof")
  chosen_logs+=("$producer")
done

for suffix in \
  fragment.drat standalone.drat checker.log manifest.json \
  finalizer.log finalizer.time audit.log audit.time; do
  test ! -e "$final.$suffix"
done

exec 9>/tmp/ramsey55-residual-finalizer.lock
flock 9
printf 'RAMSEY55_PREFIX_FINALIZER_START %s %s\n' \
  "$prefix" "$(date -Is)"
children=()
for ((index=0; index<root_count; index++)); do
  children+=(--child "${chosen_proofs[index]}" "${chosen_logs[index]}")
done
/usr/bin/time -v -o "$final.finalizer.time" \
  python3 "$repository/tools/finalize_cadical_dfs_checkpoint.py" \
    "$base_cnf" "$frontier" "$prefix_proof" \
    "$final.fragment.drat" "$final.standalone.drat" \
    "$final.checker.log" "${children[@]}" \
    --checker "$checker" --drop-deletions \
    --manifest "$final.manifest.json" \
    > "$final.finalizer.log" 2>&1

printf 'RAMSEY55_PREFIX_AUDIT_START %s %s\n' \
  "$prefix" "$(date -Is)"
/usr/bin/time -v -o "$final.audit.time" \
  python3 "$repository/tools/audit_cadical_dfs_checkpoint_finalization.py" \
    "$final.manifest.json" --root "$data_root" --rerun-checker \
    > "$final.audit.log" 2>&1
jq -e --argjson roots "$root_count" \
  '.schema == "ramsey55.cadical-dfs-checkpoint-finalization-audit.v1" and
   .verified == true and .children == $roots and
   .checker_rerun.verified == true' \
  "$final.audit.log" > /dev/null

sha256sum "${selections[@]}" "$final.manifest.json" "$final.audit.log" \
  "$final.finalizer.time" "$final.audit.time"
printf 'RAMSEY55_PREFIX_ACCEPTED %s %s\n' \
  "$prefix" "$(date -Is)"
