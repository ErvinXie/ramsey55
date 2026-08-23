# R(4,5,25) gluing certificates

The optimized `R(4,5) <= 25` reduction leaves the direct fixed-star degrees
8, 10, and 12.  The published Gauthier--Brown proof handles the same three
cases by covering the two diagonal neighbourhood blocks with generalized
graphs and solving every Cartesian gluing pair.

## Independently reconstructed encoding

`generate_r45_gluing_branches.py` decodes the published leading-one,
row-major base-three graph numbers (`0` hole, `1` blue, `2` red), places the
two generalized graphs on the diagonal of a 24-vertex matrix, and substitutes
their fixed edges into the ordinary `R(4,5,24)` clauses.  Cross edges and
holes remain free.  `verify_r45_gluing_branches.py` has a separate decoder,
edge map, substitution loop, and line-by-line DIMACS reconstruction.

For degree 8, the published cover has 27 `R(3,5;8)` generalized graphs and
two `R(4,4;16)` graphs, hence 54 formulas.  Generation took 5.99 seconds and
independent reconstruction took 4.53 seconds on the ARM host.  The formulas
have 276 declared edge variables and between roughly 2,700 and 4,200 reduced
clauses.  The family manifest SHA-256 is
`868fbdcc094e14840c9589480cd134b6ae3a08fd2a8933e73bb09b98ef60e60b`.

The all-vertex degree-window experiment is a separate route.  It adds the
formally implied degree range `[7,13]` to each direct d08/d10/d12 formula,
using independently reconstructed bidirectional sequential counters.  All
three strengthened formulas have 6,180 variables and 88,460 clauses.  In
matched 300-second CaDiCaL/Kissat runs neither the raw nor strengthened
formula solved; the extra propagation reduced Kissat conflict throughput and
showed no decisive benefit.  It therefore remains verified strategy evidence,
not the production certificate route.

## Degree-8 SAT layer

Proofless CaDiCaL scouting solved 53 of 54 formulas within 60 seconds.  The
last formula solved in 136.04 CPU seconds.  The production run then emitted
one DRAT file per formula and ordinary `drat-trim` accepted all 54.  The
proof-manifest SHA-256 is
`dd3bb57079f53d5e153c1a6146174364716ea2e7b57d66b05f2a99c4ca23858f`;
it binds 510,872,280 proof bytes as well as every CNF, solver log, checker log,
time log, and executable hash.

A second clean 12-way replay checked every proof again in 176.66 wall
seconds.  Its audit SHA-256 is
`8e070a197e5c2676f2b2c2e0e3ffe6382a35481cde83c5c4d7db713a5c26847d`.
The formulas, source covers, manifests, compact logs, and reproduction
instructions are retained in
[`data/certificates/r45-gluing-d08/`](../data/certificates/r45-gluing-d08/README.md).

## Degree-10 and degree-12 sizing samples

The published products beyond d08 are much larger, so a deterministic sparse
sample is used to measure the certificate route before committing to the full
Cartesian products.  For a cover with `L` left rows, `R` right rows, and a
128-point sample, sample number `k` uses

```text
(k mod L) * R + floor((2*k + 1) * R / 256).
```

The generator records these sorted pair indices under the sparse branch
schema; an independent verifier reconstructs every selected CNF.  The proof
collector binds the exact sparse branch manifest, so `complete_unsat` means
complete for those 128 listed formulas only.

For d10, all 128 selected formulas were reported UNSAT by CaDiCaL and accepted
by ordinary `drat-trim`.  The branch, proof, and measurement-summary manifest
SHA-256 values are respectively
`4cc5400ac50b48d0e52aa29cb43686692a7b3bba0b76b03b1072b7bfd38ac9b3`,
`23f7c9ccc1cdcdd3f1ab0cd0ca5e03d55de7eb6b93c55e882a0aeda37991d209`,
and
`0a13cf86128e6cd5373b9c171fc3eeda7e05ce14235a4c40dbf48d1c3d236818`.
The 128 proofs total 7,053,352,972 bytes.  Proof sizes have median 42,139,126,
95th percentile 151,309,304, and maximum 235,039,916 bytes under the exact
nearest-rank definition.  Solver user time totals 13,419.93 seconds and
checker user time totals 16,514.65 seconds.  The complete d10 product contains
505,336 pairs, so this is sizing evidence, not a d10 theorem.

