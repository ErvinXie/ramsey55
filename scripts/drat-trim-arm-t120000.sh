#!/bin/sh
set -eu

# Evidence checker wrapper for long ARM runs.  The executable hash is pinned so
# the wrapper cannot silently select a different drat-trim build.  The only
# added option is a 120,000-second resource limit; proof semantics are unchanged.
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
checker=$project_root/.tools/src/drat-trim/drat-trim
expected=8de9a77e5ddf754f10cce7980a7495810ce9f4328c2df4e55419970ae1858d42

[ -x "$checker" ] || {
  echo "missing pinned drat-trim executable: $checker" >&2
  exit 2
}
actual=$(sha256sum "$checker" | awk '{print $1}')
[ "$actual" = "$expected" ] || {
  echo "drat-trim hash mismatch: expected $expected, got $actual" >&2
  exit 2
}

exec "$checker" "$@" -t 120000
