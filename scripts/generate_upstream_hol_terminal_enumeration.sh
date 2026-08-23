#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 UPSTREAM_ROOT" >&2
  exit 2
fi

upstream_root=$1
terminal_base=ramseyEnum4418_0
terminal_script=$upstream_root/src/enump/${terminal_base}Script.sml

if [[ ! -x $upstream_root/HOL/bin/hol ]]; then
  echo "missing HOL executable under $upstream_root" >&2
  exit 2
fi
if [[ ! -s $upstream_root/src/enump.uo ]]; then
  echo "missing built enump module under $upstream_root/src" >&2
  exit 2
fi
for suffix in Script.sml Theory.sml Theory.sig Theory.dat Theory.ui Theory.uo; do
  if [[ -e $upstream_root/src/enump/${terminal_base}${suffix} ]]; then
    echo "refusing to overwrite terminal enumeration artifact: ${terminal_base}${suffix}" >&2
    exit 2
  fi
done

temporary_directory=$(mktemp -d)
trap 'rm -rf "$temporary_directory"' EXIT
generation_log=$temporary_directory/generation.log

(
  cd "$upstream_root/src"
  printf '%s\n' \
    'load "enump"; open enump;' \
    'write_enumscripts 50 18 (4,4);' |
    ../HOL/bin/hol --maxheap=50000 --q
) | tee "$generation_log"

if [[ $(grep -Ec '(^|> )par: 1$' "$generation_log") -ne 1 ]]; then
  echo "HOL did not report the unique order-17 input graph" >&2
  exit 1
fi
if [[ ! -s $terminal_script ]]; then
  echo "HOL did not create the terminal order-18 enumeration script" >&2
  exit 1
fi

python3 - "$terminal_script" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
if len(lines) != 5:
    raise SystemExit("terminal enumeration script must contain exactly five lines")
if lines[0] != "open HolKernel boolLib kernel enump ramseyDefTheory":
    raise SystemExit("unexpected terminal enumeration imports")
if lines[1] != 'val _ = new_theory "ramseyEnum4418_0"':
    raise SystemExit("unexpected terminal enumeration theory name")
if lines[2] != "val _ = INIT_NEXT_R_THM_ONE 18 (4,4)":
    raise SystemExit("unexpected terminal enumeration initialization")
save_pattern = re.compile(
    r'^val _ = save_thm \("R4418_0", NEXT_R_THM_ONE 18 \(4,4\) '
    r'\(stinf "[0-9]+"\)\)$'
)
if not save_pattern.fullmatch(lines[3]):
    raise SystemExit("unexpected terminal enumeration theorem command")
if lines[4] != "val _ = export_theory ()":
    raise SystemExit("missing terminal enumeration export")
print(f"generated and validated {path}")
PY
