#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
runner=${RAMSEY55_CUBE_PROOF_RUNNER:-"$root/build/prove_cadical_cubes"}
temporary=$(mktemp -d "${TMPDIR:-/tmp}/ramsey55-cube-proof.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

set +e
"$runner" \
  "$root/tests/data/cube-proof-smoke.cnf" \
  "$root/tests/data/cube-proof-smoke.icnf" \
  "$temporary/proof.drat" "$temporary/results.tsv" 1 \
  > "$temporary/solver.log"
status=$?
set -e
if [ "$status" -ne 20 ]; then
  cat "$temporary/solver.log" >&2
  echo "proof driver returned $status instead of 20" >&2
  exit 2
fi
"$root/.tools/src/drat-trim/drat-trim" \
  "$root/tests/data/cube-proof-smoke.cnf" "$temporary/proof.drat" \
  > "$temporary/checker.log"
grep -q "s VERIFIED" "$temporary/checker.log"

set +e
"$runner" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" \
  "$temporary/root-proof.drat" "$temporary/root-results.tsv" \
  1 1 0 2 0.125 0 > "$temporary/root-solver.log"
root_status=$?
set -e
if [ "$root_status" -ne 20 ]; then
  cat "$temporary/root-solver.log" >&2
  echo "root proof driver returned $root_status instead of 20" >&2
  exit 2
fi
grep -q '^maximum_solve_seconds[[:space:]]0.125$' \
  "$temporary/root-solver.log"
grep -q '^root_index[[:space:]]0$' "$temporary/root-solver.log"
grep -q '^freeze_policy[[:space:]]selective$' "$temporary/root-solver.log"
python3 "$root/tools/materialize_cnf_cube.py" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" 0 \
  "$temporary/root-augmented.cnf" >/dev/null
"$root/.tools/src/drat-trim/drat-trim" \
  "$temporary/root-augmented.cnf" "$temporary/root-proof.drat" \
  > "$temporary/root-checker.log"
grep -q "s VERIFIED" "$temporary/root-checker.log"

# Two proof streams independently close the complementary children of the
# same parent cube. Neither fragment performs a final solve or emits an empty
# clause; concatenating both streams and appending the binary empty step must
# verify against the parent-cube augmented formula.
printf 'a -1 2 0\n' > "$temporary/fragment-positive.icnf"
printf 'a -1 -2 0\n' > "$temporary/fragment-negative.icnf"
for branch in positive negative; do
  set +e
  "$runner" \
    "$root/tests/data/cube-leaf-smoke.cnf" \
    "$temporary/fragment-$branch.icnf" \
    "$temporary/fragment-$branch.drat" \
    "$temporary/fragment-$branch.tsv" \
    100 100 0 2 0 --fragment \
    > "$temporary/fragment-$branch.log"
  fragment_status=$?
  set -e
  if [ "$fragment_status" -ne 20 ]; then
    cat "$temporary/fragment-$branch.log" >&2
    echo "fragment proof driver returned $fragment_status instead of 20" >&2
    exit 2
  fi
  grep -q '^proof_fragment[[:space:]]1$' \
    "$temporary/fragment-$branch.log"
done

# An internal wall deadline must leave a clean, replayable no-empty prefix
# instead of relying on an external timeout to kill the writer mid-clause.
set +e
RAMSEY55_CADICAL_WALL_SECONDS=0.000001 "$runner" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$temporary/fragment-positive.icnf" \
  "$temporary/checkpoint-prefix.drat" \
  "$temporary/checkpoint-results.tsv" \
  100 100 0 2 0 --fragment \
  > "$temporary/checkpoint.log"
checkpoint_status=$?
set -e
if [ "$checkpoint_status" -ne 0 ]; then
  cat "$temporary/checkpoint.log" >&2
  echo "checkpoint proof driver returned $checkpoint_status instead of 0" >&2
  exit 2
fi
grep -q '^maximum_wall_seconds[[:space:]]1e-06$' \
  "$temporary/checkpoint.log"
grep -q '^checkpoint[[:space:]]1$' "$temporary/checkpoint.log"
grep -q '^status[[:space:]]0$' "$temporary/checkpoint.log"
python3 "$root/tools/replay_cadical_dfs_prefix.py" \
  "$temporary/fragment-positive.icnf" \
  "$temporary/checkpoint-results.tsv" \
  "$temporary/checkpoint-open.icnf" \
  --proof-prefix "$temporary/checkpoint-prefix.drat" \
  --manifest "$temporary/checkpoint-replay.json" >/dev/null
grep -q '^a -1 2 0$' "$temporary/checkpoint-open.icnf"

python3 "$root/tools/compose_binary_drat.py" --append-empty \
  "$temporary/composed-root-proof.drat" \
  "$temporary/fragment-positive.drat" \
  "$temporary/fragment-negative.drat" >/dev/null
"$root/.tools/src/drat-trim/drat-trim" \
  "$temporary/root-augmented.cnf" "$temporary/composed-root-proof.drat" \
  > "$temporary/composed-root-checker.log"
grep -q "s VERIFIED" "$temporary/composed-root-checker.log"

# Exercise the complete reusable protected-CNF pipeline: compose the two
# no-empty fragments while preserving learned deletions, verify the resulting
# standalone proof, independently audit it, and promote it back to a checked
# embeddable fragment.
RAMSEY55_DRAT_TRIM="$root/.tools/src/drat-trim/drat-trim" \
  "$root/scripts/run_checked_protected_cnf_promotion.sh" \
  "$temporary/root-augmented.cnf" "$temporary/checked-root" \
  "$temporary/fragment-positive.drat" \
  "$temporary/fragment-negative.drat" \
  > "$temporary/checked-root-pipeline.log"
grep -q '^verified promotion:' "$temporary/checked-root-pipeline.log"
python3 - "$temporary/checked-root-promotion-audit.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    assert json.load(stream)["verified"] is True
PY

set +e
"$root/.tools/src/drat-trim/drat-trim" \
  "$root/tests/data/cube-leaf-smoke.cnf" "$temporary/root-proof.drat" \
  > "$temporary/root-base-only-checker.log"
base_status=$?
set -e
if grep -q "s VERIFIED" "$temporary/root-base-only-checker.log"; then
  echo "root proof unexpectedly verified without the cube units" >&2
  exit 2
fi
echo "cube proof smoke tests passed (base-only checker exit $base_status)"
