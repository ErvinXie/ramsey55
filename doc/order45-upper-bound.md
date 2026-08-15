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

The depth-952 checkpoint now also has a proof-prefix-independent certificate
route. A byte snapshot of its 2,000 DFS rows reconstructs 999 closed leaves
and 30 open leaves over all 28 exact d20 edge-pair roots. The forest manifest,
closed ICNF, and open ICNF have SHA-256 values
`5e2d21624ef408246437c9c72d31ddac7b043262b2d12ff37419a85c210f10a3`,
`2d485bb1e031c101b2a91a7ad9b6358136bafaa042895e980262240a190fe6c3`,
and
`4facb09ec98441fec5b2257ac7922b17b7742018d8c69844f94c75234a3fa3b2`.
Independent forest reconstruction proves that every root is covered, using
32 Boolean DPLL nodes in total. A 30-second materialized CaDiCaL pass then
produced and checked DRAT for 991 of the 999 closed leaves, retaining
3,220,345,242 proof bytes; the remaining leaf indices are
25, 34, 156, 247, 250, 478, 754, and 788. Its manifest SHA-256 is
`47b37d9333eb46dff3d241ec6ff44a4a98f6acafd150a184a5fa675b79ee7cd8`.
The matching pass over all 30 open leaves closed none; its partial-manifest
SHA-256 is
`a6cd24c01e318e36b487792014d1dba525d8a148670c5f372f80623b818ae4d0`.
A 120-second parent-cube pass also closed 0/30, with manifest SHA-256
`bf0c872f1a40f79d72cec076342a7acd2499d560342d38dfed30a1d49ce72417`.
Binary refinement is much stronger here. After independent replay of all 991
closed-leaf proofs, one 120-second round reduced eight hard parents to two,
and the next reduced two to one. On the 30 open parents, a four-second staged
round repeatedly gives exactly one checked easy child per parent: the first
two rounds both ended 30 VERIFIED/30 UNKNOWN rather than widening the
frontier. Thus this is a much smaller, exactly covered d20 residual with a
live certified descent, not yet a d20 UNSAT certificate.

The last closed-side residual has now been eliminated. An exact iGlucose
retry of the round-34 parent returned UNSAT in 505.49 seconds; after proof
compaction the retained DRAT is 20,530,685 bytes. The producer replay and a
separate one-row replay both accepted it. UNKNOWN-only composition with the
round-33 two-row manifest produced 2 VERIFIED/0 UNKNOWN, and a separate full
replay accepted both proofs. The leaf and combined manifest SHA-256 values are
`3ff76dc5b452d5160454003bdd5e84563495584f10be424653e462a242c0bb28`
and `2d2e9f1f6e6848fb21d19473ba92db88d8778e14606cf0b12e4fc585a4741554`;
the independent leaf/full audit-log hashes are
`07521dbcbd17729a5484e9074d6fd0768dfdfc6e92c49eab2ccc038b4c25ca8c`
and `0eee6d01d56ab0f88f6485152c3fb391f0628bd87a45691cea293b1f21a0d90c`.
A terminal chain invocation independently replayed the complete seed before
recording `complete=true` at round 34. Consequently all 999 forest-closed
leaves now have a composable checked proof path. The 30 forest-open branches
remain, so neither the d20 exact-edge augmentation family nor its mother CNF
is yet UNSAT.

The immutable v3 top-level bundle then replayed this claim from the beginning.
It bound the 2,751,846-clause mother CNF and its 28 ordered edge-pair roots,
reconstructed the 999+30 proof forest, audited four closed-chain segments
through the complete round-34 exact-cube retry, and audited three open-chain
segments through the 30-UNKNOWN round-8 checkpoint. Its bundle, audit, and
audit-log SHA-256 values are
`4f2f35a8bc65be6fd0b8a8fc34ed1588e30a39b088ed6224bd78eecf75b3f021`,
`907c4bbafca61c75be695544026c2cb805fca05d5c5fc127c957563aee6e8c6f`,
and `7bf103c25001c296e61b0fd7f2f7d7bfca029e2a701207cafdc692195b72f25d`.
The auditor reports the closed chain complete and the open chain incomplete;
accordingly both `exact_edge_cube_augmentations_unsat` and
`mother_formula_unsat` remain false.

The growth-guarded d20 continuation later exhausted its 100-round allowance.
It held exactly 30 UNKNOWN parents throughout, ending with authoritative state
round 136 and current round-135 manifest SHA-256
`65dc13f445f85c7b4775562637d1fbcc79ea35001bd94470cbc12199373a210f`.
The state and chain-log SHA-256 values are
`fb2dfbc8302cd618d0e7c5f014b8c219df3dfe2110576269f3f3a630ba7f126d`
and
`92760da9823000348da445c42f75a506b943bc1ecf6f710cb2ad703d2864cb63`.
A fresh segment audit replayed 101 proof manifests and reconstructed all 100
complementary refinements, covering 3,000 parents from round 36 through state
round 136. It independently reproduced the final 30 VERIFIED/30 UNKNOWN
summary and `complete_unsat=false`. The segment audit-manifest and log SHA-256
values are
`c40173de4879a0be5c53f3d9cf84980ed4ff8fc8a3046f369f3595c9190072d1`
and
`e65c28228279340f78dcb75002df95eb5093d6ec2fb19180a320e248871da894`.
The deeper chain is therefore independently audited and is adopted by the v5
bundle below, but it does not reduce the d20 residual count.

