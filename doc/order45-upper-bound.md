# Order-45 upper-bound program

Updated: 2026-08-15

## Current status

The target is to prove \(R(5,5)\le45\) by excluding every Ramsey-free
two-colouring of \(K_{45}\). The theorem is **not proved**. What is complete at
this checkpoint is the normalization to two labelled SAT branches, an exact
independent audit of those CNFs, and a quantitative test of how much the
public extreme \(R(4,5)\) catalogs cover under the elementary excess identity.

## Complete labelled reduction

Let \(G\) be a hypothetical graph on 45 vertices with neither a \(K_5\) nor an
independent set of size five. For every vertex \(v\):

- \(G[N(v)]\in\mathcal R(4,5,d(v))\), so \(d(v)\le24\) by \(R(4,5)=25\);
- the complement of \(G[V\setminus(N(v)\cup\{v\})]\) is in
  \(\mathcal R(4,5,44-d(v))\), so \(d(v)\ge20\).

Thus every degree lies in \([20,24]\). The handshake lemma says that the
number of odd-degree vertices is even. Since there are 45 vertices, some
vertex therefore has even degree 20, 22, or 24. Colour complementation sends
the degree-24 case to degree 20. Relabelling the selected vertex to zero and
placing its neighbours first gives exactly two fixed-star branches:

| branch | fixed clauses |
|---:|---|
| 20 | \(0i\) is an edge for \(1\le i\le20\), and a nonedge otherwise |
| 22 | \(0i\) is an edge for \(1\le i\le22\), and a nonedge otherwise |

`src/ramsey55/order45.py` implements this normalization on explicit graphs,
and its degree-20, degree-22, and complemented degree-24 paths are unit tested.
The formal file `formal/Ramsey55/Order45.lean` currently checks the arithmetic
parity reduction from degree counts. A final formal bridge still needs a
machine-checked \(R(4,5)=25\) dependency, actual graph degree counts, colour
complementation, and the relabelling equivalence. The complete 75-target Lean
project, including this new file, builds successfully with pinned Lean 4.31.0
on the ARM node.

`formal/Ramsey55/CubeCover.lean` now supplies the generic certificate
composition layer: binary literal splits preserve cube coverage, and an
exhaustive family whose every formula/cube conjunction is UNSAT makes the
mother CNF UNSAT. The latter theorem has an empty axiom audit. Concrete DIMACS
semantics, generated cover data, checked leaf results, and the graph-to-CNF
bridge remain to be connected before this yields an order-45 theorem.

## Exact raw SAT benchmarks

`tools/generate_order45_benchmarks.py` emits both labelled formulas. Each has
one variable per edge of \(K_{45}\), two ten-literal clauses for each
five-set, and 44 fixed-star unit clauses. The independently implemented
streaming verifier in `tools/verify_order45_benchmarks.py` reconstructs every
variable and clause rather than calling the generator.

| branch | variables | clauses | SHA-256 |
|---:|---:|---:|---|
| 20 | 990 | 2,443,562 | `57984e902587656e67c88c6394fdb58c6f72d5e0ac8deda9c9d839b05957f12b` |
| 22 | 990 | 2,443,562 | `1675b35934f64d3f3af15550eec3b510b359be2cd69d1d6a5f2bffb1ccb52d15` |

The small committed manifest is `data/order45-benchmark-manifest.json`; the
107 MiB CNFs remain generated build artifacts. Reproduce and verify them with:

```bash
PYTHONPATH=src python3 tools/generate_order45_benchmarks.py
PYTHONPATH=src python3 tools/verify_order45_benchmarks.py \
  data/order45-benchmark-manifest.json --cnf-dir build/order45
```

On the 64-vCPU ARM node, four independent 60-second probes all timed out.
Kissat reached about 399,588 conflicts on degree 20 and 201,975 on degree 22,
using about 360 MiB per process. These are profiling runs only: timeout is
neither UNSAT nor a certificate.

### Degree-window strengthening

The raw formulas do not encode the already known degree window for vertices
other than the fixed apex. `src/ramsey55/cardinality.py` now supplies a
bidirectional sequential counter, and
`tools/generate_order45_strengthened_benchmarks.py` applies the range 20--24
to vertices 1 through 44. Every counter state is an equivalence, not merely a
one-way implication. The implementation is exhaustively checked over all
primary and auxiliary assignments through four inputs.

