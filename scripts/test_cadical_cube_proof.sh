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
python3 "$root/tools/compose_binary_drat.py" --append-empty \
  "$temporary/composed-root-proof.drat" \
  "$temporary/fragment-positive.drat" \
  "$temporary/fragment-negative.drat" >/dev/null
"$root/.tools/src/drat-trim/drat-trim" \
  "$temporary/root-augmented.cnf" "$temporary/composed-root-proof.drat" \
  > "$temporary/composed-root-checker.log"
grep -q "s VERIFIED" "$temporary/composed-root-checker.log"

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