The immutable v4 bundle extends that same from-scratch audit through the
frozen open round-36 boundary. Its fourth open segment contains 29 proof
manifests, 28 complementary refinements, and 840 refined parents; it ends at
the exact 30 VERIFIED/30 UNKNOWN manifest bound by state SHA-256
`5f6ac0e64ad049e48b1d5a5db3446c1431e24938778a1bf2e7a1086458143545`.
The v4 bundle, audit, and audit-log SHA-256 values are
`65d53c59b6ba0548ecf031090cb27828f6f29132c94c69d6ca9b2d1783106902`,
`b480f877774493b3f27726344d13ad3a5592a64d5c46596d6f47d6acd1b3ea99`,
and `426fe0bdae44ecf28fc75d0e9976a4b82824deeefa38bac662ab0fe710cd8575`.
It again reports all 999 closed leaves complete and the 30 open leaves
incomplete, so both top-level UNSAT flags remain false. A guarded continuation
now descends from this boundary without accepting any larger UNKNOWN
frontier.

The immutable v5 bundle appends the audited round 36--135 segment and was
again replayed completely from scratch. Across five open segments the auditor
accepted 140 proof manifests and reconstructed 4,050 refined parents, ending
at state round 136 with 30 VERIFIED/30 UNKNOWN. It also reconstructed all 28
initial roots and the 32-node forest, and replayed the four closed segments to
their complete round-34 terminal. The v5 bundle, audit, and audit-log SHA-256
values are
`569139c00e91b5079ca19f53097b620fcee28972667f3a6f34e0bed8311a227f`,
`1705760ea4d99fe553ed0f9baab47eba73fdb44d372dfce4260fb9347dff5aa7`,
and `41ada8342153701e43dd3f1a0d8dcd89aeaff1909475e03fd62add61ea84c3d8`.
Its closed chain is complete, its open chain is incomplete, and both
`exact_edge_cube_augmentations_unsat` and `mother_formula_unsat` remain false.

Three direct open-frontier controls found no shortcut at the tested depths.
iGlucose at 300 seconds closed 0/30 original forest-open parents. After the
certified binary chain had descended to its exact round-20 30-parent
frontier, direct 120-second CaDiCaL and 300-second iGlucose retries again
closed 0/30, with no SAT result. Their manifest SHA-256 values are
`a4ded95af63fc7d6521d0aa09e7237a6af820fa2c150d16e3a0ffe11fa23a882`,
`267cbded321f70af732cf390e0f57d657016a99590dea0879a65d2817aea5b1d`,
and `22d027adf122502bede3173564f21bdeb58152520bfa35989e98eee1878c991e`.
The quick-eight-second chain remains preferable and has continued with exactly
30 UNKNOWN branches; these three partial manifests are negative telemetry,
not UNSAT certificates.

### Materialized leaf certificates

A second recovery route no longer depends on completing or replaying one
multi-gigabyte live proof prefix. `tools/export_proof_forest.py` takes one
byte snapshot of a unified DFS table and reconstructs both every terminal
UNSAT leaf and every still-open node. `tools/audit_proof_forest.py` rebuilds
that forest from the snapshot and independently calls the Boolean DPLL cover
checker on every original root's terminal-leaf refinement. The original cube
family can additionally be reduced by the replayable sibling-merge
certificate in `tools/certify_binary_cube_cover.py`. These two checks separate
the purely Boolean cover obligation from SAT solving.

`tools/prove_materialized_cubes.py` appends each cube as DIMACS unit clauses,
runs an external solver, and retains an UNSAT result only after `drat-trim`
accepts that exact augmented formula and proof. Its manifest binds the mother
formula, cube file, ordered cube, augmented CNF, solver and checker binaries,
proof, and checker log by SHA-256. `tools/audit_materialized_cube_proofs.py`
then recreates every augmented CNF and replays every proof again. UNKNOWN is a
first-class partial result and SAT stops frontier processing. A two-leaf
Kissat/DRAT smoke proof passes both checker invocations. After the staged,
chain-audit, and compact-proof additions, the complete ARM Python suite has
113 passing tests.

The first real snapshots apply this route to the two no-symmetry H100/J132
fixed-pair streams. They contain 16,750 closed plus four open leaves for
J297775, and 16,756 closed plus three open leaves for J326185. Their forest
manifest hashes are respectively
`c45e0f4c415e94cc499e3120a55146bd7064bae9588a95fb16cea79be31ba013`
and
`f374ed7fab802b4432e7b28f83c0de82c9c1f1cbedb79107bdaad30ead64ea7c`.
Both per-root refinement audits pass. The two 16,384-root initial families
independently reduce to the empty cube in exactly 16,383 sibling merges; the
certificate hashes are
`9751264998b8b290547d52f5cea2538d8f7954b48aad8132bebcab56a25dcc6c`
and
`ee1baddd1e031afbc2f15ba19c245440b5b2b010ee73d890a6a234933d0ba8e8`.

