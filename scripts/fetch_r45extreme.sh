#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_url="https://users.cecs.anu.edu.au/~bdm/data/r45extreme.tar.gz"
expected_sha256="9cfac9dbd1c209cfa342e5d5424df2a7a3fbb008ca00bf0a992e5bbe72f925b6"
destination="$project_root/build/r45extreme-data"

temporary=$(mktemp "/tmp/ramsey55-r45extreme.XXXXXX")
trap 'rm -f "$temporary"' EXIT HUP INT TERM

curl -L --fail --silent --show-error "$source_url" -o "$temporary"
actual_sha256=$(shasum -a 256 "$temporary" | awk '{print $1}')
if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "checksum mismatch for $source_url" >&2
    echo "expected: $expected_sha256" >&2
    echo "actual:   $actual_sha256" >&2
    exit 1
fi

mkdir -p "$destination"
tar -xzf "$temporary" -C "$destination"
echo "installed $destination/r45extreme"