| branch | variables | clauses | SHA-256 |
|---:|---:|---:|---|
| 20 | 36,190 | 2,581,414 | `e3e0ec995135e1aa3f36bc256b8c72c78fd3357a31372ccd848a19aaba345174` |
| 22 | 36,190 | 2,581,414 | `c643341fcc364b766724df5ee2a6d7d0db5109bb853bfdfaf787ff8c51aca211` |

An independent encoder reconstructs all clauses and checks the committed
manifest. A separate generic DIMACS audit proves that each raw formula's
2,443,562 clauses are an exact prefix; the strengthening adds 35,200
variables and 137,852 clauses. Its logical use still depends on the
\(R(4,5)=25\) degree-window theorem, whose Lean bridge remains explicit above.

```bash
PYTHONPATH=src python3 tools/generate_order45_strengthened_benchmarks.py
PYTHONPATH=src python3 tools/verify_order45_strengthened_benchmarks.py \
  data/order45-strengthened-benchmark-manifest.json \
  --cnf-dir build/order45-strengthened
```

The strengthened formulas also remained UNKNOWN in 60-second Kissat probes.
For degree 20/22 they produced respectively 302,578/138,862 conflicts,
1,225,210/1,159,811 decisions, and 64,654,468/56,548,646 propagations. The
roughly 6--10x propagation increase confirms that the counters are active,
but conflict or decision counts across different encodings are not a measure
of distance to UNSAT.

### Cross-row symmetry breaking

After fixing the apex, its neighbours may still be permuted arbitrarily.
Therefore every labelled orbit has a representative in which the neighbours'
Boolean rows to the nonneighbour side are lexicographically nondecreasing.
`src/ramsey55/lex.py` gives a bidirectional prefix-equality encoding, checked
over every primary and auxiliary assignment through width four. Only the
neighbour rows are sorted; independently sorting the opposite columns would
not in general preserve the first ordering.

The d20/d22 formulas have respectively 36,627/36,631 variables and
2,584,036/2,584,060 clauses, with SHA-256
`656b31f45a887c255f8a4ce181cb08e1b89675484ee833b58c03db69bf0558f3`
and `f3e834bab124dc70761e3c33b4461e5d89862cb68b797bfc8e939ec80d22989f`.
An independent recurrence reconstructed every clause.

Both 60-second Kissat probes remained UNKNOWN. The d20/d22 runs produced
176,498/173,090 conflicts, 995,991/1,129,574 decisions, and
60,859,890/59,205,375 propagations. The decision reduction is useful evidence
that the symmetry is active, not an UNSAT result.

## What the elementary excess identity covers

For \(H=G[N(v)]\) and \(J\) the complement of the graph on the nonneighbours
of \(v\), twice the local contribution to the three-vertex identity is

\[
  2c(v)=(44-d)(43-d)-d(45-2d)-2(e(H)+e(J)).
\]

The contributions sum to zero, so some vertex has \(c(v)\le0\). After colour
complementation, an excess witness can have degree 20, 21, or 22. This is
different from the complete fixed-star reduction above: parity removes the
degree-21 SAT branch, but it does **not** prove that the nonpositive excess
witness is even-degree.

The public `r45extreme` data gives the following exact layer audit:

| witness split | doubled constant | required edge sum | feasible edge-count pairs | pairs present in archive | raw catalog-record pairs |
|---|---:|---:|---:|---:|---:|
| 20 + 24 | 452 | at least 226 | 28 | 18 | 316,734,625 |
| 21 + 23 | 443 | at least 222 | 36 | 8 | 3,481,603,081 |
| 22 + 22 | 440 | at least 220 | 45 ordered | 4 ordered | 967,769,881 |

These thresholds are also encoded as a complete three-branch SAT cover.
`tools/generate_order45_excess_benchmarks.py` fixes the nonpositive witness at
the apex, normalizes its degree to 20, 21, or 22, and counts H-edges together
with negated nonneighbour-side edges (the J-edges). The three formulas have
116,518/114,885/114,181 variables and 2,902,909/2,896,390/2,893,579 clauses.
Their SHA-256 values are recorded in
`data/order45-excess-benchmark-manifest.json`, and an independent signed
counter implementation reconstructs every clause. The global identity itself
was exhaustively executed on every graph through order five.

