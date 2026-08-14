#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cadical="$root/.tools/src/cadical"
output=${1:-"$root/build/prove_cadical_cube_leaf"}
mkdir -p "$(dirname -- "$output")"
${CXX:-c++} -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
  -I"$cadical/src" "$root/tools/prove_cadical_cube_leaf.cpp" \
  "$cadical/build/libcadical.a" -lpthread \
  -o "$output"
