#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
temporary=$(mktemp -d "${TMPDIR:-/tmp}/ramsey55-cube-leaf.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

set +e
"$root/build/prove_cadical_cube_leaf" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" 0 \
  "$temporary/proof.drat" "$temporary/result.tsv" \
  > "$temporary/solver.log"
status=$?
set -e
if [ "$status" -ne 20 ]; then
  cat "$temporary/solver.log" >&2
  echo "leaf proof driver returned $status instead of 20" >&2
  exit 2
fi

python3 "$root/tools/materialize_cnf_cube.py" \
  "$root/tests/data/cube-leaf-smoke.cnf" \
  "$root/tests/data/cube-leaf-smoke.icnf" 0 \
  "$temporary/augmented.cnf"
"$root/.tools/src/drat-trim/drat-trim" \
  "$temporary/augmented.cnf" "$temporary/proof.drat" \
  > "$temporary/checker.log"
grep -q "s VERIFIED" "$temporary/checker.log"

set +e
"$root/.tools/src/drat-trim/drat-trim" \
  "$root/tests/data/cube-leaf-smoke.cnf" "$temporary/proof.drat" \
  > "$temporary/base-only-checker.log"
base_status=$?
set -e
if grep -q "s VERIFIED" "$temporary/base-only-checker.log"; then
  echo "leaf proof unexpectedly verified without the cube units" >&2
  exit 2
fi
echo "cube leaf proof smoke test passed (base-only checker exit $base_status)"
