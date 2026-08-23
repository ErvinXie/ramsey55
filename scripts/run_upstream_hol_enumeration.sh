#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 UPSTREAM_ROOT JOBS" >&2
  exit 2
fi

upstream_root=$1
jobs=$2
if [[ ! $jobs =~ ^[1-9][0-9]*$ ]]; then
  echo "JOBS must be a positive integer" >&2
  exit 2
fi
if [[ ! -x $upstream_root/HOL/bin/Holmake ]]; then
  echo "missing Holmake under $upstream_root" >&2
  exit 2
fi
if [[ ! -f $upstream_root/src/enump/Holmakefile ]]; then
  echo "missing generated enumeration Holmakefile" >&2
  exit 2
fi

cd "$upstream_root/src/enump"
exec ../../HOL/bin/Holmake -j "$jobs"