All three 60-second Kissat probes remained UNKNOWN. The d20/d21/d22 decision
counts were 1,087,354/936,207/871,278, with 104,600,340/182,072,997/
187,876,713 propagations. This is a complete structural cover, but not yet a
closed one.

### Exact local-edge strata

The exact known edge ranges for the five relevant \(R(4,5,n)\) orders reduce
the excess cover to 28, 36, and 45 feasible \((e(H),e(J))\) pairs. A second
mother formulation defines separate bidirectional H/J counters. Each exact
pair is then four assumption literals: at least \(h\), not at least \(h+1\),
at least \(j\), and not at least \(j+1\). The independent verifier reconstructs
all three mothers and proves that the emitted cubes are the expected disjoint
cover of every feasible edge pair.

The mothers have 78,697/77,148/76,651 variables and
2,751,846/2,745,658/2,743,672 clauses. Their hashes and the generated cube
files are bound in `data/order45-edge-strata-summary.json`. The exact edge
ranges are an additional external theorem/catalog dependency and remain part
of the final formalization boundary.

`tools/cadical_assumption_scan.cpp` loads each mother once and reuses only
globally valid learned clauses while scanning cubes. At 10,000 conflicts per
cube all 109 cases remained UNKNOWN; aggregate d20/d21/d22 solve time was
97.4/138.2/179.8 seconds. This reuse scan is a difficulty oracle only. Any
eventual UNSAT cube must be rerun independently with its four units and a
checked proof before it can enter the coverage certificate.

### Unique H100 and the top H100/J132 stratum

The most extreme available d20 layer has a single unlabelled
(R(4,5,20)) graph with 100 edges. Fixing that graph while retaining every
24-vertex J with at least 126 edges gives a 63,091-variable,
2,688,807-clause formula. Its SHA-256 is
`6496cd1f444ea7da882d57717f56740114ba382d47cd915ff38df8121aaa3734`.
The generator and a separately implemented clause-by-clause verifier are
`tools/generate_order45_fixed_h100.py` and
`tools/verify_order45_fixed_h100.py`; their stable input and manifest are
`data/reference/r4520.100.g6` and
`data/order45-fixed-h100-manifest.json`.

At the very top of this range, the complete 352,366-record 24-vertex catalog
contains exactly two 132-edge records, at indices 297775 and 326185. Once H
and J are fixed, the apex can be omitted and only the 480 H--J cross edges
remain primary. The two no-symmetry formulas have the following exact audit:

| J index | variables | clauses | SHA-256 |
|---:|---:|---:|---|
| 297775 | 9,746 | 114,968 | `61a21ab44f1d10708f645ebdf70c1b6c4c3544c4548dfa36211a4f89271a4625` |
| 326185 | 9,746 | 115,088 | `e783d6b1c2f01832151938a6ec88e8e3708705d0a1af8bfd8851522a1dac78d6` |

`tools/generate_degree18_pair_cnf.cpp`, compiled with
`RAMSEY55_ORDER45_FIXED_PAIR`, emits the reduced formulas.
`tools/verify_order45_fixed_pair_cnf.py` independently reimplements short
graph6 decoding, the reduced five-set clauses, every degree counter,
automorphism enumeration, and the optional lex encoding. The committed
`data/order45-fixed-pair-manifest.json` deliberately selects the formulas
without symmetry breaking: an UNSAT DRAT for either file then proves the
entire labelled fixed graph-pair problem directly, without trusting a
canonical-labelling argument. The H automorphism group has order 4; the two J
groups have orders 24 and 48.

