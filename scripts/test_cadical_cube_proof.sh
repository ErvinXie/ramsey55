#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
temporary=$(mktemp -d "${TMPDIR:-/tmp}/ramsey55-cube-proof.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

set +e
"$root/build/prove_cadical_cubes" \
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
"$root/build/prove_cadical_cubes" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" \
  "$temporary/root-proof.drat" "$temporary/root-results.tsv" \
  1 1 0 2 0 0 > "$temporary/root-solver.log"
root_status=$?
set -e
if [ "$root_status" -ne 20 ]; then
  cat "$temporary/root-solver.log" >&2
  echo "root proof driver returned $root_status instead of 20" >&2
  exit 2
fi
python3 "$root/tools/materialize_cnf_cube.py" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" 0 \
  "$temporary/root-augmented.cnf" >/dev/null
"$root/.tools/src/drat-trim/drat-trim" \
  "$temporary/root-augmented.cnf" "$temporary/root-proof.drat" \
  > "$temporary/root-checker.log"
grep -q "s VERIFIED" "$temporary/root-checker.log"

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
