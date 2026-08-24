#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 REPOSITORY DATA_ROOT DIRECTORY_REL PREFIX BASE_CNF REPLAY_MANIFEST PREFIX_PROOF SOURCE_FRONTIER CONTINUATION_PROOF CONTINUATION_TSV CONTINUATION_LOG" >&2
  exit 2
}

if [[ $# -ne 11 ]]; then
  usage
fi

repository=${1%/}
data_root=${2%/}
directory_rel=$3
prefix=$4
base_cnf=$5
replay=$6
prefix_proof=$7
source_frontier=$8
continuation_proof=$9
continuation_tsv=${10}
continuation_log=${11}
poll_seconds=${RAMSEY55_POLL_SECONDS:-30}
global_lock=${RAMSEY55_FINALIZER_LOCK:-/tmp/ramsey55-residual-finalizer.lock}
checker=${RAMSEY55_DRAT_CHECKER:-$repository/.tools/src/drat-trim/drat-trim}

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
if [[ -z $prefix || $prefix = */* ]]; then
  echo "PREFIX must be a basename" >&2
  exit 2
fi
for input in \
  "$base_cnf" "$replay" "$prefix_proof" "$source_frontier" \
  "$continuation_proof" "$continuation_tsv" "$continuation_log"; do
  if [[ $input != /* ]]; then
    echo "explicit input paths must be absolute: $input" >&2
    exit 2
  fi
done
if [[ $checker != /* ]]; then
  echo "RAMSEY55_DRAT_CHECKER must be an absolute path" >&2
  exit 2
fi

directory=$data_root/$directory_rel
final=$directory/$prefix-final-v1
test -d "$repository"
test -d "$data_root"
test -d "$directory"
test -s "$base_cnf"
test -s "$replay"
test -f "$prefix_proof"
test -s "$source_frontier"
test -x "$checker"

exec 8>"$final.watcher.lock"
if ! flock -n 8; then
  echo "another forest watcher owns $final.watcher.lock" >&2
  exit 3
fi

printf 'RAMSEY55_FOREST_CONTINUATION_WATCHER_V1_START %s %s\n' \
  "$prefix" "$(date -Is)"
while [[ ! -f $continuation_proof || ! -s $continuation_tsv || ! -s $continuation_log ]]; do
  sleep "$poll_seconds" 8>&-
done

selection=$final.selection.json
test ! -e "$selection"
python3 "$repository/tools/select_cadical_dfs_race.py" \
  "$source_frontier" \
  --race "$continuation_proof" "$continuation_tsv" "$continuation_log" \
  --manifest "$selection" \
  > "$final.selection.log" 2>&1

if ! jq -e '
  .schema == "ramsey55.cadical-dfs-race-selection.v3" and
  .chosen_completed == true and
  .races[.chosen_index].completed == true and
  .races[.chosen_index].frontier_count == 0
' "$selection" > /dev/null; then
  sha256sum "$selection" "$final.selection.log"
  printf 'RAMSEY55_FOREST_CONTINUATION_CHECKPOINTED %s %s\n' \
    "$prefix" "$(date -Is)"
  exit 0
fi

for suffix in \
  fragment.drat standalone.drat checker.log manifest.json \
  finalizer.log finalizer.time audit.log audit.time; do
  test ! -e "$final.$suffix"
done

exec 9>"$global_lock"
flock 9
printf 'RAMSEY55_FOREST_CONTINUATION_FINALIZER_START %s %s\n' \
  "$prefix" "$(date -Is)"
/usr/bin/time -v -o "$final.finalizer.time" \
  python3 "$repository/tools/finalize_cadical_dfs_checkpoint.py" \
    "$base_cnf" "$replay" "$prefix_proof" \
    "$final.fragment.drat" "$final.standalone.drat" \
    "$final.checker.log" \
    --forest-continuation "$continuation_proof" "$selection" \
    --checker "$checker" --drop-deletions \
    --manifest "$final.manifest.json" \
    > "$final.finalizer.log" 2>&1

printf 'RAMSEY55_FOREST_CONTINUATION_AUDIT_START %s %s\n' \
  "$prefix" "$(date -Is)"
/usr/bin/time -v -o "$final.audit.time" \
  python3 "$repository/tools/audit_cadical_dfs_checkpoint_finalization.py" \
    "$final.manifest.json" --root "$data_root" --rerun-checker \
    > "$final.audit.log" 2>&1
jq -e '
  .schema == "ramsey55.cadical-dfs-checkpoint-finalization-audit.v1" and
  .verified == true and .children == 1 and .forest_continuations == 1 and
  .replay_independently_verified == true and
  .checker_rerun.verified == true
' "$final.audit.log" > /dev/null

sha256sum "$selection" "$final.manifest.json" "$final.audit.log" \
  "$final.finalizer.time" "$final.audit.time"
printf 'RAMSEY55_FOREST_CONTINUATION_ACCEPTED %s %s\n' \
  "$prefix" "$(date -Is)"