`compact_r45_gluing_proofs.py` now turns this measurement into an auditable
storage experiment.  For every listed formula it reruns `drat-trim` with
binary core-lemma output, requires an exact `s VERIFIED`, and then checks the
emitted core proof again with ordinary `drat-trim`.  The output directory is
published atomically only after all listed formulas pass.  All 128 d10 cores
passed: 7,053,352,972 source-proof bytes became 4,591,869,981 core-proof
bytes, a ratio of 0.651019451.  The core manifest SHA-256 is
`7750e655b042d15acd63fb873131319934614a7f649c6cbdf4fb86fe9887a500`.
The 16-way run took 23:57.36 wall-clock time, used 18,531.27 aggregate user
seconds, peaked at 417,808 KiB RSS, and exited zero; its run and time logs hash
to
`30a52fa46f084a0b4506415f7a5cde9863ec2e340f1c5913b8b0ecff36d0712a`
and
`bd43975b3a3b258ab00c7b527ef239f90f042842c828caa0c7a0ca0c248479ae`.

Compressing every checked core with zstd level 1 and hashing the decompressed
stream reduced the sample further to 1,513,909,974 bytes, or 0.214636922 of
the original proofs.  The compressed-family manifest hashes to
`0ac30aeb681584afef201478064ce74f5cf11fdc8ac4795e6c73b83f724d4808`.
A reproducible replacement for that original manual compression pass is now
provided by
[`compress_r45_gluing_core_proofs.py`](../tools/compress_r45_gluing_core_proofs.py).
It validates the checked-core manifest and every source hash, writes into a
temporary sibling directory, decompresses and rehashes every generated zstd
stream, and publishes atomically only after all records agree.  A fresh
four-worker replay on the same 128 d10 cores reproduced every old compressed
byte count and SHA-256 exactly.  Its expanded manifest, run log, and GNU-time
log hash to
`048e21224288e48817297d1fbdbea0c304796e56a200cedb95cab58f7b6ed7d2`,
`0b37d4911200dbc9fe4fa831cda0d8b521fedd6c988afa3548bf6c9e9e18f5f3`,
and
`fcbd3c23f8a31f27bac11bd5a3985c3dae8964a7513056f00998ebe58a73bcc9`.
The replay took 13.39 seconds wall time and binds zstd 1.5.5 at executable
SHA-256
`de8edfe03230ae3f378e21d845424d7df16803a5d034037bcb0d7d817e792c8e`.
The production form is:

```bash
python3 tools/compress_r45_gluing_core_proofs.py CORE_MANIFEST \
  --output-dir NEW_DIRECTORY --zstd /usr/bin/zstd --level 1 --jobs 4
```

A purely mechanical multiplication of these sample totals by
`505336 / 128` estimates about 5.98 TB of retained compressed d10 proofs and
about 22.85 days on 64 cores for solving, core emission, and core replay.
This extrapolation is capacity planning only: it assumes the deterministic
sample means persist over unsampled pairs and makes no UNSAT claim for them.
It also shows that the present 2 TB ARM data disk cannot retain the full d10
certificate family without batched export to larger durable storage.

The matching d12 production sample has also completed.  All 128 selected
formulas returned UNSAT and were accepted by ordinary `drat-trim`.  The
branch, proof, and summary manifests hash to
`78aa98e1832ddb588f166b0d667a7d1694eb9126504a4c09b9e4b67e5936049d`,
`0d59f039b91d686d3ca7420190005b39644492df44e936652958d54e850c50bf`,
and
`12c46c8fc98d7becf3aaee40933716db6262d2159bf1475252a8a2451b993159`.
The proofs total 8,264,274,560 bytes, with 12,451,360-byte median,
327,474,304-byte 95th percentile, and 1,127,021,956-byte maximum.  Solver and
checker user times total 22,119.62 and 31,493.05 seconds.  The full d12 product
contains 322,140 pairs; mechanical sample-mean scaling gives about 20.80 TB
of raw proofs and 24.45 days of solve-plus-check CPU time on 64 cores.  These
figures are capacity estimates only and make no claim about the 322,012
unsampled pairs.