The generator and independent verifier also support lex-leader constraints
for those explicitly enumerated automorphisms. This optional route is not a
DRAT strengthening of the no-symmetry formula: it instead needs a checked
orbit-representative argument. `formal/Ramsey55/Symmetry.lean` now proves the
generic finite-orbit least-representative theorem. Concrete invariance of the
fixed-pair clauses and correspondence between the emitted lex CNF and that
theorem remain to be connected before a symmetry-reduced UNSAT proof can
close the labelled stratum.
The reproducible symmetry manifest is
`data/order45-fixed-pair-symmetry-manifest.json`: its two formulas have
21,816/32,832 variables, 187,388/253,604 clauses, and SHA-256 values
`6cded9314453d477647984aa99400bcf55704e463de4319891432d2149b1229c` and
`d286a3c81f4618d3d02c73c5288f7aae1fe1352792b28c9f6a373a7e45819f9e`.
The bounded comparison in
`data/order45-fixed-pair-symmetry-pilot.json` is negative telemetry: all four
600-second monolithic CaDiCaL/Kissat runs timed out. For J297775 a depth-10
split left 19, 10, and 3 UNKNOWN cubes after 0.1, 10, and 120-second passes;
the larger J326185 lex formula did not finish that cubing step in 180 seconds.
This is worse than the no-symmetry depth-14 tail and is not a proof result, so
the symmetry encoding is not the current production search path.

Kissat, CaDiCaL, and Minisat all left the monolithic formulas UNKNOWN after
600 seconds. CaDiCaL's native depth-14 cuber instead produced exactly 16,384
cubes per formula. A 0.1-second parallel pass closed 16,361 and 16,364 of
them, followed by 21/23 and 17/20 closures at 10 seconds, and another 1/2 and
2/3 at 120 seconds. No pass found SAT. These numbers are search telemetry,
not a certificate: workers reused learned clauses and a few tail cubes needed
further recursive splitting.

`tools/prove_cadical_cubes.cpp` is the proof-producing path. It traces one
binary DRAT stream, solves each cube under assumptions, calls CaDiCaL's
`conclude()` to derive the negated failed core, and recursively applies a
lookahead split when a conflict budget expires. The implementation now stores
pending signed children on an explicit LIFO stack, preserving the same
positive-then-negative preorder TSV while removing the former depth-1024 C++
recursion guard. A final assumption-free
UNSAT call must derive the empty clause. The complete mechanism is exercised
on `tests/data/cube-proof-smoke.*` and independently accepted by `drat-trim`.
The runner accepts optional maximum-conflict, maximum-lookahead-time, and
maximum-solve-time arguments. The time bounds use CaDiCaL's supported
`Terminator` callback. The lookahead bound is important because probing has no
native propagation limit; on expiry lookahead returns the best
occurrence-ranked split found so far. These controls change only the search
heuristic, not the emitted proof or its independent replay.
The runner now freezes only variables already present in the input cubes and
the explicitly requested primary-variable range; every dynamic split variable
is frozen immediately before recursion. This preserves assumption semantics
while allowing CaDiCaL to eliminate unrelated counter auxiliaries. The runner
logs the policy and exact initial frozen-variable count, and the fixed-pair
auditor independently recomputes and checks that count. The hash-bound
`data/order45-selective-freeze-pilot.json` found little change on the large
edge-stratum samples, but reduced each fixed-pair formula's initial frozen set
from all 9,746 variables to 494 and improved tail-split throughput enough to
justify a second fixed-pair production route. A follow-up that left the
480 cross-edge variables unfrozen reduced the initial set further to the 14
variables used by the input cubes; after 120 seconds both formulas had only
four open branches, versus 20/18 with the primary range frozen. This is the
current preferred fixed-pair production configuration. Every pilot remained
UNKNOWN. A 30,000/100,000-conflict follow-up left 4/4 and 3/4 open branches
respectively; the 10,000 route has the highest split throughput, while a
100,000-conflict production pair is retained as a small-frontier hedge.
An additional optional primary-variable bound replaces auxiliary-variable
lookahead choices by the most frequent unused variable within the bound. For
the fixed H/J encoding, variables 1 through 480 are exactly the H--J cross
edges, so this mode directs difficult tails back toward structural choices.
An optional final root index switches the runner from a monolithic refutation
to an independently checkable cube proof. It closes only that root's dynamic
binary subtree, derives the root blocking clause with `conclude()`, and ends
with an empty step that is valid against the base CNF augmented by the cube's
unit clauses. The smoke test deliberately uses a satisfiable base formula:
`drat-trim` accepts the augmented CNF and rejects the same proof against the
base formula alone. A collection of such leaf proofs establishes the mother
formula only together with an independently checked exhaustive cube cover.
`tools/audit_order45_strata_leaf_proofs.py` enforces that composition: it
binds each exported cube to the independently verified formula manifest,
checks the per-root result tree and recorded runner limits, regenerates the
temporary cube-augmented CNF, and replays every leaf proof. Missing leaves are
fatal by default; `--allow-partial` produces only an explicitly incomplete
progress inventory.
The same runner can instead process every root for one degree in a single
proof stream. Its final assumption-free solve derives the empty clause from
the mother CNF, so this route needs only three base-formula DRAT replays and
can reuse learned clauses between roots. `tools/audit_order45_strata_proofs.py`
checks this unified route against the same formula/cube manifest, result-forest
balance, logged effective parameters, and independent `drat-trim` replay.
The committed `data/order45-strata-leaf-pilot.json` records four 120-second
parameter comparisons with formula, cube, runner, and TSV hashes. It is
explicitly UNKNOWN telemetry. Its historical root-only runner had an argument
parsing defect that ignored the requested per-solve time cap; the manifest now
records both the requested value and the true effective value zero. No proof
claim depended on those runs. The corrected runner prints all effective
parameters into its log, and the leaf auditor requires them to match its
declared configuration. On the representative d20/d21/d22 cubes,
10,000-conflict auxiliary splitting left 2/1/2 open leaves, versus 14/13/15
when dynamic choices were forced to the 990 graph-edge variables and 4/4/7
with the lower 1,000-conflict auxiliary budget. Raising the auxiliary budget
to 30,000 left exactly one open leaf in all three cases at depths 4/5/5. The
30,000-conflict auxiliary configuration is therefore the current production
choice; all four pilot configurations remain UNKNOWN rather than proofs.
`tools/audit_order45_fixed_pair_proofs.py` checks formula and cube hashes,
complete balanced result forests, the recorded runner parameters, and each
DRAT replay before writing a compact artifact manifest.
The large two-formula proof and replay are still pending at this checkpoint;
therefore even this top local stratum is not yet claimed closed.

