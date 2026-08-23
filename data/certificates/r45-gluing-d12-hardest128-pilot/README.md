# Degree-12 largest-proof sampled HOL4 pilot

This directory records a complete HOL4 kernel replay of the degree-12 leaf
whose raw CaDiCaL proof is largest in the deterministic 128-formula sizing
sample.  “Largest” here means raw proof bytes, not a claim that this is the
hardest leaf in the full 322,140-pair product.

All 128 sample formulas returned UNSAT and their proofs were accepted by
ordinary `drat-trim`.  The selection auditor independently checked the exact
ordered branch/proof manifests, required all 128 `VERIFIED_UNSAT` records,
rehashed all 8,264,274,560 raw proof bytes, and matched the selected branch to
line 251,148 of the 322,140-row upstream problem list.  It selected zero-based
pair index 251,147:

```text
61799329827687162405135973520825 44550800702264017901261388647987
```

Its 1,127,021,956-byte proof is strictly larger than the runner-up's
1,088,909,872 bytes.  The one-row problem list then went through the same
signed-MiniSat and HOL kernel route used by the upstream gluing development.
The child heap had an explicit 20,000 MB limit.  The build completed in
1:43:51 wall time, used 6,056.77 user seconds, and peaked at 21,297,100 KiB
whole-process RSS.  A new HOL4 session loaded the exported theorem in 2.27
seconds and checked conclusion `F`, both `C4524B` and `C4524R` hypotheses,
and absence of an `F` hypothesis.

The raw proof family remains on `sglang-arm-builder` under
`/data/ramsey55/build/r45-gluing-d12-stratified128-v1/proofs-v1/`.  The
six-file generated theory and its child log remain under
`/data/ramsey55/external/barakeel-formal-poly592/src/` in
`work_glue3512_ramsey55_hardest128_pilot_v1/`.  Their exact hashes are bound
by the committed audits.

## Checked core archive

Every one of the 128 raw proofs was independently passed through ordinary
`drat-trim -l CORE -C`, requiring exact `s VERIFIED`, and the resulting core
was then replayed again by ordinary `drat-trim`.  The atomically published
core manifest covers 128/128 listed formulas: 8,264,274,560 source bytes
became 5,154,970,064 core bytes, a ratio of 0.623765586.  The four-worker run
took 3:36:20 wall time, used 42,112.96 aggregate user seconds, peaked at
1,634,368 KiB RSS, and exited zero.

Each core was then compressed with zstd level 1 and immediately decompressed
and rehashed before atomic publication.  The 128 compressed files total
1,598,927,229 bytes, or 0.193474602 of the raw sample.  A separate auditor
then reloaded the upstream branch/proof/core/compressed manifest chain,
rehashed all 5.155 GB of cores and all 256 checker logs, required one exact
`s VERIFIED` in every log, and independently decompressed and rehashed all
128 zstd files.  It reports `verified: true` with 128/128 decompression
identities in 4.91 seconds.  Exact hashes and run summaries are committed in
`core-archive-audit-summary.json`; the large proof archives remain at the
recorded ARM paths.

## Fixed evidence

- branch manifest:
  `78aa98e1832ddb588f166b0d667a7d1694eb9126504a4c09b9e4b67e5936049d`;
- proof manifest:
  `0d59f039b91d686d3ca7420190005b39644492df44e936652958d54e850c50bf`;
- measurement summary:
  `12c46c8fc98d7becf3aaee40933716db6262d2159bf1475252a8a2451b993159`;
- full upstream 322,140-row problem list:
  `eb4b5a4b1d51bdc815c6993574f960afa7d998cc56d4e93a26fdc506f225fd6c`;
- selected one-row problem list:
  `e946ea813e4cc49e9a23fb5351c9799738a58a75bda63f46fb3b803c1d8c7f45`;
- selection audit / GNU-time log:
  `d0f06c1d2000366bd71ae1004eedfc2b133866b49a7ef52f989bcbe34c4ae5f3` /
  `e01351320874ffdbe927c5c0f6b59f64d6573260c0a9ce90a926e229e48a288b`;
- selected raw proof:
  `a5c8fed8afe5f42b5da4b40cf02b2b18875bd832f54bff92473f3f1913426632`;
- HOL build log / GNU-time log:
  `036c0e7cd993ee1aecec36347ebec8b0bf3095e7e9fa4332c813f7d7bccc07ba` /
  `7a707dc0f97e892d298bef6a996931d2f50fa653c9865daeeb8950e641d23874`;
- fresh-load log / GNU-time log:
  `7efd71d0b886389a45567bd52325db8399098fd9f004a695745b0abba853d985` /
  `b6d785fcb6ad490793fc76a971dbf914596a7a3167bdfed09a56b21c62e8dcfa`;
- final HOL theory audit:
  `f867b5c755bf744ea14a5311dbec0a3bbe3579bce442cabf1632a90b3ef8536e`;
- checked-core manifest / compressed-core manifest:
  `b32f0ee688a66842f974a0682ef72ec6c081d051474c4a14a0f4f0448e3cf2c9` /
  `8f28017592ab6b0e77df13fce92d448dc151b911b65b97338ee3389b0dae3380`;
- independent core-archive audit / GNU-time log:
  `bd2f79382d91c85f6222bcb86b8fda842f462680e4ba1ebf0e58a4b7bf002489` /
  `8bc107a189ba6b99ce9e66b905dd2e4e8d4ba02f43323f34d25a6470ba620f50`.

The theory audit additionally binds all six generated theory artifacts, the
child build log, the signed MiniSat executable, the HOL entry point, and the
four repository runner/auditor sources.

## Recheck

With the raw sample proofs and full upstream problem list in their recorded
ARM locations, reproduce the selection audit with:

```bash
python3 tools/audit_r45_gluing_hol_pilot_selection.py \
  /data/ramsey55/build/r45-gluing-d12-stratified128-v1/proof-manifest.json \
  /data/ramsey55/build/r45-gluing-d12-stratified128-v1/manifest.json \
  /data/ramsey55/build/r45-gluing-d12-stratified128-v1/proofs-v1 \
  /data/ramsey55/external/barakeel-formal-poly592/src/glue3512_pbl_ramsey55_v1 \
  /data/ramsey55/external/barakeel-formal-poly592/src/glue3512_pbl_ramsey55_hardest128_v1 \
  --output build/d12-hardest128-selection-audit.json
```

The upstream build and fresh-load commands are documented in
[`doc/r45-upstream-hol-replay.md`](../../../doc/r45-upstream-hol-replay.md).

With the retained core and compressed directories, rerun the independent
storage audit with:

```bash
python3 tools/audit_r45_gluing_compressed_core_proofs.py \
  /data/ramsey55/build/r45-gluing-d12-stratified128-v1/core-proofs-v1/manifest.json \
  /data/ramsey55/build/r45-gluing-d12-stratified128-v1/core-proofs-compressed-v1/manifest.json \
  --zstd /usr/bin/zstd --project-root /root/ramsey55 --jobs 4 \
  --output build/d12-core-archive-audit.json
```

This closes exactly one sampled degree-12 gluing leaf at the HOL kernel
boundary.  It does not cover any of the 322,012 unsampled degree-12 pairs,
prove global generalized-graph enumeration, discharge the fixed-star
theorem, or establish a new Ramsey bound.
