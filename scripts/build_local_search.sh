#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$project_root/build"

c++ -std=c++20 -O3 -Wall -Wextra -pedantic \
  "$project_root/tools/local_search.cpp" \
  -o "$project_root/build/local_search"

echo "built $project_root/build/local_search"