Materializing the seven open cubes exposed a useful conquer improvement.
Default and UNSAT Kissat both closed two of four J297775 cubes and one of
three J326185 cubes within 120 seconds, with no SAT result. Actual proof-mode
reruns reproduced those closures and passed an independent replay. The four
remaining hard parents were replaced by checked complementary child pairs;
each pair again had one child prove UNSAT in about 0.023 seconds while the
other remained UNKNOWN at 120 seconds. Early 20- and 60-second chain rounds
confirmed that this one-easy/one-hard pattern persists: a uniform long budget
mostly waits on the single hard continuation at every level.

`tools/run_materialized_proof_chain.py` therefore supports a staged conquer
policy. It first gives every child two seconds and applies the long budget
only when both siblings of one parent remain UNKNOWN. The initial long budget
was 60 seconds. A proof-mode 120-second rerun on eight J297775 round-37
residuals closed one additional cube at 96.98 seconds; that cube's sibling was
already proved, so the extra closure removes a whole parent. All four chains
therefore switched at audited boundaries to a 120-second long budget. The new
`tools/compose_materialized_cube_proofs.py` accepts only an ordered subsequence
of primary UNKNOWN rows, binds both source manifests by SHA-256, carries the
replacement indices, and hard-links or copies the selected proof artifacts
into a fresh combined manifest. Both stage manifests and the composition are
independently replayed. A real two-cube ARM smoke combined one short-stage
proof with one retry proof and the final independent `drat-trim` replay
verified both leaves.

The staged chain also has an optional cross-solver fallback. After the normal
quick and long passes are composed, `--fallback-solver` receives only sibling
pairs that are still jointly UNKNOWN; its independently audited results are
composed into the canonical `rXXXX-proofs` manifest, including per-result
solver/hash overrides. A real one-round J297775 smoke forced all six children
through this path with tiny budgets, then the whole-chain auditor reconstructed
the three complementary parent splits and accepted the final six-row manifest.
The audit SHA-256 is
`5b205021244a03e71af5c3387ea9317e38f9191ed81361e11925dada661715b2`.
The option is disabled by default, so earlier chain invocations and artifacts
retain their exact behavior.

Proof storage can be reduced without weakening replay. With
`--compact-proof`, the producer asks `drat-trim -C -l` for a binary core,
retains it only when it is smaller than the solver proof, and immediately
replays the retained core. The manifest binds the source proof size/hash and
the compaction log; the independent auditor and UNKNOWN-only composer also
check and carry that log. On a real J297775 leaf this reduced 31,254,828 bytes
to 15,791,261 bytes, and both producer replay and a separate auditor returned
`VERIFIED`. Tiny five-byte smoke proofs correctly retained their originals.
The producer also accepts `--scratch-directory`: augmented CNFs, raw DRAT,
and compact candidates live in that temporary filesystem, while only the
checked retained proof is atomically published to the output directory.
Cross-filesystem publication uses a uniquely named partial copy followed by
an atomic rename. A `/dev/shm` ARM smoke left no temporary residue and its two
published proofs passed a separate replay; this avoids multi-gigabyte
transient growth on the 251-GiB persistent volume.

`tools/audit_materialized_proof_chain.py` provides a separate whole-chain
replay. It byte-snapshots `state.json`, audits every proof manifest, rebuilds
each exact ordered UNKNOWN frontier, checks every complementary split and its
hash-bound refinement manifest, and requires the next proof manifest to bind
that exact child file. The leaf auditor also verifies the manifest's solver
and checker binary hashes and requires the supplied checker binary to match.
A live J326185 open-chain replay accepted 44 proof manifests and 43 refinement
rounds through a round-45 state snapshot, covering 188 refined parents. Its
terminal manifest remained partial with seven UNKNOWN children; the audit
manifest hash is
`ec1c1561a1a2b628031c2b1c3adee5cbc1ca8b32b4000632cb173da2963508bc`.

`tools/audit_fixed_pair_proof_bundle.py` closes the remaining certificate-
composition gap above those chains. A bundle names the fixed-pair formula,
the initial sibling-merge cover, the proof-forest snapshot, the closed-leaf
chain, and the initial/refined open-leaf chain. The auditor independently
replays the 16,383 initial merges and every per-root forest cover, rebuilds the
exact open UNKNOWN frontier and its complementary refinement, invokes the
whole-chain auditor for both leaf families, and replays every retained DRAT
proof with the supplied checker. It emits `fixed_pair_unsat: true` only when
both terminal chains are complete. Static real-data audits already accept all
path/hash/count bindings for J297775 and J326185; these structural audits are
not a substitute for the final leaf-proof replay while the chains remain
partial.

Long chains may change solver policy without discarding their certified
prefix. The chain auditor accepts an immutable `state.json` snapshot, and the
bundle auditor joins consecutive segments by terminal-manifest hash. It also
accepts an independently replayed exact-cube retry at a boundary when the
formula and complete ordered cube-family binding are identical. Cross-solver
composition retains the primary manifest's default solver and records a
per-result solver binary/hash override for every replacement from another
solver; the leaf auditor checks those overrides before replaying the proof.
`tools/compose_materialized_cube_portfolio.py` extends this to any number of
identical cube-family runs. It rejects SAT, chooses the smallest verified
proof per cube, binds every source manifest and selected source index, and
keeps all per-solver provenance needed by the leaf auditor. A real eight-cube
ARM composition retained three proofs and a separate replay accepted all
three.
The immutable-state path was exercised on the J297775 pre-switch snapshot:
54 manifests and 53 refinement rounds through round 55 were replayed, covering
443 refined parents and ending at the recorded 17 VERIFIED/17 UNKNOWN
manifest. The audit hash is
`944477bfab2b93d3025234441e81573b1734072e4466a4ec0bace99bde57e295`.