The sample's largest raw proof has now also passed the upstream HOL4 kernel
route.  A new fail-closed selection auditor checked the ordered branch and
proof manifests, required all 128 checked results, rehashed all 8,264,274,560
raw proof bytes, and matched zero-based pair 251,147 to line 251,148 of the
full upstream d12 problem list.  Its audit hashes to
`d0f06c1d2000366bd71ae1004eedfc2b133866b49a7ef52f989bcbe34c4ae5f3`.
The selected proof has 1,127,021,956 bytes, versus 1,088,909,872 for the
runner-up.  This is a proof-size selection inside the sample, not a claim of
maximum runtime or maximum difficulty in the full product.

The exact one-row HOL build used a checked 20,000 MB child-heap limit.  It
finished in 1:43:51 wall time with 21,297,100 KiB peak whole-process RSS.  A
fresh session loaded the result as a theorem with conclusion `F`, both
`C4524` hypotheses, and no `F` hypothesis.  The final HOL audit hashes to
`f867b5c755bf744ea14a5311dbec0a3bbe3579bce442cabf1632a90b3ef8536e`.
The manifests, logs, problem list, and both audits are retained under
[`data/certificates/r45-gluing-d12-hardest128-pilot/`](../data/certificates/r45-gluing-d12-hardest128-pilot/README.md).
This closes one sampled leaf only; all unsampled d12 pairs remain open.

## Selector-formula experiment

As an alternative to one proof per Cartesian pair, one exact selector CNF
existentially chooses at least one generalized graph on each side and
conditions every non-hole edge of each selected row.  No at-most-one clauses
are required: any satisfying pair extends to selector values, while any
satisfying selector assignment supplies at least one compatible pair.  A
second implementation independently reconstructed the d08 formula.

The d08 selector formula has 305 variables, 54,047 clauses, and SHA-256
`ff624fde6a2a767983b9c7accabf05720a64116ed940a5d32f56f68dffc23f0f`;
its manifest hashes to
`27fc655783131319d696954d425b59500e38da1c85372f1504078395f1928f55`.
After 1,047.81 user seconds CaDiCaL had not returned UNSAT and its partial
binary DRAT trace had reached 551,006,208 bytes, already larger than the
510,872,280-byte aggregate of the 54 independently solved formulas.  The run
was deliberately terminated and the trace retained as `.drat.partial` with
SHA-256
`6323efa357ecc1cf4b3095a8f1f53c9fb6f1cec4a62867e0604c9cc13cbdfc6c`.
It has no accepted checker result.  This negative experiment favors separate
branch proofs; it proves no UNSAT statement.

## Cover boundary

`verify_generalized_graph_cover.py` independently checks each witness
permutation, parent agreement, forbidden-clique condition, and every filling
of the at most four holes.  Exact graph-isomorphism backtracking confirms that
all locally valid completions are represented in the global witness list.
The d08-side audit covers 27 generalized graphs and 179 normalized children;
the order-16 side covers two full graphs.  Their audit hashes are
`0d0eadb8f72ef643fe583438368bf0d36479169b3d7d57e2eb9644ce9fe15aab`
and
`c1e17267e8693115a547171521f575355a34e866d12136fe36e4e5266b69c7dd`.

The exact ordered Cartesian product of those 27 and two rows has now passed
both the retained DRAT route and the upstream HOL4 kernel route.  The latter
fresh-loaded all 54 false-conclusion theorems under both `C4524` hypotheses;
its audit SHA-256 is
`783ebafadf8369743a11ceb49d7d22c1a19f108858a399b611202d751de1180d`.
The full resource and artifact record is in the
[upstream replay note](r45-upstream-hol-replay.md).

This does not by itself prove that those 179 and two isomorphism classes
exhaust all Ramsey graphs of the respective orders.  A clean upstream HOL4
tree pinned to commit `065c07054483e3132f12909103e6d0e35e912c28` now has a
successful runtime, definition-theory, and basic-reduction build on the ARM
host.  Its 1,239-way global enumeration is the active stage; exact pins and
hashes are in the [upstream replay note](r45-upstream-hol-replay.md).  Until
that enumeration, its final merge, and the connection to the direct d08
fixed-star obligation are checked, the repository does not claim the d08
theorem, `R(4,5) <= 25`, or `R(5,5) <= 45`.
