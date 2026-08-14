#!/bin/sh
set -eu

mkdir -p build
${CXX:-c++} -std=c++20 -O3 -DNDEBUG -Wall -Wextra -pedantic \
  tools/r45_identity_scan.cpp -o build/r45_identity_scan
