#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
degree=${1:-}
case "$degree" in
  20|21|22) ;;
  *)
    echo "usage: $0 DEGREE(20|21|22) [PROOF-DIRECTORY]" >&2
    exit 2
    ;;
esac

primary=${RAMSEY55_PRIMARY_SPLIT_MAX:-0}
case "$primary" in
  ''|*[!0-9]*)
    echo "RAMSEY55_PRIMARY_SPLIT_MAX must be a nonnegative integer" >&2
    exit 2
    ;;
esac
if [ "$primary" -gt 990 ]; then
  echo "RAMSEY55_PRIMARY_SPLIT_MAX must not exceed 990 graph-edge variables" >&2
  exit 2
fi

proof_dir=${2:-"$root/build/order45-strata/unified-selective-b30000-c128000-la1-primary${primary}-solve10"}
runner=${RAMSEY55_CUBE_PROOF_RUNNER:-"$root/build/prove_cadical_cubes"}
checker=${RAMSEY55_DRAT_CHECKER:-"$root/.tools/src/drat-trim/drat-trim"}
stem="$proof_dir/d$degree"
mkdir -p "$proof_dir"

set +e
"$runner" \
  "$root/build/order45-strata/r55-n45-strata-d$degree.cnf" \
  "$root/build/order45-strata/cubes-d$degree.txt" \
  "$stem.drat" "$stem.tsv" 30000 128000 1 "$primary" 10 \
  > "$stem.log" 2>&1
runner_status=$?
set -e
printf '%s\n' "$runner_status" > "$stem.exit"
if [ "$runner_status" -ne 20 ]; then
  echo "proof runner returned $runner_status instead of 20" >&2
  exit 2
fi

set +e
python3 "$root/tools/audit_order45_strata_proofs.py" \
  --proof-dir "$proof_dir" \
  --checker "$checker" \
  --runner "$runner" \
  --conflicts 30000 \
  --maximum-conflicts 128000 \
  --maximum-lookahead-seconds 1 \
  --maximum-primary-split-variable "$primary" \
  --maximum-solve-seconds 10 \
  --freeze-policy selective \
  --degree "$degree" \
  --output "$stem.audit.json" \
  > "$stem.audit.log" 2>&1
audit_status=$?
set -e
printf '%s\n' "$audit_status" > "$stem.audit-exit"
if [ "$audit_status" -ne 0 ]; then
  echo "strict proof audit failed with status $audit_status" >&2
  exit "$audit_status"
fi

echo "verified selective unified d$degree proof: $stem.audit.json"
