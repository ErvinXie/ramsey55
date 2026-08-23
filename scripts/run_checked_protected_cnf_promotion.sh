#!/bin/sh
set -eu

usage() {
  echo "usage: $0 input.cnf output-prefix fragment.drat [...]" >&2
  exit 2
}

[ "$#" -ge 3 ] || usage

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cnf=$1
prefix=$2
shift 2

checker=${RAMSEY55_DRAT_TRIM:-.tools/src/drat-trim/drat-trim}
time_tool=${RAMSEY55_GNU_TIME:-/usr/bin/time}

cd "$project_root"

[ -f "$cnf" ] || {
  echo "input CNF does not exist: $cnf" >&2
  exit 2
}
[ -x "$checker" ] || {
  echo "DRAT checker does not exist or is not executable: $checker" >&2
  exit 2
}
[ -x "$time_tool" ] || {
  echo "GNU time does not exist or is not executable: $time_tool" >&2
  exit 2
}
for fragment in "$@"; do
  [ -f "$fragment" ] || {
    echo "input fragment does not exist: $fragment" >&2
    exit 2
  }
done

standalone="$prefix-protected-cnf-standalone.drat"
composition="$prefix-protected-cnf-composition.json"
composition_run="$prefix-protected-cnf-run.json"
composition_time="$prefix-protected-cnf-composition-time.log"
checker_log="$prefix-protected-cnf-checker.log"
checker_time="$prefix-protected-cnf-checker-time.log"
source_audit="$prefix-protected-cnf-audit.json"
source_audit_time="$prefix-protected-cnf-audit-time.log"
promoted="$prefix-promoted-fragment.drat"
promotion="$prefix-promotion.json"
promotion_run="$prefix-promotion-run.json"
promotion_time="$prefix-promotion-time.log"
promotion_audit="$prefix-promotion-audit.json"
promotion_audit_time="$prefix-promotion-audit-time.log"

for output in \
  "$standalone" "$composition" "$composition_run" "$composition_time" \
  "$checker_log" "$checker_time" "$source_audit" "$source_audit_time" \
  "$promoted" "$promotion" "$promotion_run" "$promotion_time" \
  "$promotion_audit" "$promotion_audit_time"
do
  if [ -e "$output" ] || [ -e "$output.tmp" ]; then
    echo "refusing to overwrite output: $output" >&2
    exit 2
  fi
done

temporary=$(mktemp -d "${TMPDIR:-/tmp}/ramsey55-protected-promotion.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

"$time_tool" -v -o "$temporary/composition-time.log" \
  python3 tools/compose_binary_drat_protect_cnf.py \
  "$cnf" "$standalone" "$@" --append-empty --manifest "$composition" \
  > "$temporary/composition-run.json"
mv "$temporary/composition-run.json" "$composition_run"
mv "$temporary/composition-time.log" "$composition_time"

set +e
"$time_tool" -v -o "$temporary/checker-time.log" \
  "$checker" "$cnf" "$standalone" > "$temporary/checker.log"
checker_status=$?
set -e
mv "$temporary/checker.log" "$checker_log"
mv "$temporary/checker-time.log" "$checker_time"
if [ "$checker_status" -ne 0 ]; then
  echo "DRAT checker rejected the protected composition (exit $checker_status)" >&2
  exit 1
fi
python3 - "$checker_log" <<'PY' || {
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    if not any(line.rstrip("\n").strip("\r") == "s VERIFIED" for line in stream):
        raise SystemExit(1)
PY
  echo "DRAT checker log lacks an exact s VERIFIED logical line" >&2
  exit 1
}

"$time_tool" -v -o "$temporary/source-audit-time.log" \
  python3 tools/audit_binary_drat_protect_cnf.py \
  "$composition" --root . --checker-log "$checker_log" --checker "$checker" \
  > "$temporary/source-audit.json"
mv "$temporary/source-audit.json" "$source_audit"
mv "$temporary/source-audit-time.log" "$source_audit_time"

"$time_tool" -v -o "$temporary/promotion-time.log" \
  python3 tools/promote_checked_binary_drat_fragment.py \
  "$composition" "$source_audit" "$promoted" --root . \
  --manifest "$promotion" > "$temporary/promotion-run.json"
mv "$temporary/promotion-run.json" "$promotion_run"
mv "$temporary/promotion-time.log" "$promotion_time"

"$time_tool" -v -o "$temporary/promotion-audit-time.log" \
  python3 tools/audit_checked_binary_drat_fragment_promotion.py \
  "$promotion" --root . --rerun-source-audit \
  > "$temporary/promotion-audit.json"
mv "$temporary/promotion-audit.json" "$promotion_audit"
mv "$temporary/promotion-audit-time.log" "$promotion_audit_time"

python3 -c \
  'import json,sys; assert json.load(open(sys.argv[1]))["verified"] is True' \
  "$promotion_audit"

echo "verified promotion: $promotion"