`tools/audit_order45_strata_proof_bundle.py` applies the same composition
discipline to an exact-edge stratum. It hash-binds the mother CNF to the
edge-strata formula manifest, requires the ordered forest roots to equal that
manifest's four-literal cubes, reconstructs the forest cover, and audits both
the closed- and open-leaf proof chains. Its strongest possible output is
deliberately formula-relative: every exact-edge cube augmentation is UNSAT.
It always leaves `mother_formula_unsat` false until the separate, kernel-
checked exact-counter/cube bridge is connected. The materialized producer now
also checkpoints successful workers in completion order, so one slow earlier
cube cannot hide already checked proofs in the progress manifest. The chain
driver now also audits a seed that already claims complete UNSAT before it can
accept that claim. Within one uninterrupted driver it remembers the manifest
just replayed at the end of the prior round and does not replay those same
bytes again as the next seed; a resumed process still starts with an
independent seed replay. The optional `--stop-on-frontier-growth` guard now
audits and retains a candidate round but refuses to advance authoritative
`state.json` when its UNKNOWN count exceeds the parent count; it writes a
separate `halted.json` diagnosis instead. This turns the previous manual
best-frontier freezes into a deterministic production policy. The complete
ARM Python suite passes 126/126 after these additions.

A 120-second ARM portfolio on frozen hard frontiers found CaDiCaL stronger
than default Kissat on these residuals. It closed 3/17 J297775 open parents,
3/8 J326185 closed parents, and 1/10 J326185 open parents in the first
telemetry snapshot. Exact retries at later certified boundaries closed 3/8
J326185 closed parents and 1/12 J326185 open parents; their cross-solver
combined manifests independently replayed as 11 VERIFIED plus 5 UNKNOWN and
11 VERIFIED plus 11 UNKNOWN respectively. The continuation chains now start
from those smaller frontiers. An exact 17-parent J297775 open retry closed
none, and neither CaDiCaL nor Kissat `--unsat` closed either of two later
J297775 closed parents. Their already certified refinement continuations were
therefore resumed.
At round 139, four additional random seeds for each solver also left both
J297775 closed parents UNKNOWN at 120 seconds. All transient CNFs and raw DRAT
were removed from RAM scratch; the continuous chain then resumed from the
same state with CaDiCaL and scratch enabled.
At J326185 closed round 151, three seeds of both CaDiCaL and Kissat `--unsat`
likewise closed none of five parents at 120 seconds. The CaDiCaL continuation
later widened to nine parents and was frozen at round 156; default Kissat now
continues the identical ordered frontier from the round-155 manifest. An
independent immutable-state replay accepted that entire CaDiCaL segment (44
manifests, 43 refinements, and 231 refined parents) and matched the exact
9 VERIFIED/9 UNKNOWN terminal manifest. Its audit SHA-256 is
`d9ac7d0b98198f589c37c3a80fd6f6db2c06d9aa86ae485c1132e3a7245d8b66`.
A separate 120-second CaDiCaL retry closed none of the 23 J326185 open parents
at round 80. The J297775 and J326185 open continuations were subsequently
frozen at rounds 69 and 82 and restarted from their exact terminal manifests
with `/dev/shm` scratch. Thus all four active residual chains now publish only
checked compact proofs to persistent storage.
Independent replay accepted both frozen open segments. The J297775 round
55--69 segment contains 15 manifests, 14 refinements, and 276 refined parents,
ending at 23 VERIFIED/23 UNKNOWN; its audit SHA-256 is
`bbfb731c92c55a6b11395470ff858e43de505b5d0001eef3844e92829fedaa82`.
The J326185 round 66--82 segment contains 17 manifests, 16 refinements, and 273
refined parents with the same terminal counts; its audit SHA-256 is
`e591393b15c43ab26ea7fccb9d9fd801b6ae6c6de48cf3549a90dc011a965cb7`.

The pinned CnC checkout now also builds certified iGlucose. A small audited
source patch makes its Linux FPU setup portable to ARM, returns conventional
SAT/UNSAT status codes, maps the second positional path to DRUP output, and
emits the empty clause when preprocessing alone finds a contradiction. This
lets `prove_materialized_cubes.py` hash-bind the actual solver binary rather
than an adapter. A two-cube materialized smoke produced and independently
replayed both compact proofs. On the J297775 closed round-178 frontier, seven
other 300-second configurations (six CaDiCaL phase/search variants and Kissat
`--sat`) nevertheless closed none of the two parents, and certified iGlucose
also left both UNKNOWN. A raw-proof-first 1,800-second iGlucose follow-up still
closed neither parent. On a ten-parent J326185 round-187 snapshot, iGlucose
instead produced three compact proofs in about 85, 147, and 175 seconds. Each
passed a separate replay; cross-solver composition raised the exact 18-row
boundary manifest from 8 VERIFIED/10 UNKNOWN to 11/7, and an independent audit
accepted all eleven retained proofs. The closed chain was restarted from this
smaller certified frontier, abandoning only later exploratory rounds that were
not part of the frozen bundle prefix. The frozen Kissat prefix from rounds
156--187 was itself independently replayed: 32 manifests, 31 refinements, and
279 refined parents led to the exact 8 VERIFIED/10 UNKNOWN terminal manifest.
Its audit SHA-256 is
`e18d93f15b5ae60b8475ef6b79b0b69a6e4edb22d84825133ddd20a716137b8a`.

