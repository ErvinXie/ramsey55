#!/bin/sh
set -eu

if [ "$#" -lt 7 ] || [ "$#" -gt 8 ]; then
  echo "usage: run_order45_adaptive_frontier.sh formula initial-cubes initial-results first-round last-round output-prefix jobs [seconds]" >&2
  exit 2
fi

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
formula=$1
cubes=$2
results=$3
first_round=$4
last_round=$5
prefix=$6
jobs=$7
seconds=${8:-0.1}

case "$first_round:$last_round:$jobs" in
  *[!0-9:]*) echo "rounds and jobs must be positive integers" >&2; exit 2 ;;
esac
if [ "$first_round" -lt 1 ] || [ "$last_round" -lt 1 ] || [ "$jobs" -lt 1 ]; then
  echo "rounds and jobs must be positive integers" >&2
  exit 2
fi
if [ "$first_round" -gt "$last_round" ]; then
  echo "first round exceeds last round" >&2
  exit 2
fi

round=$first_round
while [ "$round" -le "$last_round" ]; do
  parents="$prefix-r$round-parents.txt"
  children="$prefix-r$round.icnf"
  refine_results="$prefix-r$round-refine.tsv"
  solve_results="$prefix-r$round-solve.tsv"
  python3 "$root/tools/refine_assumption_frontier.py" \
    "$cubes" "$results" --primary-variables 480 --keep-unknown \
    --output "$parents" --manifest "$prefix-r$round-parents.json" \
    > "$prefix-r$round-parents.log"
  parent_count=$(wc -l < "$parents")
  echo "round=$round unknown_parents=$parent_count"
  if [ "$parent_count" -eq 0 ]; then
    echo "closed=all"
    exit 0
  fi

  "$root/build/refine_cadical_cubes" \
    "$formula" "$parents" "$jobs" "$children" "$refine_results" \
    > "$prefix-r$round-refine.log"
  "$root/build/solve_cadical_cubes" \
    "$formula" "$children" "$seconds" "$jobs" "$solve_results" \
    > "$prefix-r$round-solve.log"
  awk -F '\t' 'NR > 1 { count[$2]++ }
    END { for (status in count) printf "status_%s=%d ", status, count[status]; print "" }' \
    "$solve_results"
  cubes=$children
  results=$solve_results
  round=$((round + 1))
done
