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
echo "cube proof smoke test passed"