Live proof-frontier diagnosis is now reproducible with
`tools/export_proof_frontier.py`. The tool replays the flushed preorder DFS
table with an explicit stack and exports precisely the nodes that have not yet
been visited. It accepts both one-root proof files and unified multi-root
files, while checking the global attempt sequence, root order, signed branch
literals, depth transitions, and the identity
`open = 1 + splits - closed`. A final incomplete TSV record is tolerated only
because a live writer can be observed between writes; an incomplete interior
record is rejected. For a unified stream stopped within one root,
`--include-later-roots` additionally appends every untouched later input root
and rejects the operation if any of them already has a result row. Thus the
export can represent the entire remaining mother-formula cover, rather than
only the partial current tree.

The hash-bound snapshot in `data/order45-proof-frontier-pilot.json` separates
easy pending siblings from true hard cores. A 120-second independent pass
reduced the d20/c27 snapshot from 22 to 2 cubes and d22/c15 from 6 to 2, but
both depth-512 d20 unified cubes remained UNKNOWN. On the fixed-pair final
root, the four production snapshots reduced from 7/4/4/1 to 3/2/2/1. No scan
found SAT. These are search measurements only: a reconstructed open frontier
does not contain the DRAT justification for already closed siblings, so it is
not by itself a resumable certificate or an UNSAT proof.

The proof runner now also has an explicit `--fragment` mode for composing a
flushed proof prefix with proofs of exactly that reconstructed frontier. A
fragment closes all input cubes and flushes its proof trace, but deliberately
skips the final assumption-free solve and does not append an empty clause.
`tools/compose_binary_drat.py` concatenates binary traces atomically and can
append the binary empty step only at the final composition boundary. The smoke
test closes two complementary children with independent solver instances,
concatenates their traces, and requires `drat-trim` to verify the result against
the parent-cube formula. A real checkpoint still has to pass the same full
replay: runner exit 20 or successful frontier reconstruction alone is never
treated as a certificate, because a copied live proof buffer and independently
generated DRAT state need not compose without checker validation.

