#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
output=${1:-"$repo_dir/build/generate_order45_fixed_pair_cnf"}

mkdir -p "$(dirname "$output")"
c++ -std=c++20 -O3 -DNDEBUG -DRAMSEY55_ORDER45_FIXED_PAIR \
  "$repo_dir/tools/generate_degree18_pair_cnf.cpp" -o "$output"
echo "built $output"