The next frozen-frontier probes made the solver-diversity gain more concrete.
Certified iGlucose closed two of the 36 J297775 open parents at round 85 in
about 185 and 295 seconds. Both compact proofs passed a separate replay, and
UNKNOWN-only composition changed the exact 66-row boundary from 30
VERIFIED/36 UNKNOWN to 32/34. A full replay accepted the combined manifest.
Its SHA-256 is
`cfd8bdca4029691c641c5e225b4e0f1eb3aed4b15c750ed23645f232aef9a152`.
The preceding CaDiCaL scratch segment was also independently reconstructed:
rounds 69--85 contain 17 proof manifests, 16 refinements, and 415 refined
parents, ending at the exact 30/36 source manifest. Its audit SHA-256 is
`180f084eb10847edd9cd9cb80850cdb0117f3cbd6c65d0d7654ae1b87d30e2cf`.
The first open-chain continuation started from that smaller round-85 boundary.
A longer raw-proof-first 900-second iGlucose pass on its remaining 34 parents
then closed four more, at about 517, 680, 686, and 707 seconds. The producer
replayed all four raw proofs, a separate leaf audit accepted them, and a full
66-row replay accepted the composed 36 VERIFIED/30 UNKNOWN boundary. The
producer and combined manifest SHA-256 values are
`ee81b6111c334a74e2e8e6a58fbfe3704d4448ac26c7f9bafe894d982b945f38`
and
`f90116b8ca1c50972d6c1fdee2821f0b8619cb85a6c9e20a943b3c452cab8cf7`;
the full replay log SHA-256 is
`5ce37f367304749e9e881593a44d5d8e8dd7307660136fe0391a62b7ca22d603`.
Only after that replay passed was the 32/34 continuation stopped and a new
CaDiCaL chain started from the stronger 36/30 seed.

A second, 1,800-second iGlucose retry on those exact 30 residual parents
closed three more, at about 1,005, 1,261, and 1,667 seconds. The retained
proofs are 582,216,081, 805,725,591, and 740,793,205 bytes. A separate 30-row
leaf replay accepted all three; UNKNOWN-only composition produced an exact
39 VERIFIED/27 UNKNOWN 66-row boundary, and a separate full replay accepted
all thirty-nine proofs. The producer/combined manifest hashes are
`c15e7b84b487516a96a13b297138eadc0341cb019fca49bcdcf11575853b534f`
and `60ece36ce95a2dd92158a5a960826504e0732d62df59b14af8db2b1c626ab6ff`;
the leaf/full audit-log hashes are
`c6fcce0b33de3ecd3707588c013ee0c6557cfd3a4754fd8da529efc737fdd3b1`
and `450cc84efca8e16974cbd758a5cec2d2197a91a7c553c9b0e604949ae55d1aa9`.
After both audits passed, the bundle switched to this boundary and a new
CaDiCaL quick-four-second continuation started from round 85.

In contrast, a 300-second pass closed none of the 31 J326185 open parents
frozen at round 96. A
raw-proof-first 900-second pass then closed six, at about 320, 563, 578, 608,
668, and 688 seconds. Producer replay and a separate 31-row leaf audit
accepted all six. The preceding CaDiCaL scratch segment from rounds 82--96
also passed whole-chain replay: 15 manifests, 14 refinements, and 365 parents
end at the exact 31 VERIFIED/31 UNKNOWN source boundary. Its audit SHA-256 is
`429cd800fa4a293f8963c6ef383e88a67d841d8bc5fb77e1c765807156db649a`.
UNKNOWN-only composition and a full 62-row replay accepted the stronger 37/25
boundary. The producer and combined manifest SHA-256 values are
`423e81201832bd03e6865912fa6f720d6edf9bf1e3e273052500f038dfce9025`
and
`c2c8c5bf840bfb44d7dcdd024e065d40d4e1af3b3290d2a0646ac5fa25de363d`;
the full replay log SHA-256 is
`d77efa494d0707c340082ebf55868311691d156ef5ed33227883ac35c51e705f`.
Only after both audits passed was the exploratory round-120 process group
terminated and a fresh CaDiCaL continuation started from round 96.

A second, 1,800-second iGlucose retry on the exact 25 residual parents closed
three more, at about 883, 1,572, and 1,790 seconds, retaining 409,486,315-,
638,466,757-, and 912,750,168-byte proofs. A separate 25-row leaf replay
accepted all three. UNKNOWN-only composition produced an exact
40 VERIFIED/22 UNKNOWN 62-row boundary, and a separate full replay accepted
all forty retained proofs. The producer/combined manifest hashes are
`e857457accb159e71848759a1bb59e2f81733a78b801bd799b2ca2eaf00babac`
and `6cceea7387ac18fbcf34f16ec2c63243e47164ebbd9e28067154c366097fe72e`;
the leaf/full audit-log hashes are
`68814f573f1f159d821dfc559b4d44ae63ee5d327c00a94c6456a4eaf2a9f254`
and `5d140fd13d70e4c868be355b29082f12ec86d1de351fef2180dc7a9a64ab8b07`.
Only after both audits passed was the bundle switched to this boundary and a
new CaDiCaL quick-four-second continuation started from round 96.

