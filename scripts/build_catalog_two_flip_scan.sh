#!/bin/sh
set -eu

mkdir -p build
${CXX:-c++} -std=c++20 -O3 -DNDEBUG -pthread \
  tools/catalog_two_flip_scan.cpp -o build/catalog_two_flip_scan
${CXX:-c++} -std=c++20 -O3 -DNDEBUG \
  tools/generate_three_flip_cnf.cpp -o build/generate_three_flip_cnf
