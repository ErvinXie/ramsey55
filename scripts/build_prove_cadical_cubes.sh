#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cadical="$root/.tools/src/cadical"
mkdir -p "$root/build"
${CXX:-c++} -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
  -I"$cadical/src" "$root/tools/prove_cadical_cubes.cpp" \
  "$cadical/build/libcadical.a" -lpthread \
  -o "$root/build/prove_cadical_cubes"