On the seven J326185 closed parents left by the first round-187 composition,
a 900-second iGlucose pass produced three more compact proofs at about 525,
603, and 897 seconds. The producer and a separate auditor replayed all three;
UNKNOWN-only composition raised the exact 18-row boundary to 14 VERIFIED/4
UNKNOWN, and a full replay accepted all fourteen retained proofs. The closed
manifest SHA-256 is
`2db59c0c96503cad02ce3ac083496c650d2a94b6b3d0952e6e86a9ce0a45a038`.
This run also showed that proof compaction, rather than SAT search, can
dominate completion latency: the largest 479 MB raw DRUP took roughly fifteen
minutes to compact before a 163 MB proof could be replayed. Longer follow-up
probes therefore keep raw proofs for immediate checking and defer storage
compaction.

A raw-proof-first 1,800-second pass on the four remaining parents closed two
more, at about 916 and 1,798 seconds, retaining 546 MB and 838 MB proofs.
Producer replay and a separate four-row leaf audit accepted both. UNKNOWN-only
composition and full 18-row replay accepted the exact 16 VERIFIED/2 UNKNOWN
boundary. The producer and combined manifest SHA-256 values are
`a6c98ae97395ceb7e216fd75b2176502a86ddd7594f55e60bf0016a5e3e4550c`
and
`72fc2574e528f08cd22fd4b54378357edf5d2ca210217df527476a4a11feafb1`;
the full replay log SHA-256 is
`1234a6c66e9d2890cdae7a8e29d542a80a12dad98576bf758713a0566f80cc06`.
Only after both audits passed was the 14/4 exploratory continuation stopped
and a fresh Kissat chain started from the stronger round-187 seed.

A production-shaped fallback pilot at J326185 closed round 202 advanced one
round to an 8 VERIFIED/8 UNKNOWN manifest without invoking iGlucose: the
primary Kissat stage solved one side of every jointly hard sibling pair, so no
pair met the fallback trigger. This validates the trigger semantics but gives
no frontier reduction beyond the ordinary staged round.

The J326185 closed-leaf batch verified 16,746 of 16,756 leaves and left ten
UNKNOWN, with all 16,746 proofs accepted by a separate 48-way replay. Its
J297775 counterpart verified 16,734 of 16,750 leaves and left 16 UNKNOWN; a
separate 48-way replay accepted all 16,734 retained proofs. Both residual
chains and both open chains are still running. Therefore neither fixed-pair
formula, their local edge stratum, nor the order-45 theorem is claimed closed
here.

At the exact J297775 round-339 boundary, a raw-proof-first 1,800-second
iGlucose retry closed two of six residual parents in 550.49 and 1,335.01
seconds. The retained proofs are 374,277,823 and 621,049,922 bytes. A separate
six-row leaf replay accepted both, UNKNOWN-only composition produced an exact
8 VERIFIED/4 UNKNOWN twelve-row manifest, and a separate full replay accepted
all eight retained proofs. The producer and combined manifest SHA-256 values
are `f603f4f7c725621e965260add3ca16751a905fd0e9e0a6b5144e2486d2429c43`
and `e627a6ea3a1f3df4efa7fec7eb1286e788c3dd8c7cc45470eebe600906b7121e`;
the leaf and full audit-log hashes are
`9c4b78c2fe4255cb49d5027d8b9c5d5783d2da2ae2f6cd2ac8f05a44dba666c4`
and `ec04b319556d040a1c953ca2fb5302c3969879645dd6fb8000483953be4be0a2`.
The former continuous chain was recoverably frozen at round 386 with twelve
UNKNOWN parents. Only after both new audits passed did a fresh CaDiCaL chain
start from the smaller round-339 boundary; the older artifacts remain intact.

