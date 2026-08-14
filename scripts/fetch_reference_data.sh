#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
destination="$project_root/data/reference/r55_42some.g6"
source_url="https://users.cecs.anu.edu.au/~bdm/data/r55_42some.g6"
expected_sha256="067902e853d87b49bcef0d1d4c0e3bbadd238ee18bc65341b079a3ca4780eccb"

mkdir -p "$(dirname -- "$destination")"
temporary=$(mktemp "/tmp/ramsey55-r55_42some.XXXXXX")
trap 'rm -f "$temporary"' EXIT HUP INT TERM

curl -L --fail --silent --show-error "$source_url" -o "$temporary"
actual_sha256=$(shasum -a 256 "$temporary" | awk '{print $1}')
if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "checksum mismatch for $source_url" >&2
    echo "expected: $expected_sha256" >&2
    echo "actual:   $actual_sha256" >&2
    exit 1
fi

cp "$temporary" "$destination"
echo "installed $destination"
