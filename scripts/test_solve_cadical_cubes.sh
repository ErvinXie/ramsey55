#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "usage: $0 [SOLVER]" >&2
  exit 2
fi

repository=$(cd "$(dirname "$0")/.." && pwd)
solver=${1:-$repository/build/solve_cadical_cubes}
cnf=$repository/tests/data/cube-proof-smoke.cnf
cubes=$repository/tests/data/cube-proof-smoke.icnf

test -x "$solver"
test -s "$cnf"
test -s "$cubes"

temporary=$(mktemp -d)
trap 'rm -r -- "$temporary"' EXIT

"$solver" "$cnf" "$cubes" 10 1 "$temporary/default.tsv" \
  > "$temporary/default.log"
RAMSEY55_CADICAL_SEED=37 RAMSEY55_CADICAL_PHASE=0 \
  "$solver" "$cnf" "$cubes" 10 1 "$temporary/seeded.tsv" \
  > "$temporary/seeded.log"

set +e
RAMSEY55_CADICAL_PHASE=2 \
  "$solver" "$cnf" "$cubes" 10 1 "$temporary/invalid.tsv" \
  > "$temporary/invalid.log" 2>&1
status=$?
set -e
test "$status" -eq 2

awk -F '\t' '
  $1 == "cadical_seed" && $2 == 0 { found = 1 }
  END { exit !found }
' "$temporary/default.log"
awk -F '\t' '
  $1 == "cadical_phase" && $2 == 1 { found = 1 }
  END { exit !found }
' "$temporary/default.log"
awk -F '\t' '
  $1 == "cadical_seed" && $2 == 37 { found = 1 }
  END { exit !found }
' "$temporary/seeded.log"
awk -F '\t' '
  $1 == "cadical_phase" && $2 == 0 { found = 1 }
  END { exit !found }
' "$temporary/seeded.log"
awk -F '\t' '
  FNR > 1 && $2 != 20 { exit 1 }
' "$temporary/default.tsv" "$temporary/seeded.tsv"
grep -Fx 'error: invalid RAMSEY55_CADICAL_PHASE' \
  "$temporary/invalid.log" > /dev/null

echo "solve_cadical_cubes seed/phase smoke test passed"