That replacement chain held four residuals through the exact round-345
boundary before later exploratory rounds widened. A certified 1,800-second
iGlucose retry on those four parents proved two in 1,075.50 and 1,205.46
seconds; the retained compact proofs are 209,856,662 and 215,556,817 bytes.
The producer manifest is 2 VERIFIED/2 UNKNOWN and has SHA-256
`fe2481b452687e03b01072474902009777973f7524038039af73c0f00ef18636`.
A separate four-row leaf replay accepted both proofs, with log SHA-256
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`.
UNKNOWN-only composition with the exact round-344 4/4 manifest produced an
eight-row 6 VERIFIED/2 UNKNOWN boundary. Its manifest SHA-256 is
`64f5bc201f947385f7c48b9566238b1ab2302e5a28847044ed299353e0f7b91d`,
and a separate replay accepted all six proofs with log SHA-256
`8a1e1f0288ea43b3a5e0fe29bee1385fd06dec13c8fc87081e7931f68012b81f`.
Only after both audits passed did the fixed-pair bundle append this stronger
seed and start a frontier-growth-guarded continuation from round 345. Two
closed-side residuals remain, so this is not a fixed-pair UNSAT result.

At the exact J326185 round-187 boundary, a 3,600-second iGlucose retry closed
one of the two remaining parents in 2,332.10 seconds; its checked proof is
857,920,874 bytes, while the other parent timed out. A separate two-row leaf
replay accepted the new proof. UNKNOWN-only composition produced an exact
17 VERIFIED/1 UNKNOWN eighteen-row manifest, and its full independent replay
accepted all seventeen proofs. The producer/combined manifest hashes are
`b1a2dc7182de35ecc6d6e2fd361df7a783526c7f8909aceba40eba400ee1af22`
and `f281a9b022742397cb3a066edbdedefa68887f30e226a638d991032390de00c2`;
the leaf/full audit-log hashes are
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`
and `19076a8feb7919b1cabe73e1fe2d4b0ba6734023608f22b8d0056d9198652ab7`.
After both audits passed, the stopped 16/2 Kissat continuation was superseded
in the bundle by a CaDiCaL quick-four-second chain from the 17/1 boundary.

The newly adopted fixed-pair continuations were then frozen at their last
non-growing states and replayed independently. J326185 closed maintained one
UNKNOWN parent for 55 consecutive rounds: the round-187--242 audit accepted
56 manifests, 55 complementary refinements, and 55 refined parents, ending
at the exact 1 VERIFIED/1 UNKNOWN round-241 manifest. Its final-manifest,
audit, and audit-log SHA-256 values are
`8caa1289ba9ce8263465be9afbb9985c7d07d19aee27f0d431ad86145969f31c`,
`72eb8e391c10487fe44c37e7f95a841bc67253d8538520f125e7116b51b551fd`,
and `0fa07f9e317396a1202133564546446cc31c20f05595ca39b60560158d44f91e`.
The next candidate contained two UNKNOWN children and was not adopted.

J326185 open made one non-growing round from its 40/22 seed. Independent
replay accepted the two manifests and the complementary split of all 22
parents, ending at 22 VERIFIED/22 UNKNOWN on deeper cubes. Its final-manifest,
audit, and audit-log hashes are
`a32baacf321f26b62cac1555282f5da63a607e2822a9998c2a0d398299a58cf5`,
`68fe4e54cb5a19316aee5cc74cefbf955e4cdc440cf9863529d39b32e8e5e7af`,
and `51fa8b5f26b9f2d7e4cacee94c6b86ebbce5b68ed8cf5f864dee470ddb1032e1`.
A guarded next round stopped at 26 UNKNOWN without advancing its state.
J297775 open similarly maintained 27 UNKNOWN parents for two rounds; its
three-manifest audit accepted 54 complementary parent refinements and ended
at 27 VERIFIED/27 UNKNOWN. The final-manifest, audit, and audit-log hashes are
`c44d6c8e9e7a872a103d273ad9e2fde2c1ab722e13146d155a344f2290dd55ec`,
`a59b1e6746173e4aaae60e5010a67ae1b3daca6da1c61b89cd799da17473615d`,
and `be9d166d056db9b97c9b94be8804ac9ec33db74664b5351fccd2f329f605197e`.
Its following unguarded candidate widened to 32 and was excluded. These
deeper equal-cardinality boundaries are now the exact sources for long
certified iGlucose retries; no expanded frontier is part of either bundle.

Those exact long retries materially strengthened both fixed-pair bundles.
For the single J326185 closed parent at round 242, Kissat returned UNSAT in
1,208.84 seconds and retained a 203,653,562-byte compact proof with SHA-256
`a97fc60c5124836e7f70bb2951c20f2772901f3b02032d397736a0eb8bc11e49`.
The producer manifest has SHA-256
`39b1f19b76051b82d71eb0258187d5f618aa87736a09a4dfe144510c63d988e8`.
A separate one-row replay accepted the proof. UNKNOWN-only composition with
the exact round-241 manifest produced a 2 VERIFIED/0 UNKNOWN manifest with
SHA-256
`3e0d5d8183c75a020ada6abadba66a121973e8dd9bbb16a788ecf2db34b308f0`,
and an independent full replay accepted both rows. A terminal seed replay
then recorded `complete=true` at round 242. Its state SHA-256 is
`717a938c01abae380141078b0f2db422bfb8e45084dd506b3f78eeab350a026a`.

The two J297775 closed parents at round 345 were both solved by Kissat in
1,822.32 and 1,385.11 seconds. Their retained compact proofs are 225,014,063
and 238,588,047 bytes. The 2/0 producer manifest has SHA-256
`52c7733f9278afde3263a13b491892a6681982221c4e4dc6ca79aac7a45e5749`;
a separate two-row replay accepted both. Composition with the already audited
6/2 eight-row boundary produced 8 VERIFIED/0 UNKNOWN, with manifest SHA-256
`a0b7ed65f8456e7a7a8ad7806e0208aba172d0157a3dae6a7631215a7012971a`.
Its full replay log has SHA-256
`23834eff3d3e461574658b52af7a55ac633c959eb9a820a1f8409bd648544b57`,
and the terminal chain recorded `complete=true` at round 345. Consequently
the closed proof-forest side is complete for each fixed-pair formula. This is
not a fixed-pair UNSAT result because each open side remains incomplete.