This recovery path is also protecting the legacy d20 unified stream from its
depth-1024 runner limit. A live checkpoint at depth 952 copied a
5,137,727,488-byte proof prefix, reconstructed three open current-root cubes,
and appended the 27 untouched edge-pair roots for a 30-cube global frontier.
The source runner was immediately resumed; a separate selective fragment is
working on the global frontier and will compose and replay only after exit 20.
The prefix SHA-256 is
`4849fbb423e15b17f6f5bc56ca7a6bb4e67a913aaf7aac2ae821d414433d84a4`.
This remains an UNKNOWN checkpoint until the complete binary DRAT replay is
verified.

The original recursive d20 process subsequently reached depth 1024 and exited
2 exactly at its documented guard. This does not invalidate the earlier
flushed prefix: the selective checkpoint continuation remains live from the
complete 30-cube residual cover. Future launches use the explicit-stack runner
and therefore do not inherit this host-language depth failure.

The residual cover is independently partitioned for parallel proof production:
one current hard cube, the other two deep snapshot cubes, and three ordered
nine-cube blocks covering the 27 untouched roots. `tools/audit_icnf_partition.py`
requires byte-hashed ordered concatenation to equal the original 30-cube ICNF;
reordering, omission, or duplication is fatal. This permits separately checked
proof fragments without weakening the global cover obligation.

The d20 comparison also rejects an otherwise tempting heuristic change.
Selective freezing with unrestricted lookahead left 1 and 2 branches on the
two hard cubes after 120 seconds, while forcing all dynamic choices into the
990 graph-edge variables left 10 and 10. The active legacy edge proofs are
therefore retained, and any selective-freeze hedge should continue to allow
auxiliary choices rather than impose the graph-edge bound.

That hedge is now running for all three unified mother formulas with exact
configuration `30000/128000 conflicts, 1 second lookahead, primary bound 0,
10 seconds solve`. The logged initial frozen-variable counts are only 16, 18,
and 20 for d20, d21, and d22. The reproducible entry point is
`scripts/run_order45_strata_unified_selective_proof.sh`. It gates the checker
on runner exit 20 and invokes the unified auditor in selective mode; the
auditor independently recomputes the initial freeze count before accepting a
proof. These three jobs are hedges alongside the legacy jobs, and none is a
certificate until its mother-CNF DRAT replay and strict audit both pass.

The arithmetic part of the concrete cube bridge is now kernel-checked in
`formal/Ramsey55/Order45CubeCover.lean`. Its list construction matches the
generator's H-major/J-minor iteration and threshold filter, proves the exact
28/36/45 lengths, and proves that every pair satisfying the catalog edge
ranges and 226/222/220 density threshold belongs to the corresponding list.
It then maps each pair to the same four observable counter literals used in
DIMACS and proves coverage under an explicit exact-counter semantic contract.
`formal/Ramsey55/CnfCardinality.lean` now proves the concrete four
sequential-counter cell encodings sound and lifts them through a finite
row/width induction to that exact-counter contract. The d20/d21/d22 bridge is
instantiated with the actual H/J input sizes and widths. The remaining work at
this layer is to bind the generated DIMACS variable IDs and prove its bound and
sum clauses supply the formal hypotheses; it is not hidden inside a
computational claim. The counter side is now phrased as an exact row-major CNF
substream: satisfaction of a mother containing that substream supplies every
cell recurrence, and the three formula-relative cover theorems consume those
two substream inclusions directly.

Colour swap reduces the last raw count to 483,900,495 unordered pairs. These
numbers are pairs of unlabelled local records before testing a single cross
edge or overlap, so they substantially understate the cost of naive gluing.
They also expose uncovered edge layers: the elementary identity does not
force the witness into the already classified high tails.

The audit is deterministic:

```bash
sh scripts/fetch_r45extreme.sh
PYTHONPATH=src:. python3 tools/analyze_order45_excess_coverage.py
```

