# ARM cold archive

Updated: 2026-08-24

## Scope and logical status

The user-requested cold archive freezes the ARM workspace at
`/data/ramsey55`.  It is a storage operation, not a proof result.  All Ramsey55
producers, checkers, finalizers, and watchers were stopped before the snapshot.
An unfinished DRAT stream or checker directory in the archive remains an
unfinished computation and receives no logical credit.

The archive lives outside the source tree at `/data/ramsey55-archive-v1`.
There is not enough free space to create a 1.66 TB monolithic archive before
removing anything, so the snapshot is sharded.  The largest first-level shard
is about 142 GB, below the approximately 276 GB free-space margin at the start
of the operation.  Each shard is completed, audited, and made recoverable
before its exact source directory is removed; this progressively creates the
space needed for the remaining shards.

## Per-shard artifacts

Each completed shard has four retained files:

- `NAME.tar.zst`: GNU-tar payload compressed with zstd;
- `NAME.archive.json`: source statistics, compressed-file identity, raw tar
  byte count and SHA-256, tool identities, and verification claims;
- `NAME.audit.json`: an independent rehash, zstd test, complete tar parse, and
  GNU-tar comparison against the still-present source;
- `NAME.removal.json`: a receipt written only after a second current audit and
  successful removal of the exact source directory.

`tools/archive_zstd_directory.py` creates the first three artifacts without
deleting the source.  `tools/audit_zstd_directory_archive.py` can re-audit a
retained archive after the source is gone; when the source is present it also
performs a full metadata-and-content comparison.  The deliberately separate
`tools/remove_verified_directory_archive_source.py` requires both the prior
audit and a fresh full comparison, rejects active process references and
nested mount points, restricts removal to an exact immediate child of an
explicit parent, and then writes the removal receipt.

All paths and hashes in the JSON records are authoritative.  A shard is not
considered archived merely because a `.tar.zst` file exists.

## Audit and restoration

Re-audit a retained shard without restoring it:

```bash
cd /root/ramsey55
PYTHONPATH=tools python3 tools/audit_zstd_directory_archive.py \
  /absolute/path/to/NAME.archive.json \
  --zstd /usr/bin/zstd --tar /usr/bin/tar
```

To restore a shard, first read its manifest's `source.path`.  Its parent must
exist.  Extract into that parent without overwriting an existing source:

```bash
test ! -e /absolute/original/source
/usr/bin/zstd -q -d -c /absolute/path/to/NAME.tar.zst | \
  /usr/bin/tar --extract --file=- --directory /absolute/original/parent
```

Then require a full comparison:

```bash
cd /root/ramsey55
PYTHONPATH=tools python3 tools/audit_zstd_directory_archive.py \
  /absolute/path/to/NAME.archive.json \
  --zstd /usr/bin/zstd --tar /usr/bin/tar --require-source
```

Container or skeleton shards must be restored before their child shards so
that the recorded parent paths exist.  The top-level snapshot inventory and
completion ledger in `/data/ramsey55-archive-v1` define that order.