Solver-diverse 3,600-second passes reduced those open sides. On the exact 27
J297775 parents, certified iGlucose proved 5 and Kissat proved 12; the latter
set subsumes the former. Their smallest-proof portfolio is 12 VERIFIED/15
UNKNOWN and has manifest SHA-256
`2db3854fb5e065255ace83e662f9971fbf53ac938eeb7650dac7dd52ec32fe13`.
A separate replay accepted all twelve proofs. Composition with the round-86
manifest produced 39 VERIFIED/15 UNKNOWN over 54 rows, with manifest and
full-audit-log SHA-256 values
`d93df6413297305364cf858c9017e3138770bbef2837c3b0a3c660e474db5e3c`
and
`1ae713008e452d49156770d4354657c98373fd5959130129e4edf22608b79dae`.
Its guarded next round widened 15 to 16 and was rejected, leaving the
15-parent boundary authoritative.
On the exact 22 J326185 parents, iGlucose proved one and Kissat proved eight;
their portfolio is 8 VERIFIED/14 UNKNOWN with manifest SHA-256
`984969a1364b061590f00a8eb6d22a1cd9a3b1325e44c862106cec92cb087457`.
Composition produced 30 VERIFIED/14 UNKNOWN over 44 rows, with manifest and
full-audit-log SHA-256 values
`71653f2e3e0e2a217d27dbda497ba2181db9e7f1efd3d1c8448788ce0656f582`
and
`36819a518340a35cf88b8a8b40bdd4d6e9989ad3ba7e7f51f7d379e0d2324e11`.
A guarded next J326185 round widened 14 to 17 and was rejected, leaving the
14-parent boundary authoritative.

The current J297775 and J326185 fixed-pair bundle files have SHA-256 values
`879398311418464529fcaf0757c760ca55ef5e0d189f6760fd2485a93d190dfd`
and
`87a98e744cc8f03d381cf188da98b73a6f024a379b86a3b8f83ba15defa541c2`.
Fresh from-scratch bundle audits now replay every certificate layer, not only
the newly appended segments. For each bundle the auditor reconstructs the
16,384-cube initial cover, the proof-forest root refinements, every retained
DRAT proof, every binary chain refinement, and each exact-cube cross-segment
boundary. The J297775 audit reconstructed a 16,478-node forest, replayed 348
closed and 91 open manifests across four and six segments, and ended with a
complete 8/0 closed side at round 345 and an incomplete 39/15 open side at
round 87. Its audit-manifest and log SHA-256 values are
`3db3dd861f26a47f55be9f97030e33dbfe3d34e981679fde17767a9b05027518`
and
`00bc9d39e1cf52431fb51c3074d3a4c5c43c050083992c6b9ad3b91e730886e0`.
The J326185 audit reconstructed a 16,464-node forest, replayed 246 closed and
100 open manifests across five and five segments, and ended with a complete
2/0 closed side at round 242 and an incomplete 30/14 open side at round 97.
Its audit-manifest and log SHA-256 values are
`142d1320a1ec0bdcc3904ea41da7ea181f52b2a726eea19274f6e27ad59e4a3a`
and
`d7856f89f8b3722e8e093f1db827e8a80777f57613169b5142cfa8c10d85228b`.
Both audit manifests deliberately report `fixed_pair_unsat=false`: the
authoritative open residual counts remain 15 and 14, respectively.

An exact-frontier CaDiCaL control then tested whether the remaining hardness
was merely a solver-profile artifact. The exporter bound the 15 J297775 and
14 J326185 cubes to composed source manifests with SHA-256 values
`d93df6413297305364cf858c9017e3138770bbef2837c3b0a3c660e474db5e3c`
and
`71653f2e3e0e2a217d27dbda497ba2181db9e7f1efd3d1c8448788ce0656f582`.
CaDiCaL 2.1.2 ran every cube for 600 seconds under its default and `--unsat`
profiles and under `--stabilizeonly=true --walk=false --seed=1`. Every one of
the six batches returned zero SAT, zero UNSAT, and 15/14 UNKNOWN. The stable
telemetry manifest
`data/order45-final-open-cadical-profile-600.json` has SHA-256
`7ab4f07526eb8732e65e6b8ca9288f82983cbf4dddf800752e32f5442b781948`
and binds the solver, formulas, frontier files, arguments, TSV hashes, and
timing summaries. This excludes a cheap CaDiCaL-profile shortcut at the tested
budget; it is negative search telemetry, not an UNSAT certificate.

A structural-split pilot does not support replacing lookahead by a fixed
cross-edge order. For one hash-bound J297775 hard parent, splitting on the
first unassigned H--J variable (variable 1 in the primary range 1--480) left
both children UNKNOWN at 120 seconds. The auxiliary-heavy CaDiCaL lookahead
splits are retained because their repeated one-easy/one-hard behavior is much
more useful for certified descent.

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

The ARM node has 64 logical CPUs and 244 GiB RAM. After retaining the current
materialized proofs it has about 32 GiB free disk, so proof-log storage is now
the tighter operational margin. It remains adequate for parallel pilots,
catalog scans, cube discovery, and certificate replay. More raw cores would
not fix the present bottleneck:
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