The source archive SHA-256 is
`9cfac9dbd1c209cfa342e5d5424df2a7a3fbb008ca00bf0a992e5bbe72f925b6`.
The separately published complete 24-vertex catalog has SHA-256
`83ca4028f206b2fa4315ef219b8c2c57c7835209673dd8183d8fb4353bd4fdd0`
and 352,366 records with edge histogram 116 through 132. Its upper tail
contains 11,485, 3,401, 843, 147, 32, 3, and 2 records at 126 through 132
edges.

## Small-local LP result

The exact rational relaxation in `tools/local_identity_bounds.py` was rerun
with ambient order 45 and all labelled Ramsey-compatible induced types
through order six. Every combined degree interval still crosses zero:

| degree | exact order-six interval |
|---:|---|
| 20 | \([-3489384/25,1070408/5]\) |
| 21 | \([-3472244/25,4498989/20]\) |
| 22 | \([-690096/5,682226/3]\) |
| 23 | \([-688718/5,5872992/25]\) |
| 24 | \([-696376/5,6147466/25]\) |

This rules out the old identity plus edge ranges and only order-at-most-six
local distribution constraints as a sign-separating proof. It does not rule
out whole-neighbourhood constraints, overlap consistency, SDP/SOS-derived
inequalities, or a different counting identity.

## Compute assessment and next bottleneck

The ARM node has 64 logical CPUs, 244 GiB RAM, and about 194 GiB currently
free disk. It is adequate for parallel pilots, catalog scans, cube discovery,
and certificate replay. More raw cores would not fix the present bottleneck:
the weakest catalog-filtered spaces still contain hundreds of millions to
billions of local record pairs, while a direct fixed-star CNF does not close
in short CDCL runs.

The next useful milestone is therefore a stronger, independently checkable
filter that either forces a much smaller set of whole local graphs or groups
large SAT regions under one certified lemma. Once such a cover exists, final
proof production will likely need additional storage and a distributed CPU
pool for DRAT/LRAT generation and replay. Until then, the existing ARM machine
is sufficient for the research loop.

The selective unified launcher also accepts
`RAMSEY55_PRIMARY_SPLIT_MAX=0..990`. The default remains unrestricted
lookahead (`0`). A fresh `990` hedge freezes the graph-edge variables while
leaving deterministic counter auxiliaries eligible for preprocessing; its
directory name records the bound so it cannot overwrite the primary-0
artifacts. This route is deliberately retained despite its wider short-run
frontier because it has a finite structural split set and avoids relying on a
very deep chain of auxiliary assignments.

The primary-990 hedge was later paused recoverably after its three live
frontiers widened to 47/60/58 nodes, while selective primary-0 was at 2/1/19.
Likewise, the fixed-pair 10,000-conflict primary-0 pair was paused at 12/11
open nodes and depths 309/441 because the 100,000-conflict pair had only 4/4
open nodes at depths 104/64. These are portfolio decisions, not proof results:
all partial traces and waiting wrappers are retained, and no stopped stream is
used by a certificate.

The numeric DIMACS bridge is now kernel-checked in
`formal/Ramsey55/Order45Dimacs.lean`. A row-major allocation function starts
from the three post-lex bases and reconstructs every observable H/J output.
It generates the signed 28/36/45 cube lists, checks all six first/last manifest
cubes, and proves that the final J outputs are variables 78697/77148/76651.
It now also reconstructs all six ordered H/J input lists, every typed state
literal, the two counter streams, four range units, and sum-clause tail. Lean
proves each concrete tail covers its 28/36/45 typed cubes and that all 109 map
back to the committed signed DIMACS lists. The remaining formal data step is
only to import the independently audited fact that each mother DIMACS stream
contains this exact suffix; the counter, range, density, and cube semantics no
longer cross that boundary as assumptions.

`tools/audit_order45_counter_tails.py` checks that fact without changing the
production formula manifest or cube hashes. It verifies each full mother hash,
seeks to the exact tail clause offset, independently reconstructs and compares
every remaining clause, and binds both ordered input-ID streams. The committed
`data/order45-counter-tail-manifest.json` records suffix sizes
167,810/161,604/159,612 and hashes `dd952b03...95b4b`,
`7b81acea...4e75`, and `47525d3f...1b10`.

```bash
PYTHONPATH=src:tools:. python3 tools/audit_order45_counter_tails.py
```
