#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 REPOSITORY DATA_ROOT DIRECTORY_REL PREFIX BASE_CNF REPLAY_MANIFEST PREFIX_PROOF CHILD_PROOF CHILD_EVIDENCE [CHILD_PROOF CHILD_EVIDENCE ...]" >&2
  exit 2
}

if [[ $# -lt 9 || $((($# - 7) % 2)) -ne 0 ]]; then
  usage
fi

repository=$1
data_root=$2
directory_rel=$3
prefix=$4
base_cnf=$5
replay=$6
prefix_proof=$7
shift 7
poll_seconds=${RAMSEY55_POLL_SECONDS:-30}
global_lock=${RAMSEY55_FINALIZER_LOCK:-/tmp/ramsey55-residual-finalizer.lock}

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
for input in "$base_cnf" "$replay" "$prefix_proof" "$@"; do
  if [[ $input != /* ]]; then
    echo "explicit input paths must be absolute: $input" >&2
    exit 2
  fi
done

repository=${repository%/}
data_root=${data_root%/}
directory=$data_root/$directory_rel
checker=$repository/.tools/src/drat-trim/drat-trim
final=$directory/$prefix-final-v1

test -d "$repository"
test -d "$data_root"
test -d "$directory"
test -s "$base_cnf"
test -s "$replay"
test -s "$prefix_proof"
test -x "$checker"

child_proofs=()
child_evidences=()
while [[ $# -gt 0 ]]; do
  child_proofs+=("$1")
  child_evidences+=("$2")
  shift 2
done

exec 8>"$final.watcher.lock"
if ! flock -n 8; then
  echo "another finalizer watcher owns $final.watcher.lock" >&2
  exit 3
fi

printf 'RAMSEY55_RECURSIVE_PREFIX_WATCHER_V1_START %s %s %s\n' \
  "$prefix" "${#child_proofs[@]}" "$(date -Is)"

while :; do
  ready=1
  for ((index=0; index<${#child_proofs[@]}; index++)); do
    proof=${child_proofs[index]}
    evidence=${child_evidences[index]}
    if [[ ! -s $proof || ! -s $evidence ]]; then
      ready=0
      continue
    fi
    if [[ $evidence = *.json ]]; then
      jq -e '
        ((.schema == "ramsey55.cadical-dfs-checkpoint-finalization.v1") or
         (.schema == "ramsey55.checked-binary-drat-fragment-promotion.v1")) and
        .checker_verified == true and
        .output_fragment.contains_empty_addition == false
      ' "$evidence" > /dev/null
    elif ! grep -q $'^status\t20$' "$evidence" ||
         ! grep -q $'^proof_fragment\t1$' "$evidence" ||
         ! grep -q $'^root_index\tall$' "$evidence" ||
         ! grep -q $'^cubes\t1$' "$evidence"; then
      ready=0
    fi
  done
  if [[ $ready -eq 1 ]]; then
    break
  fi
  sleep "$poll_seconds"
done

for suffix in \
  fragment.drat standalone.drat checker.log manifest.json \
  finalizer.log finalizer.time audit.log audit.time; do
  test ! -e "$final.$suffix"
done

exec 9>"$global_lock"
flock 9
printf 'RAMSEY55_RECURSIVE_PREFIX_FINALIZER_START %s %s\n' \
  "$prefix" "$(date -Is)"
children=()
for ((index=0; index<${#child_proofs[@]}; index++)); do
  children+=(--child "${child_proofs[index]}" "${child_evidences[index]}")
done
/usr/bin/time -v -o "$final.finalizer.time" \
  python3 "$repository/tools/finalize_cadical_dfs_checkpoint.py" \
    "$base_cnf" "$replay" "$prefix_proof" \
    "$final.fragment.drat" "$final.standalone.drat" \
    "$final.checker.log" "${children[@]}" \
    --checker "$checker" --drop-deletions \
    --manifest "$final.manifest.json" \
    > "$final.finalizer.log" 2>&1

printf 'RAMSEY55_RECURSIVE_PREFIX_AUDIT_START %s %s\n' \
  "$prefix" "$(date -Is)"
/usr/bin/time -v -o "$final.audit.time" \
  python3 "$repository/tools/audit_cadical_dfs_checkpoint_finalization.py" \
    "$final.manifest.json" --root "$data_root" --rerun-checker \
    > "$final.audit.log" 2>&1
jq -e --argjson children "${#child_proofs[@]}" '
  .schema == "ramsey55.cadical-dfs-checkpoint-finalization-audit.v1" and
  .verified == true and .children == $children and
  .replay_independently_verified == true and
  .checker_rerun.verified == true
' "$final.audit.log" > /dev/null

sha256sum "$final.manifest.json" "$final.audit.log" \
  "$final.finalizer.time" "$final.audit.time"
printf 'RAMSEY55_RECURSIVE_PREFIX_ACCEPTED %s %s\n' \
  "$prefix" "$(date -Is)"
