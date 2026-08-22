# Order-45 upper-bound program

Updated: 2026-08-21

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

Repeated full-bundle replay is no longer required after an immutable baseline
has been accepted.  `tools/audit_materialized_proof_chain_bundle_extension.py`
binds the old bundle and its audit by SHA-256, requires the new bundle to be an
exact segment-prefix extension, independently replays every appended segment,
and checks the old-terminal/new-seed boundary with the same identical-manifest,
exact-cube retry, or rescued-refinement rules as the full auditor.  Its output
explicitly remains dependent on the named baseline audit; it does not claim to
have replayed the prefix again.  An extension audit can itself be the next
hash-bound baseline, so later checkpoints replay only their genuinely new
suffix rather than every suffix since the last full audit.  The companion
`tools/audit_strengthened_parent_chain_bundle_extension.py` similarly reuses
the hash-bound, already checked strengthening and false-polarity backbone
layer only when the parent metadata is unchanged and the chain extension is
bound to the exact old and new chain bundles.  Parent extensions are likewise
recursive, retaining the original full strengthening/backbone audit as the
root of the hash chain.  A bundle may append segments to only one case; the
other case's exact terminal summary is carried forward without replay.
Prefix mutation, round gaps,
incomplete base backbone proofs, and inconsistent terminal counts are covered
by rejection tests.  When an accepted retry is composed into a fresh chain
directory, `compose_materialized_cube_proofs.py --cubes` can rebind its output
to the chain-local children file only after checking the identical SHA-256 and
ordered cube family.  The complete Python suite passes 178 tests after these
additions.

The first production extension audit binds the accepted v16 chain bundle and
full audit (`7bd3c89b...6a51` / `cfeee700...6f61`) to v18 bundle
`64721cdf...5d5c`.  It independently replays three appended J297 segments and
two appended J326 segments, reaching states 602 and 628; its JSON/log hashes
are `d85da4f0...ea4e` / `8e54486d...a5d`.  The corresponding parent extension
audit (`405303d9...5a79`) retains the original full strengthening/backbone
audit as its hash root and reports two and one remaining UNKNOWN cubes.  The
separate v17 full replay also passed with JSON/log hashes
`4e02e9e6...6820` / `d18c1d2d...e93b`; it is a useful whole-prefix cross-check
through states 600 and 624, but no longer needs a duplicate full parent replay.
The next recursive extension to v19 replays only two appended J297 segments
and carries J326 unchanged.  Its chain JSON/log hashes are
`4e438396...a6d8` / `f0ec261d...9154`; the recursive parent-extension hash is
`5515122f...79bb`.  The resulting hash chain ends at J297 state 606 with two
UNKNOWN cubes and J326 state 628 with one UNKNOWN cube.
The v19-to-v20 extension then carries J297 unchanged and independently
replays one J326 segment through state 629.  Its chain/parent extension hashes
are `cdbb6097...376c` / `9f472619...0001`; the terminal widths remain two and
one, respectively.

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

An independent MiniSat 2.2.1 control then ran the same exact 15/14-cube
frontiers for 600 seconds per cube. All 29 processes reached the time limit:
zero returned SAT, zero returned UNSAT, and all remained UNKNOWN. Lingeling
`bcj` was also built from the retained CnC source, but it exited immediately
with `watcher stack overflow` on both the base CNF and a J297775 cube reduced
by one CaDiCaL preprocessing round from 115,162 to 96,215 clauses. Those two
attempts are recorded as an incompatible solver error, not as UNKNOWN search
results. The hash-bound manifest
`data/order45-final-open-solver-diversity-600.json` has SHA-256
`9bc22be18b6ef73f4e3966e4c6a3e9cf11c8c26d64b07369b8de3de484c7bf6b`,
keeps these states separate, and again makes no UNSAT claim.

A complete primary-variable scan of the deepest J297775 residual then found
a structural alternative to another auxiliary-only split. Kissat tested both
polarities of all 480 H--J edge variables for five seconds and closed 23 of
the 960 children. The closed children occur on 23 distinct variables, so they
force the complementary primary literals
`-25..-36, 37, 38, 48, 97, 169, 193, 241, 337, 385, 409, 457` under that
194-literal parent cube. All 23 surviving sides remained UNKNOWN at 120
seconds, and adding all forced literals exposed no further five-second
backbone among the remaining 457 variables; the parent is therefore still
open.

The 23 false polarities were rerun in proof mode rather than retained as
search telemetry. Kissat emitted 4,082,217 bytes of raw DRAT, `drat-trim`
compacted them to 634,918 bytes, and an independent replay accepted all 23.
`tools/audit_primary_backbone_proofs.py` additionally checks that every
proved cube is exactly the same frontier parent plus one false primary
literal before invoking the materialized-proof auditor. The stable record is
`data/order45-j297-c0-primary-backbones.json`, SHA-256
`87e4a6b824db942beecac7498a635f04733dc71544fd5ae4b1573a022b3dbf98`;
it explicitly records `parent_cube_unsat=false`. These certified backbones
are a strengthening for the remaining search, not a refutation of the parent.

The same exhaustive primary scan on the deepest, 230-literal J326185
residual found 22 backbones. They are exactly the intersection of the J297775
set with variable 38 removed, giving a common fixed-pair pattern rather than
an isolated branching artifact. Their false polarities produced 3,415,134
raw DRAT bytes, compacted to 338,902 bytes, and both audit layers accepted
22/22. Again all surviving sides remained UNKNOWN at 120 seconds and the
strengthened scan found no additional five-second backbone. The stable record
`data/order45-j326-c0-primary-backbones.json` has SHA-256
`68ffa587f5349193e9ee72542518c63f08e0bedc85534eaaa3d74503ff0f9dbb`
and also reports `parent_cube_unsat=false`.

The two deepest-cube scans exposed a small set of 23 useful candidate edge
variables. Testing both polarities of those candidates across all 29 final
parents found 66 J297775 and 59 J326185 one-sided contradictions. Proof-mode
reruns and the frontier-level structural auditor accepted all 125. Adding all
discovered survivor literals to each of the 18 affected parents did not close
any of them in a 600-second Kissat `--unsat` pass: all 9/9 on each formula
remained UNKNOWN.

A broader one-second screen then tested both polarities of all 480 primary
variables on every remaining parent. It found another 193 false polarities
for J297775 and 178 for J326185, with no SAT result and no variable whose both
polarities were UNSAT. Proof-mode reruns independently verified all 371.
`drat-trim` reduced their 1,618,071 raw proof bytes to only 14,779 bytes,
showing that the resulting contradictions are essentially propagation-level
once the parent cube and false edge literal are units. Combined with the two
deepest-parent certificates, the exact final frontiers now carry 216 and 200
certified primary-edge backbone facts. They cover 14/15 J297775 parents and
13/14 J326185 parents; only final parent indices 14 and 13, respectively,
showed no backbone at the tested budget. The frontier-level auditor still
reports `frontier_unsat=false`: these facts strengthen and organize the open
search but do not reduce the authoritative 15/14 residual counts.
The combined stable record
`data/order45-final-frontier-primary-backbones.json` has SHA-256
`a5cf6d340adb421916356b7d815a3143fb958ed0a16d4ccddb07d1131e09018d`.

Two negative controls delimit what those facts buy by themselves. Adding every
certified backbone to all 13 affected nondeep J297775 parents and all 12
affected nondeep J326185 parents left every parent UNKNOWN under both default
and `--unsat` Kissat at 600 seconds. Conversely, rescanning both polarities of
all 480 primary variables for five seconds on the two parents that had no
one-second backbone (J297775 index 14 and J326185 index 13) closed none of
their 960 children. These are search controls, not certificates of
satisfiability or UNSAT.

The first column-star refinement gives a certified reduction even though it
does not yet close a parent. Final parent 1 in both formulas has the same 15
proved literals on variables congruent to 1 modulo 24. Only variables
`289, 361, 385, 433, 457` remain free in that 20-edge H--J column. A checked
32-leaf binary cover enumerates those five bits. Kissat closed exactly the
same leaf indices
`0..9, 12, 13, 16, 29, 31` in both formulas; proof-mode reruns and independent
materialized replay accepted all 15 proofs per formula. The retained compact
proofs occupy 43,788,436 bytes for J297775 and 39,255,366 bytes for J326185.
The other 17 leaves remain open, so `parent_cube_unsat=false` and the global
15/14 frontier count is unchanged; logically, the parent has been reduced to
those 17 explicitly listed subcases.

A fixed-order continuation was unhelpful. Both polarities of all 20 variables
in the adjacent J2 column were tested for five seconds on each of the 17 hard
leaves: all 680 children in each formula remained UNKNOWN. The next
continuation therefore uses CaDiCaL lookahead to choose an auxiliary split per
leaf and emits checked DRAT for closed sides. Stable metadata for the
strengthening controls, 32-leaf cover, 30 checked leaf proofs, and adjacent
column screen is in
`data/order45-final-parent1-column-star-refinement.json`.

A structural-split pilot does not support replacing lookahead by a fixed
cross-edge order. For one hash-bound J297775 hard parent, splitting on the
first unassigned H--J variable (variable 1 in the primary range 1--480) left
both children UNKNOWN at 120 seconds. The auxiliary-heavy CaDiCaL lookahead
splits are retained because their repeated one-easy/one-hard behavior is much
more useful for certified descent.

A strengthened single-root continuation is now the main parent-1 route. For
each fixed-pair formula it starts from row zero of the retained full-backbone
ICNF. The recorded lineage maps that row to fixed-pair parent index 1 and
lists the same 15 certified primary literals; the one-row root hashes are
`b8a29a9589e2715a7eaac21151875550eddc7855d7a3ef9c8fadc917e89ee912`
for J297775 and
`715b4a45b6397cec09c33dad258a0826e963a01b1a1e72a07a5b2ecd9ca753b9`
for J326185. This shares every subsequent auxiliary split across the whole
strengthened parent instead of maintaining 17 independent column-star leaves.

The chain runner retains its last authoritative state whenever a round would
increase the UNKNOWN frontier. The new growth-adoption record verifies both
parent and candidate proof schemas and counts, rejects SAT, and binds the halt,
parent manifest, and candidate manifest by SHA-256. The independent chain
auditor now checks those bindings against the reconstructed final transition.
At the first stable checkpoint, the J297775 frontier grew only
`1 -> 2 -> 3 -> 4 -> 5 -> 6` at state rounds 2, 9, 28, 74, and 132. Its six
segments replayed 138 proof manifests and 547 complementary parent splits.
The J326185 frontier grew `1 -> 2 -> 3 -> 4 -> 5` at state rounds 5, 37, 128,
and 132; its five segments replayed 137 manifests and 358 parent splits.
Both final manifests are partial, with six and five UNKNOWN cubes.

Those artifacts were copied out of tmpfs and relocated into
`build/order45-fixed-pairs/final-parent1-strengthened-single-root-lookahead-v1`.
The relocation pass rewrote 2,073 absolute paths and iteratively updated 353
dependent hash fields across 878 JSON documents, converging after two passes.
A fresh top-level replay from the stable paths checked the two source-lineage
bindings, every DRAT proof, every UNKNOWN export, every binary split, all
cross-segment boundaries, and all nine guarded growth adoptions. It reports
`all_cases_complete_unsat=false`; this is a much narrower certified residual,
not a proof of either parent or either fixed-pair formula. The bundle,
relocation record, stable audit manifest, and audit log SHA-256 values are
`f551668d83f535617914e4d8a54aa5c06a310fdab09f9e4f4c988750bdfa49a8`,
`2bbd39de58159db1b5ca67461c94befb3a86455018cff187dfd1e1549fecf1fb`,
`196b65e012a430d78918d34a5cf54f99f2a6a0fd1f0fcc179acc7c7cacd34564`,
and
`cb5d305802c3106294410be1f26350e03676f6f5af301acbe42187c415132518`.

A higher-level composition now connects that strengthened checkpoint back to
the original fixed-pair parent 1. It replays all 193 J297775 and 178 J326185
full-screen false-polarity DRAT proofs, selects the 15 facts whose lineage has
`parent_index=1`, and checks that strengthened row zero is byte-for-byte the
original parent cube followed by exactly those 15 survivor literals. It then
replays the complete chain bundle and requires identical formula, case,
strengthened-file, and lineage hashes at the join. The result certifies that
the original J297775/J326185 parent 1 cubes are reduced to six and five
explicit UNKNOWN descendants. It still reports `all_parents_unsat=false`;
the other 14/13 fixed-pair residuals and the global order-45 cover are
unaffected. The composition bundle, audit manifest, and audit log hashes are
`af11b0c438223d11e5c7ff2dddab5ca9e376b6cb107c24a0c70ecca0146e7e21`,
`a8be4397e902f50c261a8d2a9fab4199535cfc1786b509a6caa720c125d41d29`,
and
`5b1b72e5d146647fa98e2a2bbb3b2df99f22638457fc26d3a45790a4759c7c4a`.

A separately named rescued checkpoint extends that baseline without changing
its hashes. J297775 now has eight audited segments through state round 165:
173 proof manifests and 776 parent refinements leave eight UNKNOWN cubes.
For J326185, a 600-second Kissat exact-cube retry first closed one of the five
round-131 children, reducing the frontier to four. That width held through
round 161; a guarded round-162 growth returned it to five only after
CaDiCaL, Kissat, and iGlucose each left the responsible sibling pair 2/2
UNKNOWN at 600 seconds. Its six audited segments through state round 163
contain 169 proof manifests and 482 parent refinements. The rescued chain
bundle, stable audit, and audit-log hashes are
`3ceb22507ecee5eee5b2a1684d79bd15bc2d8fc393760614dfed356711c43b2b`,
`a640c4dde6e2de4b84ede3f6d443bf9ece4f45c36b1a2b9d9e17fdaf85e36fa8`,
and
`ca9325c37f662c8fb47cbb1eeeed061ff0b8a95aaae9b56846601c9cf4c05dda`.
The corresponding higher-level audit again replays all 371 backbone proofs
and connects the original parent-1 cubes to the eight/five residuals. Its
bundle, audit, and log hashes are
`b4f8e9b6e3aa837ac685795fa1d4ca410cf90cb8e49817773b7d62d1274870fc`,
`ed9e04eb2690e1049c8fcb4d3c3fc2e86c22c75c034d87b24f1f4ffcfe535d63`,
and
`24da5f48f024814c7f54611371c6e71eea7f7f94ee6a11a0c36201b4710d5907`.
Both audits explicitly return false completion claims.

A second immutable rescued checkpoint reaches the next two audited growth
boundaries. J297775 has nine segments through state round 191, comprising 200
proof manifests and 984 parent refinements and leaving nine UNKNOWN cubes.
J326185 has seven segments through state round 240, comprising 247 manifests
and 867 refinements and leaving six UNKNOWN cubes. The chain bundle, stable
audit, and audit-log hashes are
`4d8eba0c4a3f0ba6435702cbd70551c22d8b83515fcaf84f750e7b0863cde264`,
`801348f8958a09022187ca03e1e5dda8622fd17ded12ee55a354d0d09afe156b`,
and
`ebe86aae953951fc0504346cb204ed30de96a01dae4961b7b965c7f5a3e9aea6`.
Its parent-composition bundle, audit, and log hashes are
`9d4d9833c831d3d3ed71c840ba92f74e848be1e0a29a4a9b37fb198241a5984a`,
`51f6d5ba5e7aec5c60abd5cd4e3704d4c03d44d2d167436ff9ad7c4d112ffbd8`,
and
`38f75440eaf75c230895c1884f2dc70bffa8a6b47bf2e7141a4c5c9f619c0b29`.
This audit also explicitly returns `all_parents_unsat=false`.

The stable-tree migration for this checkpoint scanned 1,112 JSON documents,
rewrote 496 paths, propagated 86 dependent hashes, and converged in two
passes; its relocation-record hash is
`365bea1351e2fd507d41a7f8ad5751736e9b7549b43024cb401ff7fd26dbc575`.
Copying later solver cross-checks exposed that the relocator could partially
write JSON before rejecting a missing hash-bound file. It now performs all
path rewriting and virtual hash propagation in memory and writes only after
full validation; a regression test proves that a rejected relocation leaves
the tree byte-for-byte unchanged.

The live continuation uses a 600-second Kissat fallback on the rare sibling
pairs that both survive the 4/120-second CaDiCaL stages. At J297775 round 173,
Kissat and CaDiCaL independently closed the same child with checked compact
proofs of 41,294,002 and 62,412,884 bytes. At J326185 round 169, Kissat,
CaDiCaL, and iGlucose independently closed the same child with checked proofs
of 66,611,040, 54,089,886, and 104,704,389 bytes. These results keep the live
frontiers from growing at those rounds, but neither parent is yet UNSAT.

A targeted 3,600-second rescue substantially narrowed both round-boundary
frontiers. For J297775, Kissat closed all seven round-190 UNKNOWN cubes outside
the guarded growth pair; their checked compact DRATs total 1,178,631,163
bytes. Their cube rows occurred in reverse order, so the manifest composer now
has an explicit opt-in mode that maps a unique exact-cube subset independent
of row order and records both the sorted replaced indices and the secondary to
primary mapping. Independent replay of the composed 16-row manifest accepted
14 proofs and left exactly the original pair UNKNOWN. For J326185, Kissat
first closed all four round-239 UNKNOWN cubes outside its growth pair. CaDiCaL
and Kissat then independently closed the same member of that pair with checked
proofs of 195,953,015 and 270,149,972 bytes; the smaller CaDiCaL proof was used.
Independent replay of the resulting ten-row manifest accepted nine proofs and
left one UNKNOWN. After relocation, the J297775/J326185 composed-manifest
hashes are
`bd7a2421b4d1b6ea2fe83d833be4d7b800804081350429853794905f5f5204d7`
and
`1a3c1a3b7df11468656aaa9f85e81032488c742f2406bc7417eb93f0e6445b0e`.

The immutable rescued-v3 checkpoint extends the old chains with these two
exact-cube retries. J297775 has ten segments through state round 201: 211
proof manifests and 1,004 parent refinements leave two UNKNOWN descendants.
J326185 has eight segments through state round 241: 249 manifests and 868
refinements leave one UNKNOWN descendant. Both new boundaries were classified
as independently replayed exact-cube retries. The chain bundle, stable audit,
and audit-log hashes are
`0456aa753279802681a8a0dc4db013fc3317b55324483243b1daa728acf40be4`,
`999e416ec2793d775b82d90e848b3550c7f475eb1fa41a22644a4f74a1e3342f`,
and
`4c18a322733f8419584f593f55f71135f0d2368f7194dfeb2d8511362c99c7a9`.
The higher-level original-parent composition again replayed all 193/178
backbone proofs and has bundle, audit, and log hashes
`cca282dd0bb3d3a4620e7e944c659a41b9177d3e8f0c9d05f9489a18f80f94bf`,
`cb1b39113a0d225dd23853df91cc30fe93caeed703fd0e0f7854ddeffae0f8dc`,
and
`2d157f5dccbac556ff2ec0afcf86e85d1ee3ac1948f31777633c2b90732eba23`.
Both completion flags are false. The transactional v9 relocation scanned
1,587 JSON documents, rewrote 99 paths, propagated 20 hashes in three passes,
and has record hash
`5fa5abd2f8dd612f90003a55c1d1a64720b144e4609bd7b5ee0d981d8e937001`.
The immutable rescued-v4 checkpoint absorbs those live increments and four
further exact-cube rescues. For J297775, an older checked CaDiCaL proof closes
one member of the round-207 growth candidate; a second existing CaDiCaL proof
does the same at round 218. At round 238, CaDiCaL and Kissat independently
closed the same child with checked compact proofs of 100,709,025 and
86,486,471 bytes. These retries keep the authoritative frontier at two cubes
through state round 242. For J326185, a 255,751,469-byte Kissat proof reduces
the round-257 growth pair back to one cube. At round 277, a checked
80,547,438-byte Kissat proof was reused from an exact-cube hedge; a later
70,463,276-byte CaDiCaL proof independently confirmed that closure. The
authoritative checkpoint therefore retains one cube through state round 278.

The rescued-v4 chain bundle has 13 J297775 segments and ten J326185 segments.
Independent replay accepts 255/288 proof manifests and reconstructs
1,086/905 parent refinements, leaving exactly two/one UNKNOWN descendants.
The chain-bundle, chain-audit, and chain-audit-log hashes are
`ff0fcba4f7c031ad9a9b31d8f701339bd5e53f12d1119a4dd40eb732b61adc59`,
`24a0698ab9534c191843fdae04cf0fca349dbde448ef4a11cce1bdc3b8e5542c`,
and
`2e7bbe571f3bd973b21bc264ea1a67b4bae785c89e1cb465e6b634330e99f9eb`.
The original-parent composition again checks all 193/178 backbone proofs and
the 15 selected strengthening literals per case. Its bundle, audit, and log
hashes are
`37048cf7b639839a782370d82eb204022010b872cba377dbb658309b77f89ce1`,
`968bbbe6b878b13dcd13732ef45fec4a98e601dcc54bfeafa947419ff7d33c34`,
and
`a6f03058d08ca618a39928ee50d403aa31346ae5ec0bd502eda79c2d09492536`.
Both audit layers explicitly return false completion claims.

This continuation exposed two checkpoint-integrity edge cases. The proof
producer now atomically flushes every collected worker result before
propagating a worker exception or signal, so a short portfolio cannot lose a
valid proof merely because it has not reached its periodic checkpoint count.
The proof-tree relocator now propagates hash bindings for repository-relative
paths and leaves earlier relocation records immutable. The chain auditor
compares resolved artifact paths while preserving all content and hash checks,
so equivalent repository-relative and absolute spellings do not cause a false
state mismatch. The complete local and ARM suites pass 147 tests. Relocation
v10 remains byte-identical with hash
`bab0d6c0d80e708c9d3d0162488d732a86381faffcf0cb2b8362f57fcc46181c`;
the corrective v11 and post-freeze v12 records have hashes
`bd1edf2f184758df070641cc3748e15b57a33e3aa18a951d6f7f1ac99b8f0d6c`
and
`9225ceb31619f92e83ef9c74bdbd9b98cfa2ea2e0abd569b5f7eb54bde5efca5`.

After the v4 freeze, J297775 round 242 was independently closed on the same
child by CaDiCaL, Kissat, and iGlucose with compact proofs of 113,045,276,
112,210,091, and 308,181,693 bytes. The smaller Kissat proof was composed and
replayed, retaining two UNKNOWN cubes through round 243; the guarded round-244
candidate grows to three and is not adopted. At J326185 round 278, CaDiCaL and
Kissat independently closed the same child with 94,139,627- and
101,863,998-byte proofs. The CaDiCaL composition replayed successfully. A
stable snapshot of its single-cube continuation through state round 351
independently replays 73 proof manifests and 72 parent refinements, still
leaving one UNKNOWN cube; its audit JSON/log hashes are
`d2a08c1e5eeb5d4ea3c5a3510dcd7a2b955574b519039a264148a45d41758dbb`
and
`61490d91b3a78f6a582f7a0e61b54d2c2cb950a19e07cbe86fe88198fc623b1e`.
Relocation v13 bound this snapshot into the stable tree with record hash
`a47f0cacc54a6fbdc08104463d9206a213a5f633610aaa6e6279d584197d367e`;
the live chain subsequently stopped at the round-351 candidate because its
UNKNOWN frontier grew from one to two. Relocation v14 preserved that exact
candidate and halt record with record hash
`71a0af6a291e30d3b1e2ddc089afee1d549bc1f6f44ccd249ccaf4a3d405e2ff`.
An independent replay confirmed the one-parent complementary split on
variable 3189 and the candidate's exact 0 VERIFIED/2 UNKNOWN result. The
corresponding J297775 round-244 growth candidate was also replayed separately:
its two parents split on variable 880, with an exact 1 VERIFIED/3 UNKNOWN
result and a bound 2-to-3 halt record. These post-freeze results are not part
of the rescued-v4 bundle. No parent-1 UNSAT, fixed-pair UNSAT, order-45 UNSAT,
or `R(5,5) <= 45` theorem is claimed.

The first jointly hard J297775 round-244 child was subsequently closed by
Kissat in 1,985.07 seconds. Its 344,533,164-byte compact DRAT has SHA-256
`a80a1e60572751686ec54dfc38770fc456c33a6ddf06794ff509eec1cfef493c`
and passed a separate replay. Exact-cube composition with the four-row growth
candidate restores a 2 VERIFIED/2 UNKNOWN boundary. After relocation v15, the
source/composed manifest hashes are
`7e41e32c0286e23609f78454d9541da49000987831a7e681d0a7a941f903c57d`
and
`eade331ba216975b8515befc91a9ad8d6d85ecfdb610e2d6a288dab740ccac28`;
the relocation record hash is
`aa66ac0e42c231dc12669883716544aa27e21ae4a6054003b5049dd81cbf2e00`.
A fresh stable-path replay accepted both retained proofs, with audit-log hash
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`.
CaDiCaL independently solved the same child and produced a smaller
299,667,655-byte compact proof. Its relocated manifest hash is
`6729d76db82b177cba5fe266925a73e70d4e9a58bb4d64083e76a0fdf66b36d6`,
and a stable-path replay passed with log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
A guarded continuation from the restored width-two boundary starts at round
245. These results remain partial and are not yet included in rescued-v4.

CaDiCaL and Kissat then independently rescued the J326185 round-351 growth
pair. They closed the same child in 1,335.36 and 1,387.54 seconds, with compact
proof hashes
`ca87f0f0742e32489757bce1e4aadfcf728270d462f16b16e79b2703a53aae96`
and
`da3953b4fe4c8db1a241bf7bca9c4982c720c39a99dd2424e041869d3c4df1e7`.
The smaller CaDiCaL proof reduces the exact candidate to one UNKNOWN. The
stable CaDiCaL source, Kissat cross-check, and composed manifest hashes are
`fd71c1aafe545ff3346d1ab5ec660c620990200022daf7198807a528aea8df88`,
`977c048ebe28bdebdd9f9a2568085e82f06384a7b679d9687093de79953d16a0`,
and
`6129a9b31f8ccf792f89d2c175ce046f95121e60d68d2c0d6a83d18e9dbf999f`.
Relocation v16 has record hash
`9eef9388f9fc62de7f6b524091057590ecc522bddaabd0f7cd927142ceb3f03d`,
and a fresh stable-path replay accepted the retained proof with log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
The new continuation keeps width one through state round 356, where its hard
candidate grows `1 -> 2`. Relocation v19 has record hash
`4ddc029b6f7cae72674b2ff00a512f1748be25dd5f4c125f214d76a528a1ffd5`.
An independent adopted-growth replay accepts six manifests and five
refinements; its audit JSON/log hashes are
`74ccbf9bd6bef6bc29b83c9139855e71e1c640bd86af92f9abc5fa9aff188de3`
and
`1949a36898609b0ee026d63c3d1c2af94cffbcec1ccab216edfea760161208b9`.
The exact growth pair is under solver-diverse long retry.

A separate complete screen of auxiliary variables 800--1200 on the same
round-356 parent tested all 730 signed children for the 365 variables not
already assigned. At five seconds per child, CaDiCaL found 153 and Kissat 152
one-sided contradictions; 152 choices agreed exactly, neither solver found a
variable with both signs contradictory, and their only disagreement was on
variable 1096. The variable list, exact ICNF, and CaDiCaL/Kissat result hashes
are `4048bdac6c870267f0a606de2384f44dbf949cbe975977788e934adbcd35bf45`,
`8437d222403ac9668b268c604ecace7386ef765bef09549098e3855196c507c3`,
`19fa5b342eefd1b1ce0b4e8695d4c73e2ee119d0ee7b593876ebddc7fcf26fe4`,
and `a65aedfe0a08763b18741ddd6b73ff075fcb601f096914432ef0496110e16286`.
The agreed variable 1092 was then used for an exact complementary split. Its
positive child is contradictory by unit propagation after a 36-byte compact
DRAT, while its negative child remained UNKNOWN at 120 seconds. The resulting
manifest has hash
`80725ad1c3452b5bc363c3b4a920256a2094b16ca65da355685f6828d567228b`.
Independent proof replay has log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`,
and a one-round chain replay reconstructs the complementary split and ends at
one UNKNOWN parent. This certified alternative avoids the automatic
variable-893 `1 -> 2` growth. Complete follow-up screens selected variables
1183 and 1184 at the next two boundaries. After relocation v23, the three
selected manifests have stable hashes
`95943232b429375a03cda7d364558cd249d71763cc7f11e6f87d57dbc850e69b`,
`d419cbe1cf297a41e6db645691f92de909f8ed27042ac877dbf2244554c02bde`,
and
`a68001a1c37658c506685a674f83172507833f033eb3ccfbad661c216d3acc74`.
Their three independent stable-path chain replays each reconstruct one
complementary split and end with one UNKNOWN parent. Relocation v23 has hash
`97dad5166f3183b8ad1f7f40adeb0649696cc407d5ac8521283cd431ede59b4e`.
Three further rounds selected variables 1199, 933, and 1190, reaching stable
state round 362 without widening the frontier. Because both screen solvers put
the contradictory side below 0.1 seconds, these rounds use a five-second
proof-mode budget: that is enough to generate and replay its compact DRAT
while retaining the survivor as an explicit UNKNOWN, instead of waiting 120
seconds merely to rediscover that the survivor is hard. Relocation v24 has
hash
`5f9d66a720ec5bc16f0adafc1fdbdc35665d42dd199ac4ee0ddf864cb1d1c7a1`;
the three new stable manifest hashes are
`aec42b837ec6a3f1c5709071fa36d63c208cf3337b6d5128eed5b8b21f9a81c9`,
`935408c9b86e064f4df5fffe69b0437bd15eae3a739801bf2e8fbacb1e79b165`,
and
`60836973ba12b5eec02654509e44843143998fa23a31ce807660dcffc3855b67`.
Independent stable-path chain replays accepted all three one-round segments.

`select_screened_binary_splits.py` makes this choice reproducible. It verifies
the full parent/variable/polarity layout, hash-binds every input and all solver
result tables, rejects any SAT result or solver disagreement, and chooses the
fastest jointly observed one-sided contradiction for every parent. It also
canonicalizes recorded input paths before hashing the report. This last rule
was added after relocation correctly rejected an otherwise equivalent path
containing a lexical `..`; no proof artifact was accepted through that failed
attempt.

`refine_screened_binary_cubes.py` exposes that selection policy through the
same six positional arguments as the compiled binary refiner. The normal chain
runner can now append repeatable `--refiner-argument` options, so every round
automatically exports the exact UNKNOWN parents, screens every available
variable with at least two named and hash-bound solver binaries, selects one
agreed one-sided split per parent, and hands the complete complementary split
to the existing proof/check/audit stages. The first production run uses the
800--1200 auxiliary window, one second and 16 workers per CaDiCaL/Kissat
screen, followed by five-second CaDiCaL proof mode. It automatically completed
rounds 362--364 on variables 1181, 868, and 1149, retaining one UNKNOWN parent
at every round. Their checked compact DRATs are 26, 32, and 38 bytes.
Relocation v25 has hash
`f585e0e24aa77f51c3445358c73a6131d41ee27c9263e1a4bd6e1909800a302c`.
Independent stable replay accepted four manifests and three refinements
through state round 365; its JSON/log hashes are
`facc89a5c8818e773a22b14b7c5ca3e2e57d5d8b2dffdd5839497f07d267f2fd`
and
`44104ef4a459c2a4b8da9c7776e8ba133b91e31eaa9002a321c5cbc41e1a5a74`.
The live chain has already reached state round 366 and continues. The local
and ARM suites pass 156 tests.

Certified iGlucose also independently closed the already rescued round-351
child in 1,798.45 seconds. Its 354,042,170-byte compact DRAT has SHA-256
`4b50ae1ce636c319051a6980eaf97830d21c86bdc43cb6f0d4b24730235d02df`;
the relocated partial-manifest hash is
`49c957e1368bd018f3785a248aae1f879f0255a7658b83f2f5a6bb98b68d8902`.
A fresh stable-path replay passed with log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
This third proof remains a cross-check and is not needed by the authoritative
CaDiCaL composition.

The J297775 continuation from the rescued round-244 candidate completed
rounds 245--273 without increasing its two-cube frontier. The guarded
round-274 candidate leaves three of four children UNKNOWN, so the authoritative
state correctly remains at round 274. Its stable immutable state has SHA-256
`71c615ef1bde0b80f21d1c92453e24af38c16ea0ebba244c43183f7caa51252c`;
relocation v18 has record hash
`a903cbb6b1447548d6dba15fb7f4b9c079ffaba6b20b4c778ae7707edd99c70a`.
Independent replay accepts 30 proof manifests and reconstructs 58 parent
refinements, ending at 2 VERIFIED / 2 UNKNOWN. Its audit JSON/log hashes are
`8469c9e4d0843654a3506df0fa44e29e6b34b1f3a91c4f25a583e270fc8dd639`
and
`be5d8549d42b7d9dbc018b9058308ffb2f91a03a33db84137a79047b2c20f6bd`.
Default CaDiCaL and Kissat independently closed the same first residual of
that candidate. Their compact DRATs have sizes 126,165,358 and 135,835,133
bytes and SHA-256 values
`8dbc90f2958b54eb418af6a2b7418fd58cde78f8584581f794f6568118858cae`
and
`0633299ecb9e3cc6624e17edf065ec78d43a6a6deeca1af431b1d8eaacc0fda7`.
The progress finalizer freezes completed rows even when a long-running sibling
prevents the producer from rewriting its final progress file; atomically
published proof and checker artifacts are rediscovered and validated, while
all unfinished rows are materialized as explicit UNKNOWN entries. After
relocations v20 and v21, the CaDiCaL source, exact composed boundary, and
Kissat cross-check manifests have hashes
`c1f2b7095bd4973591803ed4a1796b5f86c86a3b46fa6642404c4867dfa133d2`,
`097d507c6fb0543dd65b9849014cf7a02a779bcb870c222a37874c13ba61c2db`,
and
`a4f9094fd97eab8b812c48b26bcb5ca7af2a44f218b5bcd0b272807a92df6127`.
Fresh stable-path replays accepted the composed two-proof boundary and the
independent Kissat one-proof cross-check. The restored width-two continuation
completed rounds 275--284. At round 285, the normal CaDiCaL stage proved one
child and the 600-second Kissat fallback proved the required child of the other
parent. Their compact proofs are 13,441,164 and 23,377,701 bytes with hashes
`599e35f295939ccd920579cd53235ab8d9c679b5479156bb2c962c040521f921`
and
`0638db0d1e663130eceb8c0da5695a0230c0b0d30b1a5ad05e0fe720aa1b8087`.
The exact candidate therefore has 2 VERIFIED / 2 UNKNOWN and was adopted.
The continuation retains width two through live state round 301. This
checkpoint and both new rescue boundaries remain outside rescued-v4 until the
rescued-v5 bundle and its full replay are frozen.

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

## Rescued-v5 checkpoint and post-checkpoint J297 progress

The rescued-v5 bundle extends the independently replayable strengthened
parent-1 chains to stable state rounds 317 for J297775 and 365 for J326185.
The two terminal frontiers still contain two and one UNKNOWN cubes,
respectively.  J297775 now has 16 segments and J326185 has 19.  Their bundle
and original-parent reduction-bundle SHA-256 values are
`202485bd3dace93fc3ed2fd7ccfac113355f04cc7f55fb0f1087ec74e58ddb7c`
and
`8b3f6830268b6a818bf685d74ac8cbd2e2fb3a77b8859612bf3f5cd92b186a21`.

Two of the new segment boundaries do not denote an exact-cube retry.  The
previous immutable state ends immediately before a complete binary
refinement, while the next seed is the externally retried proof manifest for
that refinement's children.  The bundle auditor now handles this case only
when the next `first_round` is exactly one greater than the previous final
round.  It independently reconstructs the previous UNKNOWN frontier, checks
the saved binary refinement, and binds the next proof seed to the exact child
bytes, count, and formula.  Equivalent cube paths may differ lexically, but
their SHA-256 and row count must match.  Unit tests cover both the relocated
path case and rejection of a wrong rescued-child count.

The corrected two-layer replay completed successfully.  The chain audit
covers 332 J297775 and 383 J326185 proof manifests over 316 and 364 recorded
rounds.  The segment summaries contain 1,234 and 991 refined parents; in
addition, the
auditor reconstructs the omitted round-242 and round-278 refinements of two
and one parents before accepting their rescued child manifests.  The chain
audit JSON and log hashes are
`4b41a35ecf77a52dafe5f9e5eb242df7b6f5f78df8ccdb0d134e60b78c735419`
and
`b954a36c81a713f05416b6350368b5ec8597bbd1856c7b8ebce741da9c78b29f`.
Its terminal states are still 2 VERIFIED / 2 UNKNOWN at round 317 and
1 VERIFIED / 1 UNKNOWN at round 365, so `all_cases_complete_unsat` is false.

The parent-layer replay then checks 193 and 178 backbone proofs, respectively.
For both cases it accepts all 15 certified backbones, every bad branch, and the
exact strengthened-parent lineage.  It still reports two/one remaining
UNKNOWN descendants, `parent_unsat=false`, and `all_parents_unsat=false`.  Its
JSON and log hashes are
`49790b42d58b4cfc97d9b30335a27eb63dbd2ba7b91fc1c0b18c657b2d32cf23`
and
`682e319acb6f9ac40c1f1eda962bd1fd88e7a4098b8784b0c7f85860470daa4a`.

The first post-v5 J297775 continuation has also been frozen separately.  A
normal continuation from round 317 through state round 331 replays 15 proof
manifests and 14 rounds with 28 parent refinements, ending at 2 VERIFIED / 2
UNKNOWN.  Its audit JSON/log hashes are
`681129482d6954cba6bf45ed75a76826ed563787b8c3993b3d7052d6b735e751`
and
`90e7f3bf7a5354f5b917075e174893f655e880a65fae5a467524046a3f71102c`;
the final manifest hash is
`57ee5a5a60d2b8ffbe4f59de2cb24ba60cda3a235dd910f1eca01bcec713f06a`.
Its automatic round-331 split would grow the frontier from two to three, so it
was not adopted.

Instead, a complete CaDiCaL/Kissat screen found a contradictory negative
branch for variable 897 on the first parent and variable 1179 on the second.
The two compact DRAT files are 14 and 38 bytes with hashes
`98f892363fc1a247f7600135e5872ff594b33802339e276cb111b5b50a1463a2`
and
`5ccee31cd1f48a685b4174656319e4a14b80a3ec3dcea2a67cd10f5c213091b9`.
The independently replayed one-round chain again ends at 2 VERIFIED / 2
UNKNOWN.  Its audit JSON/log hashes are
`0eb2f8c480bf0dfb02ead68c6c347ea562e35da3962bbc0dbaf634ac225420c9`
and
`2f11029d4b4e98f9a9414b914a4c3369c09c49af7e5f3bb74c4e28e79cc59fd6`;
the final manifest hash is
`17edd156cc11ebcda76b795b85043bb0d151617d3fae2b2c6d8b7bd8b5c23792`.
The isolated relocation record that contains both checked stages has hash
`fe5c12f38799f87c4897fab02e788772de58e2e13788d652e6634465519f6963`.

The rejected automatic round-331 candidate supplied a useful independent
route as well.  Its four children initially had one checked proof and three
UNKNOWN rows.  CaDiCaL and Kissat independently closed child 2; freezing live
progress and composing it with the exact four-row candidate restores the
candidate to 2 VERIFIED / 2 UNKNOWN.  A one-row ICNF selector records the
source hash, exact row indices, output hash, and both counts so queued
portfolio rows can be run without losing their position in the original
candidate.  A fresh replay of the composed four-row manifest passed; its
audit JSON/log hashes are
`a4b3f7fced348ccf3eea7924a5dc5ad87eeea6a69a2952ab8bfd80f59fda6d2c`
and
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`.
Relocation v28 stores both solver sources, the composed manifest, and the
selected-row lineage in a 646 MiB snapshot while linking to the immutable v27
candidate.  Its relocation, stable CaDiCaL, stable Kissat, stable composition,
and relocated selection-manifest hashes are
`3536c42051206bc804bbbae9c6cb5a12590a73c77a996ef4934ef005cf2bf55e`,
`15458de05c8ff2df9ac368702aa1a860e7a95deaf71faa10f37b86732f56ada3`,
`45a23301f90b45d0a1364e4a6f7f2704b2f419cf0d2bbfb9eb0450a9856354b1`,
`9e98c3913f3550b057aa1ed9068394eb5e3b0e1d427bf18945a427fe476fa55e`,
and
`7142438da1d46b1f5f7017fce0243dc5e044bfdf7c9f1d810cc271e8d5ad55b4`.
Fresh stable-path replays accepted both the selected CaDiCaL proof and the
larger Kissat cross-check.  Reconstructing the v27 round-331 refinement also
binds the v28 composition as an independently replayed rescued refinement
whose next round is exactly 332.  Independent 3,600-second CaDiCaL, Kissat,
and targeted iGlucose attempts did not close the remaining child 3, so this
portfolio did not improve the frontier to width one.  That outcome is not a
prerequisite for the restored, checked width-two boundary.

All 158 repository tests pass on the ARM builder.  The node has 32
physical / 64 logical CPUs and 244 GiB RAM; at this checkpoint its root volume
has about 19 GiB free and `/dev/shm` about 98 GiB free.  Storage remains the
first resource that would need expansion for a substantially wider proof
portfolio.  None of these partial chains proves strengthened parent 1, either
fixed-pair formula, the order-45 formula, or `R(5,5) <= 45`.

## Screened continuation checkpoints after rescued-v5

The two live screened continuations were frozen together at J297775 state
round 378 and J326185 state round 411.  Relocation v29 bound 389 JSON
documents into `v8-screened-continuations-snapshot`, with record hash
`d05e5510e373cffffaf7863256715eb4ff1286432e84ec86e778d71c8677785b`.
Independent stable-path replay of the J297 continuation covered 47 rounds,
48 proof manifests, and 94 parent refinements, ending 2 VERIFIED / 2 UNKNOWN.
Its JSON and log hashes are
`786cf7c00740b8d981ae594b3cea40caf9d6bf845c4501d8484f43b43cd5c403`
and
`b96b31f24b2e345261ef61a9a3af6ba7b5c064984a0a572acc6aae366834ed72`.
The J326 continuation covered 49 rounds, 50 manifests, and 49 refinements,
ending 1 VERIFIED / 1 UNKNOWN; its corresponding hashes are
`c3a3e02a2f5724e7d2fe2089eb0063ebd3cc757d66f268abfa7f1bba47213a93`
and
`a5089edb4b0532bbfa8e75ada7ba2fd2dd3d529f0806c45d24968ff258e2636c`.

Rescued-v6 incorporates those two stable checkpoints.  Its chain and
original-parent reduction bundle hashes are
`afbd6fd0789ddddb530bdf2d3b5f617ac167d711bc2fa6b14bcc42ab37d79e86`
and
`f93b22a168500632e6ba1cc96065b45ebf7fbd3fe5494cda38ead4133076719b`.
The new J297 round-275 and round-331 boundaries replay as an exact-cube retry
and an identical terminal manifest; the J326 round-362 boundary is also
identical.  The first full v6 run replayed the earlier J297 segments and then
exposed a path-normalization defect at the v8 round-331 boundary: the bundle
auditor used `Path.resolve()`, which expanded the snapshot symlink and changed
the exact `source_manifest` spelling bound by the relocated lineage, although
the manifest bytes and hash were unchanged.  The auditor now makes paths
absolute without expanding symlinks, and a regression test distinguishes the
linked path from its resolved target.  The rejected audit log was retained and
the full replay restarted successfully.  The completed replay used four
segment workers and four proof workers per segment.  J297 covered 17
segments, 394 manifests, 377 rounds, and 1,356 parent refinements, ending at
round 378 with two VERIFIED and two UNKNOWN cubes.  J326 covered 19 segments,
429 manifests, 410 rounds, and 1,037 refinements, ending at round 411 with one
VERIFIED and one UNKNOWN cube.  The audit JSON and log hashes are
`02cc90594d4fdd183dcebe27fc86ac45da4fd319b5d9b2c2a4e5ae95b217be00`
and
`0b90fc7f2d182e98d8d6d4110032c56389dd1437aa11315afb44a1212155474b`.
The bundle auditor also accepts an explicit
`--segment-jobs` concurrency bound.  Independent immutable segments may now
replay in parallel, but their adjacency and completion claims are still
validated afterward in the original order.  Because three terminal cubes
remain UNKNOWN, the successful replay validates the partial frontier but does
not make a completion claim.

The corresponding rescued-v6 strengthened-parent audit also completed.  It
replayed that entire chain and separately accepted all 193 J297775 and all
178 J326185 backbone proofs; both backbone manifests are complete UNSAT.  The
two cases nevertheless retain two and one terminal UNKNOWN cubes, so their
`parent_unsat` fields and the aggregate `all_parents_unsat` field are false.
The strengthened-parent audit JSON and log hashes are
`55b8809e6c2a1ace11346daec9954e43f1eb834ec7a26c700f03b4d1d7a2ffff`
and
`f8dbf65bc000b489f8ce1f21fa0034cdd133738bd01a093f172c72dce9578acc`.

The J326 screened runner then reached its 100-round limit at state round 462.
Relocation v30 has hash
`569028cd98210691f25db9a4aa6c075ca95ad480a66eb9d65cfa4ada1122b762`.
A fresh replay checked all 100 rounds, 101 proof manifests, and 100 parent
refinements, still ending 1 VERIFIED / 1 UNKNOWN.  Its audit JSON/log hashes
are
`d4bc1d06466f316056f9737f2a6b5f1f648bc82d350907f22f52cc0a758f0496`
and
`50eb3befd4e1f3a9116041454cfae4281eb3252b545878fcd897c028f70e5b18`.
The final manifest/state hashes are
`eb2986da249f51e2e731cc41eb37bc58d6dde0e0344dbdbdcd6489b32e97a74d`
and
`57b6f083de5d23978c405d3319c5aaff65b72e430e6aff478c77c100aceb0908`.
The same work directory was resumed from state 462 for another 100 rounds.

Hash-bound UNKNOWN frontiers were also exported for direct long-solver
portfolios at J297 round 378 and J326 rounds 411 and 462.  Their ICNF hashes
are
`8774bcb849f9fb2df937e34048ef191db3bbafa7b14cc1ff8a8d2f40d921c297`,
`7c45921120a956bb2d4e45788f03cf784171b3a6c9b879ac4940e1221cf65439`,
and
`d0046a4e8d28dea87cc49883fce286c77690366cdd45e86d69bde586d0d51d94`.
The two-parent J297 round-378 and one-parent J326 round-411 iGlucose runs
returned only UNKNOWN after 3,600 seconds.  Their manifest hashes are
`4caf1d736acf51c4e5e4453478cd595503af12b44b3814bb00d42def57c720d8`
and
`2ec9b687afb227b1f6d6714f89d95e1232be5125cf991125417946e61f9248b8`.
CaDiCaL and Kissat also returned UNKNOWN on the J326 round-411 parent; their
manifest hashes are
`b4f30fb65d57a542734c98c654bfd32d7afe8bd21fcb4a5039d2e9c44f394c13`
and
`ce2c7857bff56eecccd74f92403ea797aed8507175e4ff6f12048fcb5d203bf8`.
The three-solver round-462 portfolio also returned only UNKNOWN after 3,600
seconds per solver.  Its result manifests were copied to stable storage,
relocated, and re-audited with `--allow-partial`.  Relocation v34 has hash
`653b6dfbe6d12e4c8e81caeee4c33ceb71636b4604cec1233e53c5bb77be6721`;
the stable iGlucose, CaDiCaL, and Kissat manifest hashes are
`6ccc32a9a9f25d7c47d09134561ddea293e52b362e41e0654f95850e460b375a`,
`a955c8d332202a3aaece83dd1ec1c22c9d751152376231c8ef6524c558a4a650`,
and
`8fe6e2e0856e579997e57d020cb91a98d1512fbea4d3326b45cc4ebfcdfdbd8c`.
Each stable audit log has hash
`3d9c660d9fe1ad748481036a6378c600bbec37efa5e948ac800d08be7a4e6508`
and reports zero VERIFIED / one UNKNOWN.

The resumed J326 screened chain reached state round 506 before the original
one-second screen over variables 800--1200 found no one-sided split accepted
by both CaDiCaL and Kissat.  This is a refinement-policy failure, not a SAT or
UNSAT result.  State 506 and the failed round-506 screen were preserved in
`v13-j326-r0506-screened-snapshot`; relocation v32 has hash
`9b47a38bb02ef6eb4a5230993f382eac2560050a351dd7f145f2f470f5166b87`.
An independent stable-path replay checked 144 rounds, 145 proof manifests,
and 144 parent refinements, ending with one VERIFIED cube and one UNKNOWN
cube.  Its audit JSON and log hashes are
`9ab68784fb18bb7351922b9989c9ababc546b8493b11d98f60ff6fe4c00e436f`
and
`62f24443ac3dc5c24e4ef62cc9b167166a74e5b95bd46d0752c06d2c01225278`.
The failed live artifacts were moved to an explicit quarantine directory
rather than deleted.  Retrying with variables 1--1200 accepted round 506 and
advanced the live chain through at least state round 512.
The unique state-506 UNKNOWN cube was exported for the next direct portfolio.
Its ICNF and lineage hashes are
`a1786afa0545807d8cd42ad3e5c12537193a2dda4c9ab001e00b91299996bcb5`
and
`1f749324562ea13ea1819096f4ddc54cbf95ec99f3dc15380021c87bc14f14ae`.
iGlucose, CaDiCaL, and Kissat each ran for 3,600 seconds on that deeper cube
and returned UNKNOWN without a proof.  The outputs were copied to stable
storage, relocated, and re-audited.  Relocation v35 has hash
`581fcd4d50a67f6cfb812532d75d889651c4481083249a58f880d2bc2a4d030c`;
the stable iGlucose, CaDiCaL, and Kissat manifest hashes are
`e6f5361a3070702d805f219aa487e95b46b9eff2673c8dfa1fd938dc2ddbdcb2`,
`4155a0b6d91f8436a67bb5137f05db2fd2f55e7330453dab14d60a1845aaab67`,
and
`e05e772ff9c23dbf48756416a3c3976a3a1cd0a013ff24d3eb3b7d407c5c5e58`.
Each stable audit reports zero VERIFIED / one UNKNOWN and has log hash
`3d9c660d9fe1ad748481036a6378c600bbec37efa5e948ac800d08be7a4e6508`.

Finally, the original four-row J297 round-331 iGlucose run independently
closed child 2 in 2,296.95 seconds.  Its 438,113,063-byte compact DRAT has
SHA-256
`2eaecb24df9fef9de7b03423c56579c1ba9df36032b19f84706b2ed5b0faee0e`,
and its source checker log has hash
`9f134488f579b5723278b0f05bf0a362d863e0e9a2dbd807daa893ca84cb47cb`.
The interrupted four-row progress was finalized with UNKNOWN placeholders and
relocated to a stable v12 snapshot.  The stable-path replay passed with two
VERIFIED UNSAT rows and two UNKNOWN rows.  The relocation, final manifest,
and stable audit log hashes are
`53a85260aeb7abafd0536b17526dfdcfa8623a43169c4684cae501f8b6365fb3`,
`b7efce2dc0f54a1fc838e3521a66279bfbcf9f845f107eab858f605cf3845e7a`,
and
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`.

The J297 screened continuation later stopped at state round 414 when the
one-second screen over variables 800--1200 found no agreed one-sided split for
parent 1.  State 414 and the failed screen were preserved in
`v14-j297-r0414-screened-snapshot`; relocation v33 has hash
`f1a2acdff1d15042b62dce1c62efbcc3c2117b9c0a54ec7dbcb6d2fa379da0f9`.
An independent stable replay checked 83 rounds, 84 proof manifests, and 166
parent refinements, ending with two VERIFIED cubes and two UNKNOWN cubes.  Its
audit JSON and log hashes are
`ac87ffc6aca714448e0c1b75184534ec251a4bd40d8ab5796fa2a2533cd3309d`
and
`7e6f69ae5e1ddf1e32ad8a31a55dbbfdcbfeddf205ec7114ace7f664d93a802b`.
The failed live artifacts were moved rather than deleted, and the live chain
was restarted from state 414 over variables 1--1200.  It accepted round 414
and reached at least state round 415.  The two state-414 UNKNOWN cubes were
exported with ICNF and lineage hashes
`7def28ff87dcffd793cbfebb4007d4ed6c10e15b5867ed5223e08c5c8c0d83ac`
and
`1a7e31f8023bd1c3e0aed3f84e5eee3aec34679614665edf6558290fc45e1aaa`.
iGlucose, CaDiCaL, and Kissat each ran for 3,600 seconds on both deeper cubes,
using two jobs per solver engine.  All six attempts returned UNKNOWN without
a proof.  After copying to stable storage and relocation v36, whose record
hash is
`5a2aff934d593ca12c35290dd5ca55a912279b98ecb64eb41f84b7c149912664`,
the stable iGlucose, CaDiCaL, and Kissat manifest hashes are
`5dacddd038495cdce277ad677d58a37d43738cc06d1c75dfa53b0b6a5e8a09a5`,
`7e4626cec35db32a38fc7beaed76c5b6b63838305dc0eb780d43593e00b5d69d`,
and
`b7c6afe78eb52a152ff7c281e190505815df4f3c4aedb4164cc3b11a4a8af391`.
Each stable audit reports zero VERIFIED / two UNKNOWN and has log hash
`3f8f88e02ae9c2005b178d357544c6a7f2b807f8201e8e9f794c8ea16a08961b`.

The paused live chains had already committed deeper constant-width states at
J326 round 522 and J297 round 418.  Their UNKNOWN frontiers were exported with
ICNF/original-lineage hashes
`d99ee498ab6098e6b97ee6e9ebe53407114d87ab3bebe0e29e70b77e70473efb` /
`08d187f101e0bf8cfbbec7e3603aa2577dc553605e722115d13871a83751f3ef`
and
`bebfc0888867ebaae76c33e35f8d4b00b6549c063dd3caf9fc9cc11e729fd7ec` /
`4d58393232b96cb483787172dfe3f90f8efcc823af0a37bed443c0c20ed96b22`.
The exact workdirs and their seed boundaries were copied to stable storage.
Relocations v37 and v38 have record hashes
`eccc5585d5fdce91a1eab523fab21dc64bb678fb6d70aab17b4350fd80e839ab`
and
`657106354f788b4fcb1322b9a159becb438360b7b0b17498b163ef3b3bbcfd76`;
the stable J326/J297 lineage hashes are
`2c114075914742ebd9383d5a6c80ad195730a67c7b26d2c92c4ef7d318e4e4ee`
and
`9a45c88324d620f9b759da13042fd3e2b1fa704904a1c76e13754a94a92ab6c1`.
The first relocation attempt transactionally rejected the missing seed
boundaries without modifying the copied JSON.  After those two exact,
hash-bound seeds were supplied, both relocations passed; fresh stable-path
chain replays also passed.  The J326 replay covered 160 rounds, 161 manifests,
and 160 parent refinements, ending one VERIFIED / one UNKNOWN at round 522;
its JSON/log hashes are
`3950acde503ee0e50ab32b0cb00c1e0b8aadf74f6275e2ac512e420925c8400a`
and
`e6e4644c7b5c6b72a6af27e9eaad9811dff4043b453781235e7f7adfcf67f5da`.
The J297 replay covered 87 rounds, 88 manifests, and 174 refinements, ending
two VERIFIED / two UNKNOWN at round 418; its hashes are
`94cf2d6807634430aceec4b2dac5e8d31ca1d28b9a37c45968da6b466afe19cd`
and
`fb7e9d2fe92aa5a067b95929693806f8c0f066b4c75326a27ce083f81bb977c8`.
A new three-engine 3,600-second portfolio ran on the single J326 cube and
both J297 cubes.  The first wrappers exited during argument validation
because their scratch directories did not yet exist; no solver ran in that
attempt.  Those launch-error logs were retained before the directories were
created and the six wrappers relaunched under fresh PIDs.  All nine solver
attempts ultimately returned UNKNOWN without a proof.  Result relocations v39
and v40 have record hashes
`192fa3de21356e15ce010f75f135adcbee96b9ba59f636d6f899e8484b615e00`
and
`49177fb29db10fede9e34e8226f7f4270d5964ca2b4bf49a75eb3b014a91b321`.
The stable J326 iGlucose, CaDiCaL, and Kissat manifest hashes are
`95272b5bd34b163da63f91f3e8de5b9457e1b0b62cfd2ca00adf80a06434556d`,
`65894fc28379abf1c9693200a514c56a36b3fd6a61027bcef3b24eabb8d66fbb`,
and
`cc57ba9843631ebad4a2a45b606bfda31b61346fd2a5d2392d68740396e1cdb1`;
their audit logs each report zero VERIFIED / one UNKNOWN and have hash
`3d9c660d9fe1ad748481036a6378c600bbec37efa5e948ac800d08be7a4e6508`.
The corresponding J297 manifest hashes are
`a4070bc4346463e063e3d4fb26ea421f9d8ea93eca6a7515a6432138bcc3214f`,
`9e3b8f9958dfa870724cfa1bd117d47711774f0888beac7bb303ea8a787aafec`,
and
`504cfbf136f432886a369934d8762f7c9889ea322cd5d51207649a0d32834ac5`;
their logs report zero VERIFIED / two UNKNOWN and have hash
`3f8f88e02ae9c2005b178d357544c6a7f2b807f8201e8e9f794c8ea16a08961b`.
After the rescued-v6 strengthened-parent audit completed, both live screened
runners were resumed from states 522/418 and advanced at constant width
through at least J326/J297 states 544/430.

Running both `screen-jobs=16` refiners concurrently can saturate all 64
logical CPUs.  To avoid diluting the next wall-time solver portfolio, both
runner parents were stopped again after their in-flight refiners completed.
The next exported frontiers are J326 state 545 and J297 state 430.  Their
ICNF/original-lineage hashes are
`ebb59be362cb698ed76375c487e0587af13b34cc7ca9fb00be5a92830487a04e` /
`ea2af0f204dc6d8b9c46d4262ebd62df80afd7af95ec053406bb1c04c50d6d84`
and
`a66d154e8347af1e1797acd61490f63e38853e7ada49a264cb509be90b9f6549` /
`1d6029608cc0a1d69dbf0978c9badec3a9c066c13821ccf2fcd87b17672ff937`.
Relocations v41/v42 have record hashes
`7068a6c227687f348498376150c4be2237a46941f1dddcca021f4db1636473b8`
and
`20aaf6bbe7ffd184faf7033ebb47bdaa33a7273fff383d3e7ffe1751c4ac05ac`;
the stable lineage hashes are
`d5c1ac15aa095b52127de25a0c5d51fee7eee54d0afb723ef73419b523c4618b`
and
`049f5b15d0497dd5bf6b0c204b20974daa31bc0f41894ce25dde69b846cf57b8`.
Stable-path replay of J326 checked 183 rounds, 184 manifests, and 183 parent
refinements, ending one VERIFIED / one UNKNOWN; its JSON/log hashes are
`2b62b6cac76c7a472ff44c1a03404ac3a535527b35cb4090e55c4564be04e909`
and
`0b964ed7dfcb4be93512a06655eba0c283fd01192babf66df438ca9a87fc4db8`.
The J297 replay checked 99 rounds, 100 manifests, and 198 refinements, ending
two VERIFIED / two UNKNOWN; its hashes are
`d131a44d10a313890d8d9d12db666d3c8f5fdbeaa80aba6a90a2d7f1c05dcc06`
and
`b85b9044bb7957a2e49be124852704cdca6eb55350e63aefba00af2d2fad2dce`.

The first CPU-isolated 11-configuration launch used the normal proof-first
path.  Its 33 solver processes produced 5.4 GiB of incomplete raw DRAT in
about four minutes, projecting tmpfs exhaustion before the 7,200-second
limit.  All 22 process groups were stopped.  Their explicitly named,
incomplete output and scratch directories were removed, while PID and runner
logs were retained with `proof-first-aborted` suffixes.

The materialized prover now supports `--deferred-proof`: the search phase
discards its proof stream to `/dev/null`, and only a solver that reports UNSAT
is deterministically rerun to produce, compact, and check a proof.  Its
manifest binds the search log, search and proof-phase times, and rerun status;
the independent auditor validates these fields and rejects inconsistent
metadata.  Real two-cube smoke tests passed under iGlucose, CaDiCaL, and
Kissat.  Their manifest hashes are
`8fd97583a8e05e2fd164f5e3b5540b2f1fb717410850bd34b30d4c60ffca07de`,
`18cde70933db4aafddf73e137224b620d99bb2cee1105e49aedd2cf6ec423fee`,
and
`cf6e652d880df342e40898530ad14d4d2bfb70fb1b897951819f494e1e959ded`.
All three independent audit logs report two VERIFIED / zero UNKNOWN and have
hash
`0eee6d01d56ab0f88f6485152c3fb391f0628bd87a45691cea293b1f21a0d90c`.
Regression tests also cover a search timeout and an UNSAT-candidate proof
rerun timeout; both remain UNKNOWN without exposing an unchecked proof.  The
ARM regression suite passes all 166 tests in 33.949 seconds.

The same 11-configuration portfolio was relaunched with deferred proof for
7,200 seconds: iGlucose plus CaDiCaL and Kissat at seeds 0 through 4.  The
single J326 cube uses 11 solver processes and the two J297 cubes use 22, for
33 single-core instances under 22 wrappers.  After 15 seconds their scratch
tree occupied only 88 MiB and contained materialized CNFs rather than growing
raw proofs.  The screened parents remain stopped so these solvers receive
their full wall-time CPU share.

`tools/analyze_screened_split_budget.py` independently hash-checks the stored
screen tables and replays them at a smaller candidate range and time cutoff.
For J326 rounds 529--545 and J297 rounds 414--430, a 0.1-second replay over
variables 450--700 remains feasible for all 51 parent occurrences, with at
least seven solver-agreed one-sided contradictions per parent.  The analysis
JSON and stdout-log hashes are
`86ca692aca6dc4a7f112739a0c04a04328fda7834d99a7b0a2fdbd132ca42f4c`
and
`a0e53768238d06ea120f8afe70e47a9f70f3d8fac57621a947f78f87d0fff55c`.
Together with the observed 0.05--0.08-second checked contradiction proofs,
this supports a next chain segment using a 0.1-second screen and the existing
0.2-second proof quick pass.  This is a reproducible scheduling optimization,
not an UNSAT result.

For candidates already exposed by one of these complete screens,
`tools/refine_queued_binary_cubes.py` avoids screening the same variables
again.  It merely chooses the first unassigned queued split for each parent;
the standard complementary-refinement audit and fresh materialized DRAT check
still establish every accepted step.  Thus the queue is a scheduling hint and
cannot turn a stale screen result into a proof claim.

The state-545/state-430 screens yielded two disjoint reusable ranges:
variables 450--700 supplied 29 queued J326 splits and at least 36 for each
J297 parent, while 701--800 supplied another 17 and at least 22.  Their replay
analysis JSON hashes are
`28c4c7e40ffe70a13ac5a498c4a8359476b6ff53a6f48c0d4e283790001e3239`
and
`e6a8a307346ef3530f32260a71365cdecb5e9099ee08c2974b69570112d5f49a`.
Every queued split was then rerun in proof mode, compacted, and checked.  Two
stable segments advanced J326 to states 574 and 591, retaining one UNKNOWN;
their audit JSON/log hashes are `0f3ef8b5...f6a2` / `4367814f...6aec` and
`29550bc2...ba61` / `e3fc21b2...f950`.  The matching relocations v43/v45 have
hashes `077b8c3f...c1eb5` / `27d66247...55d1f`.  J297 similarly reached states
466 and 488, retaining two UNKNOWNs; its audit hashes are
`7f7a2aad...0801` / `ae653aaf...bf29` and `042ba075...6d5` /
`fd8993dd...2a5e`, with relocation-v44/v46 hashes `3e835d99...0c9c` /
`29d5355d...3998`.

The deeper exported frontier hashes are
`dd6e4889c10333c494706e82cc751ab026e3d0e6179f557424614bd8a7b5b6e5`
for the one J326 cube and
`375ed2ee5061ee92489d00bf8f25a6b08e3ae685062b78cf30f0ce7abb2a5479`
for the two J297 cubes.  Their export-manifest hashes are
`e5bf1be1e254960fe0fd1b2c750693021889eee5806aa4825a262fec1185508f`
and
`0195b6d095adb4cf06ae68b45c2d3533ec609800dc191e3b6ce43d70c141f237`.
The shallower state-545/state-430 v2 portfolio was superseded after about 34
minutes with no manifest or deferred proof rerun; its PID and runner logs were
retained.  The identical 11-configuration portfolio is now running at states
591/488 as v3: 22 wrappers drive 33 single-core solver processes, with proof
generation still deferred until an UNSAT candidate appears.

A one-second replay of the earlier complete screens recovered another 22 J326
splits and at least 24 splits per J297 parent.  Each selected split was rerun
in proof mode and independently replayed after relocation.  This advanced J326
from state 591 to 613, retaining one UNKNOWN, with audit JSON/log hashes
`b9268c7c2df861fefb9941dcf60397f35b54b62730342941f78e7abb337e9e44`
and
`b0d70b5dd57989529db2b9e001d28afe098ff404e0b1f87e005f822304f09853`;
relocation v47 has hash
`70bc01b86e476f06ab6d4b7db05ee82ac7f32e50ec728d2e103c71978ba96a63`.
J297 advanced from state 488 to 512, retaining two UNKNOWNs, with audit
JSON/log hashes
`638c9e8aa8393794f824d0a585336bea189683487089c98391562d133ce7c957`
and
`ca3929b17f45144abc44b131d4f7b0c38a1575991703fbb18847399fa52678aa`;
relocation v48 has hash
`ea72c39ac270084c603ceb42ed0f8d190173bb9a8415e871466303ae82a06f40`.
The source screen-analysis JSON/log hashes are
`fd209349241a85fce2798cdd169b99dd9be9bc7a390695e447adf3dc1088fd98`
and
`b44d837f9c9aaf6a2f1492115af8304de2b962000160d6a37f496c341d2976a6`.

New 0.3-second screens at states 613/512 found two common J326 candidates and
118/79 candidates for the two J297 parents.  Their combined analysis JSON/log
hashes are
`953b8c9c4a0bcdd3a5c8e3f1b632bb185f10dab9c503c989827c8f8bf181f21d`
and
`4effa3d18e3c6a2b9cc42ebf478fd8b54beabf5e3be0dd19258d8f345ee394ba`.
Fresh checked segments advanced J326 from 613 to 615 and J297 from 512 to 591.
The J326 audit JSON/log hashes are
`e7b352b89f685746cd26216c6a7ff20a96f52c2dc411bfd05861220d137ac559`
and
`0f9f8a7c608aec0313b4650ff874ea068806215afa12dd5044810a2f15e204ad`;
relocation v49 has hash
`e2422c77c86184562664ded43227061dbf7e9cd7e38842f6c791c1598dbc4cbb`.
The J297 audit JSON/log hashes are
`414605d39d08c9c46e9811012afefbe679f9c6c9df90200a7398b54e52cb3d1d`
and
`ad266ffb6484ba06fa3a9fe15e1241c3d5fab62d1410a641ae0577fc5718adf2`;
relocation v50 has hash
`a985e515620637f14019f2eff8eeef937c1a380ccbbb4e63223d407becc667b4`.

A targeted state-591 J297 screen supplied one additional common split.  The
resulting checked round reached state 592 with two VERIFIED / two UNKNOWN;
its audit JSON/log hashes are
`5f65a4487867d4329613e068d046ccb1f8d94c36c6165e00fe27837aa9aa9c6e`
and
`1523ca6f434c91c68b03efaf81c5ecf117d076c6e82a88df383540c844fa9e7f`,
and relocation v51 has hash
`c5f5812c1f42c74dfd5e6e0fe3c8867b5b409b2ee46aa8af55309bc6e21319b7`.
A subsequent 0.3-second screen found no agreed candidate for its harder
parent; J326 state 615 likewise had no candidate at that cutoff.  This is only
a scheduling boundary for those probes, not an exhaustion of either branch.

The state-591/488 v3 and state-613/512 v4 deferred portfolios were superseded
after deeper checked frontiers became available, with their PID and runner
logs retained.  The v5 portfolio searched J326 state 615 and J297 state 591
using 22 wrappers and 33 single-core solver processes.  The J326
ICNF/export-manifest hashes are
`0e82380295183629f344394a91e2d6fb8de5915a54c208153f0510d80bedc7e4`
and
`3dfa1bcf37a78ac8fa8ee445d0b18cfd32d1af4c85d671f6b03df19133bbc707`;
the J297 hashes are
`2f7919edfc974d1de6ec27b12f0b0f070e24d4a24587253bbacb4bdcca11275c`
and
`dbe98b1954dac937351e0085e4095d50df6687e54eb8e7fb0ccfb1f30245dd81`.
All 33 attempts reached their 7200-second limits without reporting UNSAT, so
no deferred proof rerun was triggered: J326 remains 0 VERIFIED / 1 UNKNOWN and
J297 remains 0 / 2 in this portfolio.  The 22 terminal manifests were copied
from tmpfs into the persistent `runs/` directories and independently audited.
Their two 11-source composed manifests have hashes
`162bc246d80fe92073799c614c5db673e151cc5d3d581da72f9a0aa99e1be503`
and
`0b4923d220c0f6734f79e341196a6eb5423e80628883853b2132fad8cbc43707`;
the composed audit-log hashes are
`3d9c660d9fe1ad748481036a6378c600bbec37efa5e948ac800d08be7a4e6508`
and
`3f8f88e02ae9c2005b178d357544c6a7f2b807f8201e8e9f794c8ea16a08961b`.
The attempts total 80,721.433701 J326 solver-seconds and 161,442.883602
J297 solver-seconds.  The one-round state-592 J297 checkpoint is retained,
but the v5 portfolio was not restarted for that single extra unit constraint.

An independent four-segment/four-proof-job replay of the candidate chain
through J326 state 591 and J297 state 488 has passed.  The candidate-bundle,
audit JSON, and stdout-log hashes are
`136074dbfc712a0debc9423d0c42f048ad5b937a3ecbcb9e4d57a1f9e51a7d1b`,
`99e3b82cf096a45a9fe858de36ae61db9b2b9af18cc1e4c5d695779db4ef1dda`,
and
`8766afca28de2ad193e9207ccd7d3f1ddcf30a3ffccdca1cc1594398436e9ee4`.
The terminal frontiers are two VERIFIED / two UNKNOWN for J297 and one / one
for J326, so `all_cases_complete_unsat` is false.

The one-sided failed-literal route was then replaced by one explicitly guarded
frontier-growth round.  CaDiCaL lookahead selected variable 5581 for the J326
cube in 0.196 seconds.  Both children remained UNKNOWN after the staged
one/five-second proof attempts, so the complete binary cover was adopted as
state 616 with two UNKNOWNs.  Its state and independent audit JSON/log hashes
are
`fa87326d4e7c98ebf8631abfbb80e1a07181b2e7d2d6976b50f73a777be3c128`,
`99ddd8e6e76db24821a853c1d2cbe717ac900a66f8fb5f30ce21a07e5d934666`,
and
`b6d766dc06a590db26b72c0f1edda4e0e49ae0d8f64310723948723ebf668db6`.
For J297, lookahead selected variables 7264 and -1140 for the two parents.
The positive 7264 child closed in 0.118 seconds with compact DRAT hash
`49bfd2097786f5ca1b5b651d3fc6d2aa694a495d579ccecbefb4cc14640ca54b`;
the other three children remained UNKNOWN.  The adopted state-593 and audit
JSON/log hashes are
`13397257a60c60eeea83b18c9f948c878e976e3823047db4c07310f3a26bcdad`,
`b1328db490b8a01740c9985c171179802116aa6e1e37a84a62f1aed4d8274899`,
and
`1327294758f4fd1b17faf80bff9e4aad308e22d9f4ee68cbdb5302707bc0e244`.
Both one-round segment replays verify the guarded-growth record, binary cover,
and every available proof.

The current candidate whole-chain bundle now includes every queued and growth
segment through J297 state 593 and J326 state 616; its hash is
`cb4047e1a5581c621b2e90eecbfc5943ad83df57c59dae533ff42c82dd2eb9da`.
The matching strengthened-parent candidate has hash
`ed0ad6ee801d49cc58c196ece68ff1df3039d705d5491b70c274153bd90ff9f0`.
The intermediate v8 replay was stopped before it emitted a manifest, avoiding
a full duplicate audit of a bundle already superseded by this guarded growth.

Dynamic CaDiCaL lookahead then found useful auxiliary-variable splits outside
the screened primary range.  From J326 state 616, three consecutive rounds
each closed one child of both parents, keeping the frontier at two VERIFIED /
two UNKNOWN through state 619.  The state hash is
`9e4f37698018df336752bfd9f5897f6eebb348c1c4ca4aacd18dbdb8c7e07e15`;
the independent audit JSON/log hashes are
`42bcc27b3a6e8b7c5cb515cf73bc43a2a676b255babfdf0c694bb2cd7995e89b`
and
`7115a317563bf71f951386b987939f0f9e33df58560b900cbf582a354508c886`.
The next round grew two parents to one VERIFIED / three UNKNOWN and was
guarded before adoption.  Its explicit adopted state and audit JSON/log hashes
are
`5f64f90d6a2d0b01a7da5b9771cd878557aacffc18abd1fb41fe92b91a597b84`,
`8ec8b0494ad3298ac7bd4c2dd836336577d63b43af21ffcb7d078e193a3022c1`,
and
`75a7038d6a3b8878c6d3abe59407fe9d673272875ab457979e04c9ae6f2691b4`.

J297 similarly stayed at three VERIFIED / three UNKNOWN for two rounds from
state 593, then the third guarded round produced one VERIFIED / five UNKNOWN.
The adopted state-596 and independent audit JSON/log hashes are
`9cf105c3b6c284be893989a60edf9a0b4309442e5b5a33a3f29d6de00ca7fef0`,
`323588f825ab6a459ecaea30febca9589bc7d8084e7d2bd21c4c3bc54750dc2e`,
and
`5551970e478d110f836a6f3fa96ba02e84d081f698be003f3be4f950122e15d2`.
This establishes an exact eight-leaf cover across the two strengthened roots;
it does not establish that any of those eight leaves is UNSAT.

The v9 whole-chain replay was stopped after about six minutes, before it
emitted a manifest, because these newer segments superseded its endpoint.  The
current v10 chain and strengthened-parent candidate hashes are
`e866fb2df2a1ce55ff80fbc8963b8cdbf820a2402d4b61334c676ffbc6a717c9`
and
`cfda033cc086ad073f21f2380a3d1a3ab9e5b7caeab21528803f32dcd6cd8aff`.
A fresh whole-chain replay is running at nice 10; the parent replay is gated
on exact terminal rounds 596/620 and counts J297 1 VERIFIED / 5 UNKNOWN and
J326 1 / 3.

The final J326 ICNF/frontier-manifest hashes are
`0ab3839e36b4a319f443b694ab51ca6bbcff088a0af491bad34c678ebb315574`
and
`4a244289d9e0a29181132ed110ae9ad81870441bd1f41a0ade7415a81d606304`;
the J297 hashes are
`a88d7a86a7134a9cbb1d1abc50540d73dea9be38fda862d09bcdba7f75cfde8e`
and
`4a86b9650888d238c32f0ccf58b0cad81e78bebe749b8b30a2a223033c6d1ffb`.
The original v5 portfolio subsequently ended with all 33 attempts UNKNOWN, as
recorded above.  A nice-15 CaDiCaL seed-5 run searches the earlier 2/3 leaves,
while a nice-15 Kissat seed-5 run searches the final 3/5 leaves.  These
comparison runs use deferred proof; subsequent verified results are recorded
below.

The seed-5 CaDiCaL comparison then closed one of the three earlier J297 leaves.
Its deferred search and proof rerun took 207.942122 and 135.185220 seconds;
the 28,442,046-byte compact DRAT has hash
`2cac4b7776c7ef7ce550b5c477b91a1ab4cc4326f0f509627d077caccdcfac2c`.
The stable producer checkpoint and its independent replay log have hashes
`7e71ac80178debe22337ff8aaf62bdca9839ae5e7c149f58d3c33bc8c50d5388`
and
`920c23df17293ab33b634b630e4acfd3e6fc34342cd13f46b9b11ae063c30ad5`.
Exact-family composition with the state-593 primary manifest raises that
boundary from one to two VERIFIED rows and leaves two UNKNOWN.  The composed
manifest and independent audit-log hashes are
`48438b33566956ef8558c3b3889fde91a90e5236b744340e577f92569ec55d6d`
and
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`.

This exposed two provenance bugs before they could enter a stable bundle.
`finalize_materialized_progress.py` now copies a completed row's deferred
search log, and both proof composers copy and rename that log together with
the selected proof and checker records.  A mixed composed manifest may carry
valid deferred metadata on an individual result even when the top-level
producer was not globally deferred; the auditor now checks that combination
while continuing to reject missing metadata from globally deferred verified
rows.  Focused regression tests exercise all three cases, and the full local
and ARM Python suites passed 168 tests at that checkpoint.

The final-five-leaf Kissat comparison independently closed both children of
the same ancestor.  The compact proof hashes are
`a2df8c7c2f2347b4a52f42f75548d044978e96cfed1a3f5072aa0b68e877a952`
and
`7be0d1c2ed7210af40c5642411dba40ed311741ab4d387e74f5b2bc2aacfb8f5`;
their sizes are 4,023,290 and 33,892,870 bytes.  The second used 170.466188
seconds for search and 234.160600 seconds for its deterministic proof rerun.
Checkpoint v3 has manifest hash
`e3e4ccb9d5a10a50d304057489d016288d8c05cac45b06308f25a0ea2b9f1c4f`,
and a separate replay accepts its exact 2 VERIFIED / 3 UNKNOWN summary.  Both
child proofs are independent corroboration but are redundant for frontier
size because the CaDiCaL ancestor proof already closes their union.

Restarting dynamic refinement from the stronger composed ancestor boundary
kept J297 at 2 VERIFIED / 2 UNKNOWN for two rounds through state 595.  The
next fully checked candidate had three UNKNOWN descendants, so the growth
guard retained state 595.  The state, terminal manifest, and halt-record
hashes are
`4df3cb425880c277c51bd871d81e781306217afdad22416b479b50222f1a8652`,
`564e6003bd2b7a894abe912acb8aced7a2191a69b7dd28aef68feb1d201354e3`,
and
`a8767ec37a64401ceb88d656ac4824a31c70f56aa79698131c6651e4c76ebef4`.
An independent replay checked three manifests, two refinements, and four
refined parents; its JSON/log hashes are
`872d5a740483597527be18b8002d58d1bc52804ad3e1d45fb0d3d881b3d87d58`
and
`92d307e013c573df7ea40cb80aaaf71c8794501a2a8a3dc7e4f2be9a4667dad2`.
The resulting two-leaf ICNF/frontier-manifest hashes are
`429c551b028a6d231fb351952a0536afbcb01260637a007818fb51ca66d2f1b6`
and
`c8cbc477c3a2d61c65b3f54e52a801cc694bd4ac52282e2f6b4c3d7aed7e6f89`;
a new seed-6 Kissat deferred run searches both leaves.

The v11 candidate replaces the wider J297 endpoint by this independently
replayed exact-cube retry and continuation while retaining the J326 state-620
endpoint.  Its chain and strengthened-parent bundle hashes are
`4dac9958ffc1049667e81ce4bcd2dc73a629bd7bb17cb1a85777a273937e7c1d`
and
`93ec676244cde08f8e2529902d79e948d785bf86022d8ccabd9e61c44d3492e9`.
Whole-chain replay is in progress and gates the parent replay on exact terminal
counts J297 2 VERIFIED / 2 UNKNOWN and J326 1 / 3.  The v10 replay continues
independently so already spent checking work is retained.

The v10 replay eventually stopped without an audit manifest at the J297 v38
segment.  This was a certificate-path spelling defect rather than a proof or
cover mismatch: the recorded manifest, cube, parent, and proof hashes and all
counts matched, but the lineage stored its source and output paths relative to
the repository while the bundle auditor supplied the identical absolute
paths.  The parent gate saw no accepted chain manifest and correctly refused
to run.

The chain auditor now compares a recorded path with the expected artifact by
resolved identity and then continues to require exact content hashes, counts,
cube order, refinement structure, and DRAT replay.  The same rule is applied
to frontier lineage, binary-refinement manifests, child bindings, and adopted
growth/halt records.  New tests cover all three certificate layers; both the
local and ARM full suites pass 169 tests.  A real absolute-path replay of the
previously rejected v38 segment passed and reproduced state 593 at 1 VERIFIED
/ 3 UNKNOWN.  Its audit JSON/log hashes are
`3bf8be5f1aab454dc4e6deb9b9e783c8e1c6bcc6940971ad7306b3e21e79d39a`
and
`98e0f8bb1b275b216ca08288b027853e84d7715022f404a7799587af2aabae72`.

The first v11 run crossed this audit-code update while in progress, so it is
retained only as diagnostic work and cannot trigger its parent audit.  A fresh
v11-normalized-v2 replay, started entirely from commit `22e0f7f`, gates a new
parent replay on the same exact terminal rounds and counts.

Further guarded continuations produced deeper constant-width boundaries.  For
J326, one round split all three state-620 parents and checked one child of each,
ending state 621 at 3 VERIFIED / 3 UNKNOWN; the next candidate had five
UNKNOWNs and was rejected.  The state and terminal-manifest hashes are
`290b834d46ebfa25a654cd9140d51a4233957d62166ac8af6430317e1b7cefba`
and
`714fae25f648422343d75ebaa8f50a4c24481ae7294a17afd81b9c01506ee4a4`.
Independent audit JSON/log hashes are
`da8d2cddbc0818e2dc97ee03cfaf38d43f946df5725b2fb78139253a58b05c91`
and
`91e2825b0b9e02671d3f571b69c0997a68833e08dcb346e26456dbdb6b6bd006`.
The three-leaf ICNF/frontier-manifest hashes are
`5b7e202134bb2f007e670168cb653faae63a58b994f51d1b421722e065e9b57a`
and
`3de094e27c5385a06a85b207fbd6e68d381b28caf366f1802109576ca732af25`;
a Kissat seed-6 deferred portfolio now searches them.

The alternative J297 three-leaf growth candidate remained at width three for
three rounds through state 599 and then rejected a four-leaf candidate.  Its
state/terminal-manifest hashes are
`86a4977bc513e4252a8fd12d77bf9a1ecd8ea9518e93f2b87b962d58c39a8621`
and
`42188f501e4725b377023fa675fa6fd08ed8b171dcb3bd9517431a46581df596`;
audit JSON/log hashes are
`b928e3cc74ac3673e1b3f5eb43c10981896e97a78ebb4a15da5f93932bc76f7c`
and
`99b9bf9851a6ffc850cc42d9401f7f2a6c6f20f37f37b00f735e071e5bed2de1`.
This does not replace the smaller two-leaf state-595 boundary.  Its exploratory
three-leaf ICNF/frontier-manifest hashes are
`f540cd9983f0b546faea71151622b094f17598f492ca31026d6fecaa0296c2a6`
and
`dd3bfddb09ea2af3869fa3ab7a9e8a117ebecdc76e49b71f5947b9895a243fe4`;
an iGlucose deferred portfolio searches those descendants.

The stable formal candidate is therefore frozen at v12 with J297 state 595
and J326 state 621.  The earlier v11 replays were stopped before emitting a
manifest, and their logs/PIDs were retained as superseded.  The v12 chain and
strengthened-parent candidate hashes are
`99e186141f5957c40d0d68eca061146dd5de3a1046e8230f684a802f7505edb5`
and
`c8b7a07dc207597c07dfeb3ca5ff4496b705890e8f950a53bf349f4911e22f1e`.
A clean whole-chain replay gates the parent audit on terminal rounds 595/621,
VERIFIED counts 2/3, and UNKNOWN counts 2/3.  Later same-width refinements do
not supersede this frozen candidate.

One further diagnostic continuation immediately enlarged the already wider
families from five to six J326 leaves and from four to five J297 leaves.  They
were not continued.  The remaining logical CPUs instead run low-priority
CaDiCaL seed-7 searches on the frozen J297 two-leaf and J326 three-leaf
frontiers, alongside their Kissat searches and the exploratory J297 iGlucose
run.

The clean v12 whole-chain replay passed after about 54 minutes.  The audit
JSON and stdout-log hashes are
`42b677efb145bbb90c2001433371dce2bdd26e2fc721d4de912f19e40d3bee0a`
and
`0500d3813cdcd383979d1732f189e053c81cb9566404c021c969112e9356d320`.
It independently checks 25 J297 and 28 J326 segments and reproduces exact
terminal rounds 595/621, VERIFIED counts 2/3, and UNKNOWN counts 2/3.
`all_cases_complete_unsat` is false.  The exact-count gate then started the
strengthened-parent audit, which independently replays this chain again and
checks the false-polarity backbone composition.

That v12 strengthened-parent audit completed successfully.  Its audit JSON
and stdout-log hashes are
`ddc04bfe1fc7cc259c9e960a105d27a9c1f71041e2ed8fa00f9d810cb9839336`
and
`a2ce27448fe8ee397f2fccd52d1a14057792242603fe131c98d3648f3476db52`.
It independently verifies all 193 J297 and 178 J326 false-polarity backbone
proofs, confirms that both strengthened cubes are exactly the corresponding
parent plus 15 certified backbone literals, and replays the 25/28 chain
segments.  The remaining terminal counts are still J297 two UNKNOWN and J326
three UNKNOWN, so both `parent_unsat` fields and `all_parents_unsat` are
false.

The state-620 Kissat seed-5 comparison subsequently closed two of the three
J326 UNKNOWN parents.  Their compact DRATs are 174,534,017 and 176,834,884
bytes with hashes
`18d4ca9953c4996fea9dfbe465ad0eb4748dc8a7f8ba237f14d7d37f98ff3742`
and
`6277c86f2da94f4aef796c8de29e46078db35b35132253d687e4525d538c5dbd`.
The persistent checkpoint manifest and its independent audit-log hashes are
`9abf9211351ea35537ab42ffefd3f142558a14ce35ba350117084f672846522e`
and
`ef6e9aab2129af37b68d6a323e710f1204f35ba38566a6564df2168ebc0d15ad`;
the exact-family composition with the audited state-620 primary manifest has
hash
`e71c5ea159d088b0a8fd382cd7ecae2b687ba5d8af21a0ad2e0f919df2894692`
and leaves three VERIFIED / one UNKNOWN.

Restarting the guarded chain from that composition split the sole remaining
parent on variable 6498.  One child closed with a 79,371-byte compact DRAT of
hash
`cbafb9b8e5382bb4467765162e2d598525bcf8e892629c2e1d5cf82cae65dfd9`;
the other remains UNKNOWN.  The state and terminal-manifest hashes are
`4b3d488acb04b9a5319bce8a774ca53cea7ee88a63a2be042817e73b5c1e8ca3`
and
`7d657b87ee71ef185bac43eaa6ae6fdc21dc02aaa21f394639b6efef65eebc67`.
An independent one-round chain replay checked both the exact-cube retry and
the complete binary refinement; its JSON/log hashes are
`2e76182425a370ff0a0ae341953c3cc652d5c1cbd5e699840044bac853975b6b`
and
`d99f98e72d96eb75479592363572ed7a08100452a6f83e1a45c418ce7f780ac8`.
Thus the certified J326 frontier has been reduced from three UNKNOWN leaves
to one, but J326 is not yet UNSAT.

The previous state-621 split of the same remaining parent used variable 9448
and left cube `2ff9dd8e...` UNKNOWN; the new split leaves the distinct cube
`8f640a56...` UNKNOWN.  Both are now searched independently.  The selected
old-leaf ICNF/selection-manifest hashes are
`3075767422be32691a67c0142ceabb31b66c70e40d23bf18a980bc1a4d0c8264`
and
`c1f3c74359dafbda2c039edee09f91cb83524ea5a831964b22a88adf88bc0c52`;
the new-leaf ICNF/frontier-manifest hashes are
`d97568c428257cdf27ddc0e9238ec0c4b6bc6ca116ea90dc578fddea8ec50234`
and
`e4553bcc908a21d97b2a46cd7272ffd7b800fa73d5e91f0f223c5e080091e488`.

The resulting v13 chain and strengthened-parent candidate hashes are
`01996f776c5a211442532e1ee7521bbb454389fffa19d3e4fa2438f469b02ad7`
and
`28845912c868616ce387bd258e0a3b3a1289761287c9a2260fd31b1df4ae5f9e`.
A fresh whole-chain audit passed with audit JSON/log hashes
`ae4e7cb2bfa6fc79ba8270979dc720df363c62e2ec99999c7173ae394e502a74`
and
`8299797ef795dee9a0fdad5a9c5dee46d3795cb12a4837d8600105c16f05d18d`.
It independently replayed all 25/28 J297/J326 chain segments and reproduced
the exact terminal gate: J297 state 595 with two VERIFIED / two UNKNOWN, and
J326 state 621 with one VERIFIED / one UNKNOWN.  The bundle hash recorded by
the audit is the expected `01996f77...2ad7`, and
`all_cases_complete_unsat` is false.  The exact-count gate then started the
v13 strengthened-parent audit.  That second replay also passed, with audit
JSON/log hashes
`b2afc593228d6eb4954da5ca8a96c8247605df4511ff1ea9bce4594928494f41`
and
`15e3e4d5d6a75c3f18a07a36de90490aab85ce794d8e5010d52145c411cc3c9c`.
It verified all 193/178 J297/J326 backbone proofs, both 15-literal
parent-strengthening bindings, and the repeated 25/28 segment chains.  The
parent endpoints remain two and one UNKNOWN, so both `parent_unsat` fields and
`all_parents_unsat` are false.

An independent CaDiCaL seed-5 comparison also closed the first child of the
earlier J326 state-616 two-child growth family.  Its 227,111,943-byte compact
DRAT has hash
`8d29f3afc46582a26bfb390525166039e64529f28f8ce91dcf9019092f697190`;
the final manifest and independent audit-log hashes are
`b7632ad25faffbdc08c2a06fd6b30808311c8b84e6753492581ed053cd808318`
and
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
The replay reports one VERIFIED / one UNKNOWN.  This is useful ancestor
corroboration, but the current J326 UNKNOWN follows the other state-616 child,
so it does not shrink the authoritative one-leaf frontier.

On the alternative J297 state-596 family, Kissat seed 5 later closed a third
nontrivial child with a 256,128,846-byte compact DRAT of hash
`2aa0eaa9dfa5bce85b02b7d34aba5f8ef47a04ab5400b95c7b36251df5907a10`.
The five-child comparison manifest and its independent audit-log hashes are
`9bfa356374fc978a3557e38888d6de994a75ba07a23cc8429e037ab170e8e655`
and
`78cce30ee069247720e71202dff0c1082ec61b4e230729b8865d22dba53fafb9`;
the replay reports three VERIFIED / two UNKNOWN.  Exact-cube composition with
the six-child primary family gives a four VERIFIED / two UNKNOWN seed manifest
of hash
`a80e3eeed712e6eb63c66c7c3d7c31c9d48ae718b2347725194ee296684d2582`.

A guarded continuation from that composed seed retained two UNKNOWN leaves
for three complete binary refinements through state 599, then rejected the
next 2--4 growth.  Its state/final-manifest/halt hashes are
`a3a069075d881bb68e640e949026c9a2ff2bfcb8ac053483e056fba0a14dbcfb`,
`b130bfac8a59431512099fd757f4743091d7b7fcc4d971491dd2ca1af0584c24`,
and
`c5dcf2de5457c70e591e7c105155575290bdb700009761344f0ae5c8fa516394`.
Independent seed-and-chain replay checked four manifests and six refinements;
its JSON/log hashes are
`518a5f5d61c4c7124352456468ad573771e2637589cd73c347ddfdeac4011bd9`
and
`e9d2bb8b9fba9c0b5a8aba13ef53656277e572005e221c7c1eb113d3ed8c6233`.
This is a deeper two-leaf alternative to the state-595 formal endpoint, not a
reduction in leaf count.  The state-599 ICNF/frontier hashes are
`112c1dfff4f10f4a4a3366ad688ae9938cba15116864e9c2ad4b7a19024c629e`
and
`444783cd4d172ee86d587fc83751b393f3bf3a120c73abf08d4620f8d769a3e1`;
iGlucose, Kissat seed 11, and CaDiCaL seed 11 each subsequently exhausted
7,200 seconds on both leaves without a proof.  Their final zero-VERIFIED /
two-UNKNOWN manifest hashes are
`8ae55e41dae9a285db523c6f33286385cccd4a5ef916d5cb63c602bab978bc4a`,
`6dac685e4dd87978a98ec17adb5ce35329944705e08825ddd577a6c756126439`,
and
`f60e2fd43e969ffb2e53f56e55ebe8d32901751ed3ee2f4055d24ea9107ff8b6`.
Exact-family composition and independent replay have hashes
`430091bb42ff15c98b79c036611e3db1e989d4c968c7497e7fa0bb65b0b93862`
and
`3f8f88e02ae9c2005b178d357544c6a7f2b807f8201e8e9f794c8ea16a08961b`;
this is negative search telemetry, not a certificate for either leaf.
The v14 chain/strengthened-parent candidates that replace v13's final J297
segment by this audited alternative have hashes
`d292cc97dc5bcfa975c0514e26ab172fec813c116496be1a4d4ecc1b2c83d94d`
and
`29611d8b6b61391e5cfe94952aa155f3f1e7f51100b04bd64588d16b94b0320e`.
They were superseded before replay by the stronger v15 candidate below.

The iGlucose search on the rejected J326 state-622 two-child growth first
reported UNSAT for child 0 in about 72 seconds, but its original launcher had
not enabled iGlucose's certified mode for the deferred rerun.  The resulting
six-byte output was rejected by `drat-trim` and was not admitted.  A corrected
`-certified` retry reproduced the search result and generated a 96,074,160-byte
raw DRAT, compacted to 30,387,786 bytes with hash
`6c6d0413937c8e5a88dfa78a78c204bc4240532fd018763372d3e3efd52513c8`.
The one-child proof manifest and independent audit-log hashes are
`ea2a5140b8a573162d1cf66b9de159f9379e5c603837caefbf6fd3dbad4b5d2a`
and
`07521dbcbd17729a5484e9074d6fd0768dfdfc6e92c49eab2ccc038b4c25ca8c`.

Composing that proof into the complete variable-913 binary split advances the
alternative J326 chain to state 622 at one VERIFIED / one UNKNOWN.  Its
terminal-manifest/state hashes are
`d05b91b51e239d8849bdf1f53273964986a9e6a89edaa7175ebc0cf83c54dbee`
and
`65324d323e1818986c07c9e52d74978e4806f1b7e82988fb6b533fe6af0b7609`.
Independent seed, frontier, refinement, and proof replay passed with JSON/log
hashes
`54ae9423766f4915540367f90173d24f28bc544cb5d63ebea1f57770ffb68630`
and
`980e3bb5517abef666f710f89fb4e4e8fd3c57001a954558a538d831fb0afdda`.
The new single-leaf ICNF/frontier hashes are
`0e399f0ccc20fc64bbccff90c09aa653e306bee783e0028bfda806b1bef4acae`
and
`ab696fdd46e198072b8a53030cbde23a305a35929b39ff5fafd87bc21b064e6f`;
Kissat and CaDiCaL seed 12 search it alongside the existing iGlucose run.

The resulting v15 chain/strengthened-parent candidates combine J297 state 599
and J326 state 622.  Their hashes are
`80bfa1a06beb28511140c7f5119884113c0f980cbda250a17dbd3146501738e6`
and
`e0717fb22e54ffd1c34758509b66234e72b64f57006d7998a03d19e47d0549e6`.
They supersede v14 before audit.  After the v13 parent replay passed, the v15
whole-chain replay and all of its live descendants were promoted from nice 16
to nice 10.  That replay later failed closed without emitting an audit JSON:
the v42 J297 segment was accidentally paired with the two-UNKNOWN v47 retry
manifest, although v42 was generated from the three-UNKNOWN v38 manifest.
The auditor detected the resulting `UNKNOWN frontier mismatch` before
accepting the segment.  Replaying v42 separately from its correct v38 seed
passed three rounds and nine binary refinements; its audit JSON/log hashes are
`323588f825ab6a459ecaea30febca9589bc7d8084e7d2bd21c4c3bc54750dc2e`
and
`5551970e478d110f836a6f3fa96ba02e84d081f698be003f3be4f950122e15d2`.
Thus v15 is rejected as a bundle-construction error, not as a failed DRAT or
mathematical claim, and v13 remains the latest accepted full parent audit.

One further guarded J326 lookahead split the state-622 leaf on variable 676.
Both children remained UNKNOWN after the staged six-second CaDiCaL check, so
the 1--2 growth was rejected and state 622 remains authoritative.  The
candidate-manifest/refinement/halt hashes are
`82b314050683cf2944b722e3099faaaef750f560aa53e6bfa3745423f7b45040`,
`ba62a1c78bc3bfac50995362cb16dba199de9c1a2b88b5f91711947847fb86fb`,
and
`3f70fdd657e8341917dfef667331542ca342ea4614976e00a61fe2564cd3a51d`.
Certified iGlucose and Kissat seed 13 now search both rejected children; they
are exploratory routes back to a one-leaf frontier, not adopted chain state.

Kissat seed 13 and CaDiCaL seed 13 subsequently and independently proved the
same variable-676 child UNSAT.  Kissat used 330.942 seconds for search and
318.344 seconds for the certified rerun; its 59,869,386-byte compact DRAT has
hash
`281e126ff5cc6d112d8235f083bb156feb4c6d0c807d3f9d69304409ac693d28`,
and its frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`b7640280069471d1d9713d36544ce6119af972dd4ca136a4260a008c71010a7a`.
CaDiCaL used 569.137/562.470 seconds and retained an 83,167,625-byte compact
DRAT with hash
`89aedabf4e9165fc9f86c19e3c3e06d943400f93b4e83b6d8ef92987a1db1ed8`;
its checkpoint manifest hash is
`a0558636854fdda497a7fc3bfd6cbb0d6ea0d3613c02aa99db3d6c4e251560cb`.
Fresh external `drat-trim` processes replayed both checkpoints as one VERIFIED
/ one UNKNOWN; their identical summary-log hash is
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.

The smaller Kissat certificate was composed with the complete variable-676
binary refinement.  After correcting the directory name to record the actual
solver provenance, the composed manifest/state/refinement hashes are
`6e322353c54f46f1561581337938166bf235b6457bc6862388487401d407223f`,
`45ae9abe8f7952a76df25559c3040195005fe5b4b1e8f63aec8158b2fa1cd385`,
and
`acc4aba4df41be66843ed6178795a295945b90f1904f37d0886262dc31729d13`.
Independent seed, proof, frontier, and refinement replay advanced the chain to
state 623 at one VERIFIED / one UNKNOWN.  Its audit JSON/log hashes are
`8d267890c408e185398071c286cad37d8c06f15c0c728d06c5e22a4cde83516c`
and
`14b8819f434f6a2fa22292d6f803a63df808ce85d390cc3df7b9d2b38cf1a0d6`.
The remaining-leaf ICNF/frontier hashes are
`896290bd4ca35ec501da0f6a86a9829841c72a3577222fc1af8423419355c409`
and
`b986c2123925120f8ae6ca4df44af390d33948596b5644124067c39c7cc0bf8e`;
the original three state-623 searches remain live, with Kissat/CaDiCaL seed 14
single-leaf comparisons added at nice 19.

Version 16 fixes the J297 v42 seed and appends the audited J326 state-623
segment.  Its chain/strengthened-parent bundle hashes are
`7bd3c89b12d04270523e5210725b29d54b9339b715a188504d47a1bb0ff46a51`
and
`ca7ef4d50346ddbf18a45c4a420966c4c13a626fbe86e13975cb90c56f10c306`.
Cheap boundary preflight classifies the J297 v42-to-v61 transition as an
independently replayed exact-cube retry and the J326 v67-to-v71 transition as
an identical terminal manifest.  Fresh whole-chain replay accepted all 26
J297 segments through state 599 at two VERIFIED / two UNKNOWN and all 30 J326
segments through state 623 at one VERIFIED / one UNKNOWN.  The chain-audit
JSON/log hashes are
`cfeee70083975cdeeca65285e8d7bef713aaf71c4082b0e625206b17006b6f61`
and
`9d6d8bc66d48c27cfdbd8223f73094e608e26784c53001b6e7678479e1fdc244`.
The gated strengthened-parent replay then rechecked all 193/178 bad-backbone
DRATs, both exact parent-plus-15-backbone bindings, and the same terminal
counts.  Its JSON/log hashes are
`4857a6df4f4662976326e0e4a106037cce0633d69bdef447a6f927e6e962121c`
and
`1e5b518c0d2f8c94fc4a3596b0227a7086225f947884dbf2c85ffa221a271760`.
Version 16 is therefore the latest accepted full-chain and parent-audited
baseline.  It remains incomplete because those three terminal UNKNOWN leaves
are not yet proved UNSAT.

Appending the independently audited J297 state-600 and J326 state-624
segments gives v17 chain/strengthened-parent candidate hashes
`8760cdc03213f6bd5d564657db7d64c1041797c6fbd4df586dc1563619c96d0e`
and
`26000e7b4f46865322394114877cdd4af9b0f083ba2e5c96de9954bc78c6c2ed`.
The candidate contains 27/31 segments with exact terminal gates 600:2/2 and
624:1/1.  A fresh whole-chain replay and gated parent watcher are running;
v17 is not accepted until both complete.

The next guarded J326 round split the state-623 leaf on variable 5945.  Both
children remained UNKNOWN after the staged one/five-second checks, so the
driver rejected the 1--2 growth and retained state 623.  The candidate
manifest/refinement/halt hashes are
`566048d887b658b35c83294dedd0f4861481f2eb789136637b7b7db6e0ba89b9`,
`4843c51c155ee72dbc2b0eae7b90c12ef60092ced6639320dcd4c25e807f4b63`,
and
`7ce4afe0f8f8e0812af145973681a90a8b6b6cd4b770c1f47d938e0d9c698043`.
The complete two-child family has ICNF/selection hashes
`fa87f65defb5a431884aae8b7156c4a6610a9ad4d0499e96cea19808852e678b`
and
`3845229eed7cd1b5dcdaceb3aa6b7e0eccc7d76a0efdfaba4025d4032e3aa178`;
certified iGlucose, Kissat seed 15, and CaDiCaL seed 15 search both leaves at
nice 19.

All three engines later proved child 0 of that variable-5945 split.  The
smallest retained certificate is Kissat's 220,191,720-byte compact DRAT with
hash
`84406e874e45314749cc6539b21b92c276d350829e023187b45077fbdb98705a`.
Its one-VERIFIED/one-UNKNOWN manifest and independent replay-log hashes are
`7317a18121d073f887743c46fd6dec2a6f2019f2eb77427aef17026449068c5b`
and
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
Composition with the complete binary refinement and another full one-round
replay advance J326 to state 624.  The terminal/state/refinement hashes are
`7db9340bd9633f42acc8d7073b151bc4c894b94c21b92da2018fbf520991fbe4`,
`954c73c523aca9a5992769503e18859c48a5ed058fc64b1a645477f63dfcde81`,
and
`8117d57e4cf32d2fdeb489e942582af618f6d622917c23264a41e25beb3866f3`;
the chain-audit JSON/log hashes are
`c55300e515e1b6b3cb1938ed70d5d73e431eb21c8a92f4940e11fff9aa05b9b8`
and
`7daa29f48670a7ddc2f709f204c2512240dcbe10e104bb7936ed836b7f87c33a`.
The remaining child is still UNKNOWN and is being searched directly while a
guarded continuation replays the new seed.

That continuation retained exactly one VERIFIED / one UNKNOWN for four more
rounds through J326 state 628, then rejected the next 1--2 growth.  The
terminal/state/halt hashes are
`13de057394d117da8fa0621a88a9f9fb7dc68665ec9165c00147cb38e6e6d652`,
`3cf03d5c89b55201dd11fb111a6731373728b1ace6cd5a5c6792d6ce5cbc4266`,
and
`f9e3cdc1633cb4ec68833ec2b4d2225169f1a3e9138012a624ca3e579d207972`.
Independent four-round replay checked five manifests and four refinements;
its JSON/log hashes are
`8be61a539d2d5c5f4f0acbe1a36ab9b585e199f2da501868acc06cfd9758c677`
and
`313dd20f88075ffb55813afaef2446217510d2a6e77c77f0a4c1ee84eb611fe7`.
The rejected round-628 children/refinement hashes are
`f635572791fb4faac13facfd4fc44255fa38a3ed5f5c0cd103711f962946607c`
and
`fb81acd5a827eabba1dbbd032db4fcdcbdceb7938e419049acaf5165200dc16c`.
Ancestor-only state-623/state-624 searches without proofs were stopped and
their six cores moved to this deeper two-child family.

Kissat seed 18 subsequently certified child 0 of that exact state-628
two-child family.  The retained 209,926,094-byte compact DRAT has SHA-256
`f7163b62f9b5dd339af577239610fcd67a9fbcd5c192bab7aa5fee392901ceee`.
The frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`bb30565ce4b71c392779bf2ff6c2e85483e86dfffa623ccc42e59cd0d8a7c83f`;
an independent replay accepted it.  Exact-family composition and a separate
one-round chain replay advance the authoritative J326 endpoint to state 629.
The refinement, terminal-manifest, state, and chain-audit hashes are
`69df6169d3b477e480979a4650b1e5b088ec76cb95e8ef260daad2210e47ceb4`,
`bcc8e20f9c8d03d183eb4f85df902b08ff4ea3167bb610d2c24614ca156cf394`,
`a3cd162f249e62b6bab68de7d828f80faf077cb7b07726ce328bb684f446b65e`,
and
`ca4c8b9f622fa33cb530451425d5f84e4642f5f5f377c55e5be5837a76f293e`.
The surviving child remains UNKNOWN, so this is another certified frontier
advance rather than a J326 UNSAT result.

The recursively audited v20 checkpoint appends exactly this one J326 segment
to v19 while carrying J297 unchanged.  Chain and parent extension hashes are
`cdbb6097143c86ae98af5a9a008f90f5f3f1bddfd009444d853a4ba65360376c`
and
`9f47261932bb97a37ff043418667cc26479ff1a591cc1f01ba6e6f38beeb0001`.
Thus the hash-rooted production chain currently has 31 J297 segments ending
at state 606 with two UNKNOWN cubes and 33 J326 segments ending at state 629
with one UNKNOWN cube.  A guarded continuation rejected its next 1--2 split;
the exact child-family/refinement/halt hashes are
`203055cb91f29c65c46b91782539dfb6f272d98dea8cadcea028d87077e54cb7`,
`190b8c944b5110edda8390be46f6a93f4228ab80970b9315c5e5f5cda7c88e8e`,
and
`4902a9e7a500b069a766186d1c9f7f3491ed8e0d57b6201dc3a93cc4f15af5ff`.
Direct and two-child solver portfolios continue from this same certified
leaf without changing the authoritative state.

On J297, Kissat seed 15 closed child 0 of the previously rejected state-599
2--4 growth in 17.740 seconds and reproduced the result in 17.767 seconds.
The 3,906,881-byte compact DRAT has hash
`66dd7b972cffee7bd25953a3339feb728ae5ebf4cdc59b464118cbb569192995`.
Its frozen one-VERIFIED/three-UNKNOWN checkpoint manifest and independent
audit-log hashes are
`477b64a321ff94767c0bb1f0cbbb62e494418386f6ca35b25c2d9b2c1890c17a`
and
`d4663a77837b6d8bb809e059514e16beab078d460156ddbc68ee7ac2a57c698b`;
exact-family composition has manifest hash
`8f68b0b5ffd1effd5de7bae6a0004ccb5f40394bea295e58e05891d05e87a12a`.
Three children remain UNKNOWN, so this does not replace the authoritative
two-leaf state 599.

The complementary child of the same original J297 parent was then isolated
as a one-leaf subproblem.  A zero-proof progress finalization was correctly
rejected, so a 0.001-second solver run produced an explicit zero-VERIFIED /
one-UNKNOWN seed manifest instead; its hash is
`f1c3b80ea76d0f252dc6b1cb3bcf289986bd3faf23f186883f576cf0f492e172`.
Guarded lookahead from that seed closed one sibling at each of variables 6316
and 6870 with compact DRATs of 47,971 and 2,836 bytes, hashes
`eec1f044014213323ad414f05777b1954f7ac199dec276f837c18b4027e70dfc`
and
`d64449c5f663b8b189d0c2b0c0b46969ed4e9dd14d50aa5038a95b7ab6473cc9`.
It retained a single deep UNKNOWN through subchain state 602, then rejected a
variable--1140 1--2 growth.  The state/final-manifest/halt hashes are
`f88fffc687924536f8fa237adb896406100a36d9526182874c72740f29d12de0`,
`c5238f6bd3765c282f86b3298d533c5dcec50a06ac4aac31244321afa8762d2a`,
and
`236d525745a23143de7e8c61fb096f8e1f66a9c8f75ab51b23437f9f7a3f5d86`.
Independent replay accepted three manifests and two refinements with audit
JSON/log hashes
`78c8f78372499a47bc6d1229a3b4efa1bd7b2cd73c46147f9b2c580804063518`
and
`3cbcad7db9aeb25dabd9b7a89455ce87cdaa93b1069066f3e8808371722f8bbb`.
The deep-leaf ICNF/frontier hashes are
`22bc2fec7d66374efcdc0546103447cfb9726d4653eb8b98917c60781ed87d3a`
and
`62fdcd9bd259d739acaca602fccd8966822c4a7c882f1365c8a3986a934fe4c4`.
Two ancestor-only comparison processes were stopped and replaced one-for-one
by Kissat seed 16 and CaDiCaL seed 17 on this audited deeper leaf.  This is a
certified subchain, but it remains exploratory until its leaf closes and the
selective subtree is joined back to the state-599 cover.

That same J297 child later advanced substantially.  A Kissat proof for one
side of the rejected state-602 split was composed into state 603, after which
guarded CaDiCaL rounds retained one UNKNOWN through states 605 and 606.  The
state-603 manifest/state and audit JSON/log hashes are
`235c0f2a1f01ffed38e5c1eb79abef8b2ba87b8cf0b32255a9976afc2ddc75a6`,
`b00ebecab6c5f05b00426c2568cbd4e5a87694e21e063fc5490a717975744044`,
`39ea05de96f4a2ed89b87f0bbf6207fb542ae529d934520827802bc65663df5d`,
and
`4a65ab71b9cb705126c041237cab7b5ca4aacedcc6448a5272040fe065514d33`.
The state-605 audit JSON/log hashes are
`f921c9ab705fd09a9182b391f712ba38a5cd38b6b8d2d91fe8fdf9975406d560`
and
`dddfd6232a9af334cc2f9bc2d86ed80dabe17c77b2ebe3925dc5d8ce2146dc67`;
the next composed state-606 manifest/state and audit JSON/log hashes are
`4a9a259b425e0f75ab8380f71600a3340c6fe87d996a80ab27e67b1f166fafb3`,
`472d92b633d3ebe194ae242a3ac04311520f48499f2ed12d30be296eb7073c8f`,
`44241413571bdaac166c969278d3af7e8cb5f64e79e04b0b08f39e28f7b6c4ed`,
and
`9ca71eaaddab1787602ba5736e25ac6490036504a9bcb0356fed6e3afa6b2bfe`.

Ten more audited rounds kept exactly one VERIFIED / one UNKNOWN through state
616; a further seven did the same through state 623 before the next split grew
1--2 and was rejected.  State-616 terminal/state and audit JSON/log hashes are
`0366f4f087940afcd7458d50761206071e88e2516d811599ff4c4852153d0418`,
`0741f8c9240352e0ebdf703b70ce4de449d83cb1518c724fc527903978253c71`,
`18324409791f1cce1d7397083c9984f4f945f5dfaa4fe9a54110f4dcdba68c4e`,
and
`b1f0505b6588b68d38bc692575d73219807a62e742f7412c779014f1dcfc55f4`.
State-623 terminal/state/halt and audit JSON/log hashes are
`706a3f9db410bc51d7b5e6388d841b640214c891f77c4b25144ca536b5202e21`,
`9add1b95931a322ec36dd8d01d204590a06f041b99873d1601245a24005dca97`,
`5db417b9d1c19474eb75c597bc01c6477e24833490432b0dc0af39135578401f`,
`2d053dd19dc8e9a3366927aaaa7dc5b91b37cf8d41a2c164a440cb6c37cd6392`,
and
`f8e8e354e9173d1613edf4c9ccc9dc31794fff4196bea655008edb2436a77af4`.
The deep endpoint still has one UNKNOWN; direct parent and rejected-child
portfolios therefore remain search work, not a proof of this original child.

All three rejected-child engines later proved child 0 of the state-623 split.
The smallest retained result is CaDiCaL's 17,610,953-byte compact DRAT with
hash
`022906692ff648e56107fa97a9b2241e6c7d791f28045a9724f21b96520d4cbf`.
The live progress snapshot was frozen with child 1 as an explicit UNKNOWN and
independently replayed at one VERIFIED / one UNKNOWN; its manifest/audit-log
hashes are
`fd4252a21a6ab60056a8739514cf113671c4e25bd5aab0ba5e6a534cdd55fa5c`
and
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
Composition with the complete state-623 refinement advances this selective
subchain to state 624.  Terminal/state/refinement hashes are
`d710adce3514db9611015b01a24d1e28f9986208018570e76e4cad8c872ab2e0`,
`afcb3542d2d66c33c693cf65d56691bda713e253f88042ee0baeac6d3e7c3f20`,
and
`7ad056d0644eb4f0a67ab502e62af8c9e4db5aef838366b6b3dd69d0ee75e2c5`.
Fresh one-round chain replay passed with JSON/log hashes
`3cfd45827418be978b87cabe533c14ddabd22d2aab260362952eeb7d9b7c1658`
and
`cfc8d4569ec7aa980118e7490d2cde9e2af1c003dedd0577269c619937903a67`.
The three still-running child-1 searches now target the exact state-624 leaf,
so they remain useful rather than redundant ancestor work.

The same selective procedure peeled the two children of the other original
J297 parent.  For child 2, nine consecutive lookahead rounds each closed one
sibling while retaining exactly one UNKNOWN, advancing the subchain from
state 600 to state 609 before the next 1--2 candidate was rejected.  The
explicit zero-proof seed, final manifest, and frozen state hashes are
`b8209f1ec0e23338ca4ec38de61834163aa7438583dff99d108d443750d94a25`,
`d74dcb3beeb7b041f707164ec959c6c059e9790afc5495706340d13853f363bc`,
and
`2899bbf1189505784d40b9fa51903786418639452b92c558fd89f74e9f5a6c86`.
Independent replay accepted ten manifests and nine refinements with audit
JSON/log hashes
`bd37f324884ebf7309ba9fc252b4fbb538e7f2721380119c7c26e572817456ab`
and
`e9b9db5d7a6cb452e92af1dea899ea9a7542a16bcb0eaabe0d2ac0930ce898d8`.
The remaining state-609 leaf has ICNF/frontier hashes
`37dc2dd2dd27ba1d947f3a23939d3bdb00c7228041fc5933452143154b342d4b`
and
`6854e705ab00d7928542169459cda5f9cb4983db236fb804003bd3c2840b6ccc`.

Kissat seed 15 subsequently proved this original child 2 directly in the
four-child state-599 refinement.  The 232,878,779-byte compact DRAT has hash
`d1ac202beeec99c735995468620de8ec14bb724aab2de46c3490bbdedfcb5fe0`.
Together with the earlier child-0 proof, the source portfolio has manifest
hash
`d74f57d7e2e99adf97341cdc20912338a3b89497a7a8ee0274a30555b62922d8`
and fresh independent replay has log hash
`f57494e8b072e0ac00ac8ec7061bbc50c58b50713ef8f4013f6116d740fbd606`,
reporting two VERIFIED / two UNKNOWN.  Exact-family composition and complete
one-round chain replay advance the common J297 endpoint to state 600 with
manifest/state/refinement hashes
`68b95471dd1a74c3b401a87e2dd1e656228be38a12f562ea155f10706dabfa35`,
`29788dd6deb7c876f5fbb2431a5015fa6e1f16cf47afd7bdc8a1dcef1d1cf123`,
and
`12a361ae9a7dd49e057ef1d398c5d451466ca980cb04635d12b321bd892b2954`.
The chain-audit JSON/log hashes are
`d43a6732ec86342ff8fc9be0310237aeb1c2ab436d5548ac1f1234bf00fb6d31`
and
`72f255f33f96724487e7fd4aa9d255878d2ca538c974ef561a184c27ab86a0e7`.
This closes child 2 at the shallowest available level, but the two other
children remain UNKNOWN.

Three deeper certificates independently corroborate the same child-2
closure.  Kissat completed both sides of rejected binary splits at states
610, 612, and 615; the respective manifest hashes are
`5b47f0578f7e7b355976a62acf6ba0779c0aedacbde0c264e2fe608379da8fe9`,
`145cf3a739fe7c5a1bf32872af95cb9ab22bf746f95556e0886ad5e9eb4bfee3`,
and
`52e519ea89f9a5de63073c6ad7bbbcbaed4695ab69a72e6d6f5e797bda208c6b`.
Fresh complete-family replay accepted all three with common summary-log hash
`0eee6d01d56ab0f88f6485152c3fb391f0628bd87a45691cea293b1f21a0d90c`.
They are redundant checks because the direct state-600 certificate is
shallower and smaller as a chain dependency.

For child 3, one lookahead round closed one sibling and retained one UNKNOWN
through subchain state 601; the next split grew 1--2 and was rejected.  Its
seed/final/state hashes are
`ff4574a413f918e6391999bf2c9e79374b451235ef4786dbdfddb9b10d30b804`,
`bfd0d2152b58189c7fac8bcf7293f7cb383890d6ba598031645ff7fb3c9e51bd`,
and
`4905839de278fb167a1d1bbcc7faae329d33f6fcb0a6ea122a1373e7ae9404eb`.
The independent one-round audit JSON/log hashes are
`94e41336075131cbb7ebdb2215e3968afb0ab2ebd857f637110546bba074773d`
and
`f07777881d6ae3a0d3c2b9dd54832c9cbaf437b6dff6a5eec4f499a8ac335cea`;
the state-601 leaf ICNF/frontier hashes are
`6ec8766a8ed330df3f40fa3ba661f1f2c7ea5ca2f1e3e9db2e01b043eb114eca`
and
`045652a77fb03d27b215f375565bce2c41aff6e00268843579269df2b2e590ae`.
Each of the state-609/state-601 leaves now has a low-priority Kissat/CaDiCaL
pair.  These certificates remove shallow siblings but do not by themselves
reduce the three UNKNOWN leaves of the current selective state-600 family.

The row-3 rejected split later gained a 241,287,898-byte Kissat child-0 DRAT
with hash
`6e7f0891fa6d2984824297e427c24fe7683d70b22015651849419cb60956e4e8`.
Its source manifest and fresh independent replay-log hashes are
`c3752bf3b5b4643118830dbb3ad375df3f113f8249174122f5289ab709c2a5a4`
and
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
Composition and complete one-round replay advance this selective subtree to
state 602 at one VERIFIED / one UNKNOWN.  Terminal/state/refinement hashes are
`96c61a50c839ed198cbd9e2c94016d89a6c68105d3c0e71766ed388593aee21d`,
`214770048af0f0d0d46a542402535309ebcc62d329c0a2bad4dabfb5a9f9f170`,
and
`c1e6c78de30b1d78308992abc96c73aa3010b091390e07290f1166bc62bed1d1`;
chain-audit JSON/log hashes are
`6dc5d8271d63eb12bbef3ef661928faf2cde7fc358c4be7da9856d5f9ce21ffd`
and
`b11ead002a87857ec5e570eef1b5ae1b802d2b51f4e1eec2aa49084fbd5ee8ce`.
The row-3 right child remains UNKNOWN; direct three-engine search and a
guarded dynamic continuation run in parallel.

The guarded row-3 continuation then retained one VERIFIED / one UNKNOWN for
four rounds through selective state 606 before rejecting a 1--2 growth.  Its
terminal/state/halt hashes are
`aea915854da99023dd8c096a51e0482c2e0abf85c2d0335ba4d2ad26e29146b6`,
`5a1441e78f80363d2c69fe77c7d2447c4b0c1b9aecaf38b48215da1abbd07697`,
and
`cf4b345eda7254c8b31872ea65bd286153737aac6f9c32a32451904d87db9b5a`.
Independent replay checked five manifests/four refinements with JSON/log
hashes
`0d614453e9f2b73fd363f1f524d9661976ac5c2b9a0a0819ccee33433d6f571f`
and
`f0011daf25c374ff8e44421f06ff958c29583b51883023dc56d0d549416fded0`.
The rejected child-family/refinement hashes are
`5b686aa5c9bceab31fbf43c6a02669c174bce7eba31400f92e96007a90daa094`
and
`b5d3b600754876722d9faaa3c5b451c000df881c039ed3b633cb6563107d94ab`.
The three old state-602 searches produced no proof and were replaced by
three two-way portfolios on these deeper children.

The older 7,200-second CaDiCaL seed-7 comparisons also finished.  J297 state
595 remained zero VERIFIED / two UNKNOWN, with manifest/audit-log hashes
`669a551bbcfa823ba4dbf39bc2ff4f0904691b2da2a5e448d0d7273edb3bc59e`
and
`3f8f88e02ae9c2005b178d357544c6a7f2b807f8201e8e9f794c8ea16a08961b`.
On the older three-leaf J326 state-621 representation, CaDiCaL independently
produced 204,481,010- and 216,057,359-byte compact DRATs with hashes
`92a3c9af1b780b81c04351e2262e3e966b5d0a66665b35056bb94ec94a94c2d5`
and
`305eedc529debfd0c854e85d92e724d5fd7cddf8a2118af10063c2d56c4c3a5c`.
The final manifest/audit-log hashes are
`08fa2082e3e67158a9eefe2614d4b4fdfd5c1ae2ef3cfa94629dd8f4567f5233`
and
`ef6e9aab2129af37b68d6a323e710f1204f35ba38566a6564df2168ebc0d15ad`.
Those two closed leaves are already subsumed by the stronger state-620
ancestor proofs, so this is independent solver corroboration rather than a
new frontier reduction.

The two surviving children of the common J297 state-600 family were then
advanced together, rather than only inside their separate exploratory
subchains.  The first complete binary refinement closed one sibling below
each parent and retained two VERIFIED / two UNKNOWN at state 601.  Its
terminal/state/refinement hashes are
`2f743376750ace0aacb15488f7d967e5caec45cc96fb7e50d4500c15a6f53c02`,
`87f7a411f16c8559e8ecf7daabeee7b1840889dc7055f4af59d3883ff37e4408`,
and
`16609e19a81feac7a92246162326e4fa51117dea18ce171396216c01b4b2a10c`.
Independent replay checked both the state-600 seed and new terminal manifest,
plus both parent refinements; its audit JSON/log hashes are
`f963cf9e6285e417c142e6879099fb04cf69a56eec154762ee8292451fa03387`
and
`27d7d31cf4b1fef9681ed558546096cc75ab2c9824062675a036633911913416`.

The next ordinary staged run produced one VERIFIED / three UNKNOWN and was
therefore rejected by the no-growth guard.  Its candidate/halt hashes are
`c26b1b560f81d3143805b357629de3670958777dd5be599aecc65e79db684ce3`
and
`0cd6eb2117faaa9d484d0cef4746ac9d446644b65540ccba27a411ba0d9bab0b`.
An already independently checked row-3 proof closes one of those three
children.  Rebinding that proof to the exact common-family paths and composing
it with the other result yields state 602 at two VERIFIED / two UNKNOWN.  The
terminal/state/refinement hashes are
`226c0b55c63f222a676b82cd2a1dd8d71a6651965c4ae7ee610e685dad81d16a`,
`a3d1f0577a0beea5012c17859fc21a66faf9cd36061983e18b5c237a8b264f1b`,
and
`61530a89cd78fbe14cad070699da2c7a422d96cf08cebe351ca049fd86222320`.
A fresh whole-segment replay again checked two manifests and both refinements;
its audit JSON/log hashes are
`4e857890cc3d7f2e18d7298d1b78975f519f26131b16eecb675ffb65940fc3b6`
and
`0dd010f05fafd97c14531fd94f7486b17a99e1a1fa86a96ef7972d0ed1ec87f6`.
This is a certified common J297 frontier advance from state 600 to state 602,
but its two remaining UNKNOWN leaves keep the case incomplete.

A guarded common continuation next rejected a 2--3 candidate at round 602.
Its two hard children under the row-1 parent exactly match the earlier v95
family, whose child-0 proof was already independently checked; the row-3
parent's child 0 received a new 67-byte DRAT in the same attempted round.
Composing those two results with the exact common child family restores width
two and advances the common J297 frontier to state 603.  Its terminal/state/
refinement hashes are
`528fdb2038c04e2dd40aff7b697e333b3292241c03b00f136874db9b468cf080`,
`7c1fe0ac06ac3c1b3622392f3bbaffba855ffe00bc3527a8d31fd70b81f28b0d`,
and
`c2ba700987c84dba79797c0ec6a6539a4323eb97ec9bd4256d2cd75556e9b244`.
Fresh replay checked the state-602 seed, both parent refinements, and both
terminal DRATs; its audit JSON hash is
`4a38798bc6065821b5165d5e5a1a920d162a90fb756a79151bcc1dc896f94efa`;
the replay-log hash is
`940b6cd27d3000211414c581a5a34070f534bb8ff7d239d91767683252335b48`.
The terminal counts remain two VERIFIED / two UNKNOWN, so this is another
depth advance rather than a width reduction.

The common continuation retained the same two-by-two terminal counts for two
more rounds through state 605, then rejected a 2--3 growth at round 605.  The
two hard children under the row-1 parent exactly matched the earlier v101
family, where a 4,919,499-byte child-0 proof was already checked; the row-3
parent's child-0 proof was generated directly in the common run.  Recomposition
therefore advances the common chain through three fully replayed rounds to
state 606.  Its terminal/state/last-refinement hashes are
`c0f66544277c34625e93712e9afa79b10964596c5c1d75395347b252cafd52d8`,
`9bc64df07d0581ceab2dcfa1b49fe6fcf804659d9415bc52290241658cb42f24`,
and
`385b83c43e3b9850f3ed3275ea881e5c01117e36e0d65ba9b1afd24d6c6a781d`.
The independent audit checked four manifests and six parent refinements,
ending at two VERIFIED / two UNKNOWN; its JSON/log hashes are
`e22c84f368866aa27f553dfd8e6df3fdedf41ef500d4e1a0788a79097837ddfb`
and
`df57396e702fd8c59c0b772218394e10a3376fba3b9879c1a7391f4a22c8fc73`.
The next guarded round closed the row-1 child 0 with a 67-byte proof but left
both row-3 children UNKNOWN, so its 2--3 candidate was rejected.  Candidate,
halt, and refinement hashes are
`53095a8571f81c0390f57815d720199c7ff56130cd386c2143fc5de542e1ad5b`,
`abf5a91896ad979a679c214ee5f62046c687e29c6f6e0e9425e957d893858a5c`,
and
`2466710376cb6bf113e08379ead0277a9cd63db4759321f10642ffcd637acb5d`.
Kissat seed 29 later certified row-3 child 0 with a 276,221,984-byte compact
DRAT of hash
`d33c50a72378d7ade9b809e6c5c429d0473f4be0bd8fa8c16021fcd8ed36e4c7`.
The frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`34852ea7277eae5c966cb6bc2740abbce55f04bd37fcde7ade3b547b4297c08a`,
and its independent replay passed.  Exact-family composition advances the
selective row-3 chain to state 607; its refinement/terminal/state hashes are
`7e0e9138406028aa67126cfda6c5a7c25bb6da131201d88f8b7726f7008c4911`,
`1adb009d0b433ddb4fb0e9efe61fbc59c6bf3c680141a28e362b384b007fe168`,
and
`4736cd31819c112a3dd7c033b12d9371cb5fc534c01d0665028f6154e0e86764`;
the one-round audit JSON hash is
`7d72d38deec0bb3e0637cf0f536a83d5d88b8896e92485bfe35c6e4500fd45d2`.
Composing the same row-3 result into the rejected four-child common family
retains its 67-byte row-1 proof and advances the authoritative common J297
chain to state 607 at two VERIFIED / two UNKNOWN.  Its refinement, terminal,
state, and independent chain-audit hashes are
`1c6d3a6dcaa9632f3e696dde92981769dfedfe800c2f9878b08b584d20354136`,
`5cf5c04d2cc7f899a890398b1e22bbb900ddb4f307bddc1d5e67feb7ea1d2aa2`,
`70de1bbb19d0aa8cc96d4c06d0816c582c070c624577875e0ac92a4080996469`,
and
`091a13936e4fa7a8505233cb5d8a98a88e1070a02944c56311f2acf455e62e6c`.
The v21 bundle appends this single J297 segment while carrying the J326
state-629 terminal unchanged.  Its recursive chain and parent-extension audit
hashes are
`1c31ff24774cb619c02878cd4c5987bcd6b7caf8ab88ddfdb87ae15b99a05242`
and
`315b551ae7d40331ef20d58be040019a8f9fb2a2243d6dc1103671ffdd7aa1c0`.
The accepted production checkpoint therefore has 32 J297 and 33 J326
segments, with two and one UNKNOWN cubes respectively.

A guarded continuation from the exact J297 state-607 seed closed the first
row-1 child with a 3,583-byte DRAT of hash
`7b1b2045a13eb63b4b8dddeaf974dedcc598d8068c9087b04c91266f61ebfa87`
but left the other row-1 child and both row-3 children UNKNOWN, so the 2--3
growth was rejected.  Child-family/refinement/candidate/halt hashes are
`6484955eb57de7d547e5475ed8d2d8b5a3af6b0d9b11ffa6cff2e24ef820fac8`,
`e9574eaa88b0473607b4b3a4248d1338264f3e56c54dbe3bdc4d4001a86a9c9a`,
`613daaeb41e116d7d8fd26cc4083a8635ce864d4f0913d4d9eb0734f01ddde0c`,
and
`27066b3f086d19a99196f11076f02a1575ae8e6b10c663b82fe57765e7aab549`.
Three-engine portfolios now attack the exact two-child row-3 subfamily and
the single surviving row-1 child while the corresponding unsplit ancestor
searches continue.

CaDiCaL seed 30 certified child 0 of the rejected J326 state-629 split with
an 87,761,516-byte compact DRAT of hash
`1364aad27416acd858570bc261961cce65f6511a8c348bbd6a084bf62d9daaf3`.
The frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`da8103d76f73e881b3507dd9297397be9b856556350ec492cc3903d7366c4396`;
its independent replay passed.  Exact-family composition advances the J326
chain to state 630.  The refinement, terminal, state, and independent
chain-audit hashes are
`f702e9a80cf53c394c3a7fe4c4a316a995b88420dfcd28157e18714606507d7d`,
`618a9743528d84b77de4ddff9476cd454d304083146b4d2d022ef137f6a22f3a`,
`135477998407f390aa168bc0f582fd57c54e9e11445eb8c3d94868d88847e71f`,
and
`57637156447e17202a694eeacad25581cfa092d8271fcfb84ac3356290c7e86d`;
the chain-audit log hash is
`9312e1199fb382e0756192f2a08abeb0863c5e5531b359fbbf915912aba99078`.
The v22 chain and strengthened-parent bundles have hashes
`85f930c9555add0a889976ecb0890c4e26631e54ae4a59981e5ae3e89973b9cf`
and
`5817313d2f30b12a38a13473b880d88ac725f265eba55cc5c18b1826f5261f8b`.
Their recursive v21-to-v22 extension audits passed with JSON/log hashes
`08afabe977a9ad34fee61bb708b9a5d37c89e51a0679d827ce758fa0a9160af1` /
`43f91ea240f4ef0d4bd81d2d92886a56080f8d033124b6f31851c7f079367d3f`
and
`09627428ebc56aa34ca5eadc2cf7d6036b391e0712fe9883c17a75e614dc878d` /
`d7701e0cf904251e5ab774e61696ba98bc69a7fe3cdff09e55a2590872d81400`.
The accepted production checkpoint therefore has 32 J297 and 34 J326
segments at states 607 and 630, with two and one UNKNOWN cubes respectively.

The guarded state-630 continuation split the remaining J326 cube on variable
`-1155`; both exact children remained UNKNOWN after the one- and five-second
stages, so the 1--2 growth was rejected.  Its child-family, refinement,
candidate, and halt hashes are
`d0ef7c980b03db63f159ba8cf72607e4b0054a8334317bdcbf570d8d6c128f96`,
`275cff9c4eedad91ef1002c5ae5153e8625d8f59d604dd66d61ec9a34ca89994`,
`a6996efdc66652cd5503ff3fb1f56f74266879a0e0bf18be4c9e4d3637e9869f`,
and
`56ccb13f1425896f417b1a8b123d7e8128586f258b7c6cf9a083f0516f9933f1`.
A three-engine four-hour portfolio now searches those two exact children,
while the unsplit-parent searches continue.  A separate solver-agreed screen
tested both polarities of all 859 unassigned variables in 1--1200 with
CaDiCaL and Kissat.  All 1,718 cubes remained UNKNOWN to both solvers at one
second, so the screen produced no alternative split and changed no state.

CaDiCaL seed 31 then certified child 0 of the J297 row-3 subfamily with an
80,755,357-byte compact DRAT of hash
`c7c1f6a674a8a1fe54ffbc141917b9bdb12652392b238bc5e73be30e81cb0da7`.
The frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`ea50f94a70a879f47f11d4320ccff5fd6fec9e00d9d481559e8c57744cba06eb`;
its independent replay passed.  Composing this result into the rejected
four-child family retains the existing 3,583-byte row-1 proof and advances
the authoritative J297 chain to state 608 at two VERIFIED / two UNKNOWN.
Its refinement, terminal, state, and chain-audit JSON/log hashes are
`89288d65e2fa64efecd17c96d1b825677056fda314dd0dc36ca517775b2cce7c`,
`a74a6847a36c6dd77f0aaed780f7945d453d14cd6dd24e7e609583a50e64cce6`,
`bd3d6b6753a6e80a8915c7d01926d5dd43d880f8866a74060dda123fc31d1794`,
and
`dd4278504511987e65e02218670bfe01f57d7eca2502b8ac3c01fb99b387ae51` /
`dcbf278cce7f00800688c6236de307bf2a5c40708ed99dd0c3d354666e1c0fdb`.
The next guarded continuation split the two residuals on variables `1049`
and `-747`.  An 8-byte proof closed child 0, but the 2--3 growth was rejected.
Child-family/refinement/candidate/halt hashes are
`87f5931923329adb19f241a72eb5200872db2de816997c94ed9aafe3463abe59`,
`e45bb8915b4181e6047cbc3a6f986be4a00af4884b13a4c9b4ef530debb04dda`,
`c8b3f7d71ed6538e44e9b1a0ad75b620d1ff5255ad35b98b81902b6d0c233139`,
and
`d4bb84c00a0e9d8611d6aed69d1ac1912865522b85a4e048e957a173e462344e`.
Three engines now search the exact three-UNKNOWN family of hash
`2c07ca6a0341c0e6a69af67521e9bc5c2a1997c535fd8e0589465b18f403414c`;
closing any one row restores width two.

Kissat seed 33 independently certified child 0 of the J326 state-630 split
with a 90,228,187-byte compact DRAT of hash
`b0c1ddb5fc361ede34a779bee9dd6ac44a463f413b976dd8edb19cbe597b69c4`.
The frozen checkpoint manifest has hash
`18d77a42163cb51b8094236bfa581c96afe2d3d8e30d433aa3d3c88d57eba9b5`
and its independent replay passed.  Exact composition advances J326 to
state 631 at one VERIFIED / one UNKNOWN.  Refinement, terminal, state, and
chain-audit JSON/log hashes are
`a0cbad3784118eca3bd382f66bf8d0dd8e79c820f7c2394e9bbe9379317469a3`,
`a300c8bede14a64254cbdb110111f06136dfff98caf24123f35a765a84809afd`,
`95d1799a7532fd360b489d8435535871d42fc93d8d47cf2a61df2b31b275b805`,
and
`b434b23387f4ff315e5749aeaca3878037a5bf3524bfbdab8c1be5fe5ce31b64` /
`334074eac183f078656e9624941fb84a298e6d2a0a4a7b51f72500da5175cea4`.

The v23 chain and strengthened-parent bundle hashes are
`bb7645286c69524a0314c171afc0b579049f1c03b67811bf4cfa6049a0f1c813`
and
`379ae8be338d86a02b27b3f914caeabef9113f150a8b9e714eff517ba9ae0779`.
Recursive v22-to-v23 replay checked exactly one new segment in each case;
its JSON/log hashes are
`4c2075a692f97f7d6314ffad541617f253dc99e84ab1d9c3c4f4f9ea4509b79f`
and
`c7aebd2635e16ae3a65206743bbc83659f9946e9aaf28a659dafb55d5ef699c3`.
The strengthened-parent extension passed with JSON/log hashes
`2aabbd05f67198d3e204a7f99bce482ff3b5ce48647d27bc3ddc14a57a1c602d`
and
`163e73d9c793299a062f16d5a6beeff5f7031a15b718fab0ed942dde9a1e026d`.
The accepted production checkpoint is therefore J297/J326 33/35 segments at
states 608/631, with two/one UNKNOWN descendants.  A guarded J326 state-631
continuation is running while all exact residual portfolios continue.

Kissat seed 34 then certified row 1 of the exact three-UNKNOWN J297 family
with a 111,143,175-byte compact DRAT of hash
`35150257178a366f01655ddaa89006bb78a00ccabbae3300643988f6ee3f8d38`.
The frozen one-VERIFIED/two-UNKNOWN checkpoint manifest has hash
`cda3cde5daf42f1ce341842df5e06113fbfec86e10ce090ec068d9336f284168`;
its independent audit log has hash
`920c23df17293ab33b634b630e4acfd3e6fc34342cd13f46b9b11ae063c30ad5`.
Composing it with the existing 8-byte row-0 proof advances J297 to state 609
at two VERIFIED / two UNKNOWN.  The composed refinement, terminal, state,
and independent chain-audit JSON/log hashes are
`ae496280db9494cac004536be9b0cacfe281c7c7dfa46d32a8307f1e91e1c7f3`,
`b9c33495e4649419f5b57f5c501fee3ae18843f3bacd46a36b0420d10c9eded0`,
`9f3a7dc2ec1924235f20b42641bb1e21ea4f226d513b6f7a6e5e6e325cedcc58`,
and
`a9bd206595a92a7b35d6cecf69f62360a9d30b089fe616e98ddddac6b1d2ebe7` /
`2b433d165d927e74df2157a6823efdbc3d03d8e2c8945cde9eece3ee07f0846c`.

The guarded J326 state-631 continuation retained width one through four
successive splits on variables `5393`, `6862`, `7044`, and `-7409`.  Their
8-, 58,366-, 14,941-, and 67-byte compact DRAT hashes are respectively
`11a717bb687cdafd9b51feba7f44bc4c37793e47f27910e3c57709bae20f5760`,
`598d468229e327697119e5d7c8fb26b9936c68e95843a806668929a1c28be718`,
`f44674a1fe253c9ce6103e5e394a6ed1c11b84b0d9fbd297817b77e9e367608c`,
and
`896fb8552e0ab250899c690e861f942a7327db1fd58e5b5c7e37b3061b839eb4`.
The four refinement hashes are
`6d0b7a973a2f67f97d6f836c605f757e84f2f79bdcbeb6bdd84826c8aa2842d2`,
`25eb8e0c122da73b2c2261bc61fb53a3e8c6fd75a4180a80ac5da6eeace2448c`,
`f00bffde7dafc99efcdf754c87538229ec378c9e60213c4c8fc1d0477f1576f7`,
and
`a7c2de5b904375115eddfe031213d92c8245e0691e4a8d21e7842aa5fad18718`.
The resulting state-635 terminal/state hashes are
`fb861dfe79b5a6ed7429a821426d2e4ccf8ca120afefdf67d763979812e3ca3c`
and
`09a8e3b78bb1309f6c903adbd3afdc07d5f1ab377656b83060692a3e7bb30d73`;
the four-round chain-audit JSON/log hashes are
`efa4b963b2355da06347030e4d54bb72576c7ab5b2877ed585d15d18faff3bae` /
`2837828418b8d3d57e963327445c726e3550a78b06509a5a59b6a7516f75fe5f`.
Splitting the remaining cube on variable `6309` left both children UNKNOWN,
so the 1--2 growth was rejected.  Its child-family, refinement, candidate,
and halt hashes are
`95100f8cb6f366f6dd1f84e83c219e4d198646a87f1314479dda9c2d7c8766fc`,
`88d53dd01a3e07f6fe1047cc47f74c647b6e46ad0c6df8802b46516192f7fa9f`,
`ab0d284cab47f8a2bea42dd0cd4b10bd0e3411c9347ec655c061c7c0a3be676f`,
and
`e4d1ad02104d04c022361792a312f8f35427b9d4eb6e58f9a65842470b5ea03f`.
A seed-35 three-engine portfolio is searching the exact two-child family.

The v24 chain and strengthened-parent bundle hashes are
`0598d24201fa68175521466acc3e7d7b99a6586b8d4eebbf018033ff5e78c2df`
and
`66b045a0aba2cc394e80ff486344ea0b98a7b89e5de7e312ef0df3878269fada`.
Recursive v23-to-v24 replay passed with chain JSON/log hashes
`51bcf8e1122caaef8f7b9e336e2e01537a349c8ec36b013984cddd234945c425` /
`9ce698ff81827e7f8febb217ba684210057d3f0ac03fcbd76fa23a1b63264f87`;
the strengthened-parent extension passed with JSON/log hashes
`86b847849f72e519cafb4c79fbfe7412b41f19d1346cb82c6e64ffcd84751cba` /
`3d08e6335bcc424d935badc091aeb9562a098baf4ae1992115ecb7f15114c6e4`.
The accepted production checkpoint is now J297/J326 34/36 segments at states
609/635, with two/one UNKNOWN descendants.  The guarded J297 state-609
continuation and all exact residual portfolios continue remotely.

The solver-agreed J297 screen over variables 1--1200 then completed all 3,296
polarised cubes but found a one-sided split only for the first parent.  The
authoritative state therefore remained 609.  Expanding the screen to
variables 1201--2400 found variables `2211` and `2389`; 100- and 38-byte
compact DRATs closed one sibling of each parent.  Their hashes are
`a5731127be04c91714a6ff67acf80a6ec03c4e6bd6b49d3cb082f65a85f5a5af`
and
`0e9e28c51e210b5068a0380850962aa7ad7d68711959b55288fd53f9a1e83dae`.
The first attempted chain replay correctly rejected a reused frontier-lineage
file whose embedded output path named the screening directory.  No state was
accepted from that attempt.  A fresh export and exact proof composition bound
all paths to the authoritative directory and passed independently.  Its
refinement, terminal, state, and chain-audit JSON/log hashes are
`aeac611d7bae598235ebb1166d38c499c44d5d4338bcae93697e9ca79ea76b5a`,
`68bd0fa696ac5fa9f81a8bacf43f4dc28551261902d59efd72249a01389c35a1`,
`64b76087d3792e4bef8ffc9bef068628b8250727c4c6f97dbd8a3c7a72ec0dbc`,
and
`91dc1bc2a6b90c43db0dabcdd0919ff457671aedc99f0c81676e84d38b1d9934` /
`78b329b3a41766e3ff9ecae32b29e0ee01669aa9cc463d168f4368c605817719`.
This advances J297 to state 610 at two VERIFIED / two UNKNOWN.

Two further expanded screens preserved the same frontier width.  Splits
`1813`/`2390` produced 28- and 32-byte compact DRATs, and splits
`2104`/`2394` produced 8- and 326-byte compact DRATs.  The state-611
selection/refinement/terminal/state and chain-audit JSON/log hashes are
`62b65d8ef90a3fa99a9856ae5a8241864f08d720ab329e8f9149e065362d4630`,
`bf02ff3fae57647199c63329a511d54363ecd64a9ab281720f07d63a111f3493`,
`158a6145e83e9ebdbd5a03d16fe8e41a006c1d792f07c6db7bce1e20df3705e3`,
`2ed07b5b8509b0b05f01c8fdb89c06a9ca4ac9a4e8e2246d27e2b98a8ce58def`,
and
`6bd1006575261d65b78abb03d8ef3594b84b9e9b5acd2c27c48ebe3f75093a04` /
`67343acec250f75c29439a4df56a2592c607c1510c4776c208277b58f89f849c`.
The corresponding state-612 hashes are
`2f5c3cfaeb582a378480fbaf34b4ed2500568cb294dee259adf2422ab8be6a86`,
`2fceeec747d356d273f09def35eaf80ae59a97916fa18276f560a1bae6b88f7d`,
`a28d639144a259a1bfd589ab4306a31241d845f5af53b7a9946bd7a232664308`,
`0837624c56c3334cae50452d4e84834e66bab25505f660d4368376b7f29d962e`,
and
`7b6a7586f4b4284205dec5e2c801135ebcbb9ce1d862d099889f9181731f8dc2` /
`acc6b10936e3e4139bc56c50acb30fa3a243e1dde1d0bb4e4cb3da577989022d`.

Recursive v24-to-v25, v25-to-v26, and v26-to-v27 extension replay accepted
these three J297 segments without changing the J326 endpoint.  The v27 chain
and strengthened-parent bundle hashes are
`e4299cddb3888f9ff546bfdcc38c42d9e369dce9e331022535b770db71c8704e`
and
`ec2c30d61ce56726d664c336c39f9d8b3a2068b972df68e788668df2acaaf0f9`.
The intermediate v25 chain/parent bundle hashes are
`d5111eec362f086720b8f4f8a9ddc1ac84c3a1d68fff6021dae9e5859c7e3f4b` /
`322e311ada04fc157ab8669aea0cc8fd37b3aa137721fbda827c54187d558e33`,
and the v26 hashes are
`dc7718af4c765a066d849bcee906718c930b8e39e3f2fafef4cd6c731d095a6a` /
`0a7c42b5c69bb0c117ea2979560583547315491e47991526ce1ffee4a0f6ee8c`.
Their chain JSON/log hashes are
`b74d52eca98d97640c29ab7eec182d84dd65f24ef5fe6120432210de53a6dbd5` /
`d3fc99ef7dec1db1159e049f7113976064d6e3e8a73f6c2a2d3bb524391be739`
and
`d2420cdfcf413b1178b6b6961a343705f50c35ae50edb381c50d1a0684027bfc` /
`030822660ac6fc57a59c2b66b7ef185280496deb20fca7e4758a19db719d69be`;
the parent JSON/log hashes are
`666a98bc340bbe1b9647e1e7e1a9fce0e8fa6ee07a388bb07d97ad9acfd07793` /
`9133b8357624467c1d485e7b57c1a522d106c028c77118160a5054d1af8119be`
and
`91fc047c2b1adebfd201d37438e9822cdbc479a9db9754ac694beaba2a295153` /
`a8d1e85148127230f230f98078852a608710d6bc6f96f3a9fe50e757777c0ccf`.
The final v26-to-v27 chain JSON/log hashes are
`40645e4318204c7c69dd22c2517e8791be77528297cf8c6b5247fbf4b549292f` /
`3a32187a87baf802dedbeb9e6d466128c74c58eca10e25c52a594d65ccf97b85`;
the strengthened-parent JSON/log hashes are
`f3d93063681d8b281efd3dbbb043b036fa0f61781bd26d340797dd2f85515cac` /
`9b41dadbb6f703247fd82c804d031601e65d617940117d824981e229baec34c3`.
The accepted production checkpoint is now J297/J326 37/36 segments at states
612/635, with two/one UNKNOWN descendants.  Another expanded J297 screen and
the exact J326 residual portfolio continue remotely.

The next expanded J297 screen selected variables `1583` and `1455`.
Fourteen- and 20-byte compact DRATs, with hashes
`3399cdde2d814a5949ac4e4acc08e5f33b51904c7358a07aaefe3fefc6c466cb`
and
`f474f289405ceace62b410984d1b873e40cdd247430b8dfcfbba4f1c0784ad1a`,
again closed one sibling per parent.  The selection, refinement, terminal,
state, and chain-audit JSON/log hashes are
`e82ca2034597dd6e0665b77f5db300e2a9953677d982d50fcf35538cfbc8e42e`,
`d7fa5a335c4255a40d6e170272d62e746b8cb4239d5c858136de2664e915e50c`,
`125b9117bae9b592f2acf01053eaa6df409d26d604421087a5508cef8e4e84e6`,
`44efdb3f44cc15138e7bf4ebadda594f346f16ee1dc7e4266ad11fc2d05b16a0`,
and
`4d3c19bc84ca75323deb7b8c3f7c0a1b02e1974dc4dfd17f8736a0f51da3f166` /
`e36ee3a0c4d295add9c1fc41d08c2f7c22aecbb89b1832ea6540f236766593bc`.
This advances J297 to state 613 at two VERIFIED / two UNKNOWN.  Recursive
v27-to-v28 replay passed; the chain/parent bundle hashes are
`66cfe3f20242d221b83e4e9dfbb030e8095b96b4cd9834386ac515b4313a2c0b` /
`08ed69cab6a51bb958aef6d842b202c7dd1e82fe2ec3b314da19c09ee8a8845e`,
the chain JSON/log hashes are
`e06eded6e037e6acb0512c72a44952869965c9a8ad264d64811cc9c91ce68301` /
`a343534af08af09f22bb5c28a1a9223174eefaa6a44945f189ba097ec3abe9c3`,
and the parent JSON/log hashes are
`5dca51b53b709c75c107b443e3cc126186d28bcfd423550c016ebb35352c27a4` /
`ce30f0f35ee36f07cb8fadd984e78d1dfa54b6b6ac2842a0f7b8ef1e7013fd0e`.

Kissat seed 35 certified child 0 of the rejected J326 state-635 split after
3,314.625 seconds.  Its 179,265,033-byte compact DRAT has hash
`9f38b46a6ccf0a5e36b5a2d726fc008584ed33236e9a261691a6687a452d390c`.
The frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`eaf74d0b8b8f374170f5402b0ed82b4a112c2b4a5394509533a294ab872430da`;
its independent replay passed with audit-log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
Exact composition on split variable `6309`
advances J326 to state 636 at one VERIFIED / one UNKNOWN.  Its refinement,
terminal, state, and chain-audit JSON/log hashes are
`537b1b6acf31708b1b098a29432ec65837618333f8f4d8930f5d96e3076bb98e`,
`37535a8974c13bac672018559995b225c563071bc44734d6034d118de91d912b`,
`5e3e074f6e84ee4a1ed4fd815aca2455ea121c4646b2c1be09ce371e12a165f8`,
and
`aa550f7d4b6d6474f5d498fc3c58d6adbad4c5a9fe387f57928a235c5514ff0c` /
`d9c1a60c521741d3ae80bab2dd20065126b5bb4f712d31745aed3cdae51a951a`.

Recursive v28-to-v29 replay passed with chain JSON/log hashes
`f66705d3efa7cc4b7478f5fc29031de0cd6953d478397b35d35c0da077ca2abe` /
`b324956ba482f1c50e86f92a7531e83945135330d6adac98e97c24fa7dfa7bd0`;
the strengthened-parent extension passed with JSON/log hashes
`255611e47880ad6430a8e5735bdb989bbb4b0322f94edb11138b64628d92ad97` /
`61ce6c5f3c2cd357e9c696fc0e8c7d3ea4f158a957da4c0abe0b56ffebf3c1bd`.
The v29 chain and parent bundle hashes are
`d9dcfa29c5f3f8715b8c7d4168fc85d2a9ed970e29693868f458d447ace7dde5`
and
`9dcd6562b8f483b9374c17b02fe4edecebc853d73a47602c8b830bd24d4e62ac`.
The accepted production checkpoint is now J297/J326 38/37 segments at states
613/636, with two/one UNKNOWN descendants.  The next expanded J297 screen,
the remaining exact J326 child searches, and the J297 parent-0 proof
compaction continue remotely.

That J297 screen selected variables `1858` and `2157`; 14- and 50-byte
compact DRATs of hashes
`59714a49e448df2a5cdc0b9f6fe9c440ed0c0942b834999f07162c969e89e5f7`
and
`300913fa6885ab1c4409210418478d432ff77a3f621321d042b70a40a7eefa91`
again preserved two VERIFIED / two UNKNOWN at state 614.  Selection,
refinement, terminal, state, and chain-audit JSON/log hashes are
`3d2cd5f5df7ce851c7b4c4de1e49d01aeaf2271af7a682edfbafef5eb65d5df1`,
`0ca78f9c55d7fa53589c2fee3a6c2c58f941eaaf248633a4e9c557bedc3e73f1`,
`2374e56d40099d34239e4dc8190ab08f1f9af6d23bdbf678df28f955fd790cdd`,
`a3c67d6d2ec689af3114984c4f6f0784ce80bd93ab7464cfbe42156bdd114bab`,
and
`8f2583cdc4d890da15833cbc61e8f9d9bc0fb366eadd0e16e54e81e432a0ac7c` /
`7ad93b114f57c383a7a6d482293eb87640891a2641ac7ad29339580b2275b4f1`.
Recursive v29-to-v30 replay passed.  Chain/parent bundle hashes are
`4bd57eb96f9876aa423e8775ac7248e1b03de80b247c32c9e7c0d81b8a12b0e2` /
`cc403eabc7554be272c12eb11b4a837ccc948d6d50f4c1a49182a8d2f9784050`;
chain JSON/log hashes are
`6c4592bc69ed64015b3222a2254db20772589e662c975b93168e5d2a54502dda` /
`55e4c56aaee03c97ad006b28e32b3c1e6cdefb7677729dcbf648c8e6c95e1c73`;
parent JSON/log hashes are
`8675553adde3ba20e22231f93fedb396e316fd570e2652690dffaf83b6f17382` /
`7eb0636210a1dcd4284a4a9b02945ae24f7edccdf17c38d54928c724a76d8a60`.
The accepted production checkpoint is now J297/J326 39/37 segments at states
614/636, with two/one UNKNOWN descendants.

Two further J297 screens selected `1900`/`2334` and `1210`/`1308`.  Their
20/8- and 20/8-byte compact DRAT hashes are
`5ccf8c053c0918b916a32a3ed89e77c8a130cee3060a0f1035c8226288cea2a7` /
`f662413801ccd5bb7b6ded8261b8d97ff4df1e4f71ed15f8f2bf0f4f4b12b58c`
and
`4edcf5aedd60554dc519f8b7e8c9503c8d55e2d7c7252a2861907a5be6596d1a` /
`183579aad8299a3833be91f1d02637e034ee2f4eb781501b966f00c9f45ec7e8`.
The state-615 selection/refinement/terminal/state hashes are
`8bf7921ebf18448b6b5b520fc8487d20f802a9e0595e47588639fa35b57a94f3`,
`ab379909fb59078a43ab0005a7bfdf14149ce2aa8d408f725164abc311322b26`,
`6d56185f89a3d2235ddcd3daf1cdece6c7178912f4f18d720b78a54c8e0456ec`,
and
`f55f40538f69be000e3229bfb5bea6acced6141fabaf3d8286c5bb5f2a2953b0`;
its local chain JSON/log hashes are
`82dcd546fc08b090986e7703c9d679b77cbe5d326a0cd66d00f648a22e31ef5d` /
`9beb7f1c051a8503cc373c72cd831b9ee66351fdea4218c2f128754e16ff76f7`.
The corresponding state-616 hashes are
`3a80b6fbc5637751dbcb0edd0b61edc7193fb9e16c1172b9cbeca8aef4e2142c`,
`f60ebd870728f35aa4998d1442c41faddc089ecfec1d29b1bef1045ea6f167eb`,
`b355050b279f321ab1af9b4293ed082330121e2b9f75305d8cfe8f7d00b304fb`,
`4ac8dcda328bc91306450a8dd251e689ae162db3c5cb65cbed376709098b2318`,
and
`ba82b78d17db16ed0b5f545949842995cc16916afbd1253a5ab08d9d62f858cc` /
`917f2bc5200f644f4d97c25a8788f5e169fa7f8beaa7b5353f09c37f0c465ec6`.
Recursive v30-to-v31 and v31-to-v32 replay accepted both rounds.  The v32
chain/parent bundle hashes are
`1871a5bb07b38d56325f0ed6733daf341227d7c174fd147bea9f4d6362bdff7a` /
`afbeb92897c76a7f51cdcafda626299614ec8ca29468905adb423f3182a51718`;
the final chain JSON/log hashes are
`b365b191139a09537c070697478a7936993db0eeb173a5bc6324f7ec29ec68ab` /
`660663e4517debb09cebfe8fe3e0ab1af83e8a9d91a3ae8e77c990aed3bcea79`;
and the final parent JSON/log hashes are
`5bbbf5be8cf3dbc82382dd4f887b9c69ed80e47278a797594350d720e0b13f04` /
`68404b0b37ce497a8b000eb55c85dee93dc682068c5be328da24f4b5a10b7122`.

CaDiCaL independently certified the already accepted J326 state-635 child.
Its 176,141,701-byte compact DRAT has hash
`719593acc588143f29d9cdc9619fa4f01fcdae9ecfd1608e1f07eaca0f576e9a`;
the frozen one-VERIFIED/one-UNKNOWN checkpoint manifest has hash
`e3b6552487c561489b5e05bd1454628ad9812a68cb4d9fb538d43e6a1393f116`,
and a fresh replay passed with log hash
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdcfccea31df7e26c894a045a9`.
This is a solver-independent cross-check of the Kissat source, not a new
frontier segment.

An expanded J326 screen over variables 1201--2400 then selected `1933` from
the unique state-636 survivor.  Its 212-byte compact DRAT has hash
`5484e90f2c53d8e31d24126ac33c75028e6d358cbbe5332f1acf7c8f2419e5ed`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`c72725c59d63814691ff8dd4aa8703296dd32f2fdc8cf293cb9c502132ee225f`,
`0460573e289503ba30563e45765628c17af87e07c4c2702bc21c29730232fd61`,
`ce59d911dfb76ad597240e80f157c7ff23a1d9ceddc7090912a42fa82c2dff74`,
`48d5a3158c602b93e638af4aa82b8da3f3cf2132c901e53c4f167406cb406896`,
and
`46c8db10eddbf04c078c561b70c344ed3f86469b8333e9560d4e822f45653150` /
`0c73059f2bc20ebf7836f81a07dd086cd8746ee0d5225278c668c42fcf31b7a4`.
In parallel, a J297 screen selected `2198`/`2114`; its 88/32-byte DRAT hashes
are
`4fcb396c0f0ec6703a8cf189c4e720170b7112816e817cc64d95640a31d17767` /
`d10e05dd7ea2f6ef43b0d507fc44dd09efceabab85ab62408171a5a0c826bbc5`,
and its terminal/state hashes are
`80b03c70f22bed45ee89004d0eeb5d8a47ab351c5583335c967f48cbdd215404` /
`950a7ef33319f890ef0cc8aecf5dc2122b06d82f25f24387612cb8ae5d6b7bec`.
Recursive v32-to-v33 replay accepted both new segments.  Chain/parent bundle
hashes are
`03c9fe3eaf4fd3be985c8c369fe8c063cad5626c4aff6cfad86797824eb66ba1` /
`3b943538fcf702328ee057c43213233e8be0b9bd863d6cbcb7780774fa76f905`;
chain JSON/log hashes are
`24aecd5f9fade9abb2cb755654f675f6e027ef658554690773406a8755412fa5` /
`65bf28dfb866c8c7b750c0dd5a277eedebcd3567a1a8c7acc8fa915c0ed62556`;
parent JSON/log hashes are
`a5de46d252f5f938da4857777666ae23a725e43b3e7e349fab934b429e33dee6` /
`db18a7f6d58dc19a26258a80ff1e56e45adc78d17bb08359a688afef63f702d5`.

Two more J297 screens selected `1974`/`1597` and `2103`/`2005`.  Their
184/20- and 14/14-byte DRAT hashes are
`8f9a5a88edba299e35d357327f9c2ecf040bb89a90d93a0dbea2ccc8e488b7d0` /
`f7a9ab0056e78bae6951136d474e95c29cbd811515649bd59370cdf15ced9413`
and
`2800c0a32af6e4c8f911116224afde4391be005b0426a602b00f224d96dffc57` /
`23d1812b39f8e72f993a89daaafbfb3831c9830f42098a03a616405f4db18e66`.
The state-618 terminal/state/local-chain hashes are
`1ab911d6d667b61595ee4922c4f4695872b1a53c283ab5e298fdd404f3e56f21`,
`8b69d728e100deb39b6ec95866dd29f33499c7d695ab98d8e0d9c9a9980f4d7d`,
and
`2491643e0e2672c50f22cea62dcf39149f919179485042f86136fa174ce79083` /
`b21ce6cc3b356dfa9208df66b279f2427e8c491d6cd59cfd0dd2b5ea19821985`;
the state-619 hashes are
`4a3ea43ce5a30ce91ee7faa035cb1796d6b3283594fde61a11e0a1a618dc5352`,
`c3eb33c45535fd223f1bcb17ee0325d09588987dbab76483423b50dfad776f67`,
and
`0497ee62cd8476f8f9eb8d2ffcdedda7552e619ef83995650209c62ded6a55eb` /
`e27cfa607cab723472e4abd3ef6f8eeae3cb878d0fe957ba16eccd4c58d5cdb3`.
Recursive v33-to-v34 replay accepted both rounds.  The chain/parent bundle
hashes are
`09b695eddeb59f434781c8bc9606537184a3e010d80c2498eaf84180b8f47bb7` /
`2b344243f1280c6aeb9b0c70452fc6df5622d8dc28afb82e48394802b28d6928`;
chain JSON/log hashes are
`03a2cc14684d4311c431cc51d7f895c984340e415c44fdd021e1ec379a9853d4` /
`9bde0f97f4b47acf48f04f5e79fc87485e1823e88f795c94704350384111a1d6`;
parent JSON/log hashes are
`a9478d42b59ba7c7261c30492c0c12ccc0a03c57a8d057f1168ceb7279a4d088` /
`efd4e77bca6b1205ccd123c7de9f798eede4544e3c2d1db68241a9cd89f1b29c`.
The accepted production checkpoint is now J297/J326 44/38 segments at states
619/637, with two/one UNKNOWN descendants.

The next J297 screen selected `1553`/`1641`.  Its 8/26-byte compact DRAT
hashes are
`c33bd0083d8e9f0d4d777ee7cd41fe91ac67f638f4b1ad4ea3d7897734cbb4f0` /
`3c061805f534c4c85c3f0a40f0fe3905694c23db1160bbcdc9e66b286c5bd477`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`b8b7e163be3c3d312c285e8d2b020b82a5457c0fdc88e22414b3e065b7fa5d47`,
`36062a6f42b3345a5896e98e9589cf4f1cdd1163642a49f1337cc032f7e04246`,
`152f61afedd871d32a6fa707c7afcf3512c728a31c70f1b27ed4786d175283d6`,
`6b832355e836dfb3fd80de3b8e132132a3a38b398e51139852c4642f68d8a30a`,
and
`b7f53d8812404ae29a3ef5d4fc5b75e8b0a96e73a20640a03df1d24e2b747c2e` /
`1d2c1655b2d657aa79952a10bc0bda9f585495f43bc4d8452ad4342631fc889f`.
Recursive v34-to-v35 replay accepted J297 state 620.  Chain/parent bundle
hashes are
`198f19b6ede2d9185c0f5db952a4b8a5e46148b7809d97842343eb53d44cb0ee` /
`50c779c13103e36558453f9afef07c95827f20fcb690a5fe46800c0992e7a4bd`;
chain JSON/log hashes are
`f41b9536d8184df8f430bd633c0f3ca5d696c3d8afa270719d2764131d7bc54b` /
`f3d0c65f5d12c45840f801897e412ed1404f8fa0b8e29f12a4c8ef42d06c77da`;
parent JSON/log hashes are
`e626043943febe1839eff5bd1570aa150f85e91f09b5239c7e49d1c26ddf7522` /
`1ce48090a4370d1ba34baccd0dec089e6ce7989fd97634a1c631403900be17e6`.

Three consecutive J326 screens selected `1704`, `1553`, and `1688`, keeping
one VERIFIED / one UNKNOWN through states 638--640.  Their 26-, 8-, and
212-byte compact DRAT hashes are
`38ea661998ddc6efad56c324662d9a6a886bd4c13d521176a9c2aa9f577eeeca`,
`c33bd0083d8e9f0d4d777ee7cd41fe91ac67f638f4b1ad4ea3d7897734cbb4f0`,
and
`4674ff1532a490dcc9eca7640319740810c48cd9d8b88ad7645ab5ff43152c8e`.
The state-638 terminal/state/local-chain hashes are
`e1191e4cb9d4bab10fe8cc5099a8e085b3158054f40cb19c9d0662159b714541`,
`952fa8dae8c9e8cfe7557ee02b2a390fe52d42ff2fbcc24b5fdaa04ada139e98`,
and
`5786f62604755d3037e2147237c9f410f0ed19a16c681521bcca09dd0f8909ba` /
`1432e785a78174d7693d123e250e752c4bfb1fd8a532a4ac31c857d75022a16f`.
The state-639 hashes are
`35bf1924690ea1ef8d56dcb7d2cf78ac1176a7f965e2aa691ce15c8fbf7c8df3`,
`9b09ad4129994d14ba248b551ff7fa3c378fb9c280183909a719a1c47518d065`,
and
`32ce9fd75b2fc1a134e152dcf2d8b0d5975005afa6df21127eeba31f7964c383` /
`13376b4c4a132e1a6868b2f105a71995dcbf6ca813595e2b89ec7a51e1c5e4c8`.
The state-640 hashes are
`6d72881cf02e4001edd5720830b0e5ad0c660aa3f523204120504ef2c316b600`,
`819a22b15c0a4a35b8bc93d4e4e5b56f81bb4710373b9258fe5528fcf81d049f`,
and
`b7f2fc20b24bc42599fe813d167ee92306a7f3baee6fea23de1691d254e808c1` /
`5b8c277059efeb4c8e1fc6122a15de9c3b4ceb82d92020453981cfbfa26d79dd`.

Recursive v35-to-v36, v36-to-v37, and v37-to-v38 replay accepted the three
J326 segments.  Their chain JSON/log hashes are
`468420c5aa719f2b1c9c8ad84ffc96e62bd060d68208cf231f7b6049f742323a` /
`4f812b407472b2a07a78d980ee84911cc8f1908de6f48b299ab5f34004711f2d`,
`e0b56ad84cad0d3b7eccbc459491bdd3641031d59fd7e9fbddeea0b6023871cd` /
`58a5c14e7cbe6530a31f0e3237e31df9acd9faf267d679912baa8bbbcbc4e8a0`,
and
`d24197d450f344d081f68c4383b1abe58c06082ab74838672ee5eab9cc45dace` /
`6253fb1af99526d28869afbf1f61eadc5591db82716884c1a048e8840eaaf96c`.
The matching parent JSON/log hashes are
`e529766f512ab7891648dedb27e184deb84be300ae55fe0e4de4778ca765c8fa` /
`4e1f2eeb40eed7e1a3861240f43275c848770569d7e777510eefba8e9858d3c0`,
`4207f2722b31bbf2f5f36f66cda0bd0b16e16328be001dd5c3e40e12a25aee6b` /
`b82ec0cebc7b6c08f0f4146744f7cec873025f620a94b915dec25b0220c3f7e6`,
and
`4a69cee115bf1704860677dcad7265fbd4a0ba13b7108815797d6ab660d1553b` /
`af72789687e87d11e5e7fa78b7273a9ef1d68412e0762b4835e3ed29a008369b`.
The v38 chain/parent bundle hashes are
`f9e932f9e7a55169a95e89697808c72a9a3d48c72bfd0b9088ce29360d6b7da5` /
`39b9c10191174fa49c208c47a36201a8ec9371fbdbbd860c9fac1724c41cfc6d`.
The accepted production checkpoint is now J297/J326 45/41 segments at states
620/640, with two/one UNKNOWN descendants.

The next J326 screen selected `1339`.  Its 8-byte compact DRAT has hash
`dcff6ff893524ab8d3a9b00a5e987d99e68d9910fdc1a53ac7137124e98962c5`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`1478884a5309785d6ec52ca0ff9b3949632a51ab2ef9ea86a82238ed0343acb5`,
`7536c86d4c88919e06253c2e460e608a883aee9b77c0546b9559093211af81e3`,
`2ae78b4ead100d0e4756c7c4768f2a8d08a575451a0315e6cb8e7bb72c79d54a`,
`419aa3fe1e921d069efc9e2071c56c1c749283f445d00d0961f49a8469a54091`,
and
`19a05f83baf03996cf00a1d11b8c6cacb1a0b0dd613bd2600e64aff2cbb84af3` /
`91496de86810a5810af2397f4fa1b867ecd242b0ea8a26a95295e1dfdf30e206`.
Recursive v38-to-v39 replay accepted state 641.  Chain/parent bundle hashes
are
`cf20cfc5561e471c6c4c01171ed6c346f3a12fd4d8d7a42ae573e6b4bcd35a19` /
`6263f4cf9e411515a65c97e23da1c64d1c42c13e83b936927fad2c4eb3487d79`;
chain JSON/log hashes are
`73ac0680551647615fbcb4e0d4ce6bce19edad8db469d62193364476359d7ec1` /
`d40d484ec0abb95bdb8e1e0266ae19fbbd7871398cae315d17dc6d45bd288632`;
parent JSON/log hashes are
`d3348e6db71dc153684bb7dc9b8b17a7293d43cd17c4f7eb18c3064982ed713b` /
`b6e44bfdeee6c4dd09ffc6e6c401333e14275859aeb18df63e80770d31a10943`.
The accepted production checkpoint is now J297/J326 45/42 segments at states
620/641, with two/one UNKNOWN descendants.

Three more solver-agreed J326 screens over variables 1201--2400 selected
`1352`, `1422`, and `2114`, preserving one VERIFIED / one UNKNOWN through
states 642--644.  Their 20-, 32-, and 32-byte compact DRAT hashes are
`7b9bde3ccd319c0191147fb06261bf670167c982ec92490a61ea349bbd692817`,
`037403d5cefb960ce6f226c13d8a877524ae1a645210eb417a71e0101d68f094`,
and
`d10e05dd7ea2f6ef43b0d507fc44dd09efceabab85ab62408171a5a0c826bbc5`.
The state-642 selection/refinement/terminal/state and local-chain JSON/log
hashes are
`83432a896cb1453531ae611fd6dd5919059a758af21f4bae5fca3eea1cea8744`,
`72aa05def6705c175924e96acfe93ac95c96d43720309f49d74ba4573195227b`,
`a66cad16d4f63af46d5a843eae55b8d0058303548c865627a10daf8ad3136729`,
`6489c2f9020e6b400d0c6b9719ef49fb24a7e6f0449cec092402fecdd4325a66`,
and
`dfe9130060b4f21286ea6cb0fdbb08638f38a7e9bdbab3979731d7ea7c0d948f` /
`02e25e1c1d5d8ad8f44b770b929840f499bcd90f149feb95dde4cc4a6bffa4f4`.
The corresponding state-643 hashes are
`e4bea22f08c53866c5ad57b21d3430b8f8da8f7298f84a478859e03bf6fca17f`,
`878f675634a4291aac929bc3f2df26f2eb792c61b8cc0e68c596f00a2339067c`,
`d4bfa9f4fe3bb9f660dc626e1e23f2481854ae588ac50a1022f2c23d89b8be1f`,
`0be741f4cedf4815f654d37667d5901a735a660769c2721ed3d8b35e71aef690`,
and
`6f04abb62a46cfdf839c0ff9fee5726a649c263b85f38f06ded97a9c5f8f3b03` /
`a5940c6e03a6905f28508d6bdb76ddf9c9e8fb84d50f62839b94698427c0b412`.
The state-644 hashes are
`917b8c3538d9eec8b0455424bf10d859ce292f070a19a488c69012b40c39ddb1`,
`9f0a8293e6c48ad193752c6df8b3d8afc8a2e013f51db8d63eab32915262fc69`,
`eb44d5ca249fe794e7250d3c0805594da07a001e119bad5c4ac26e99e45fc081`,
`769f6152cdc4b32a3bedee037b3f9f2246bf2fa1ab1fb8120a8d7162f04ecaa7`,
and
`53a65db72355ffca80e30c9c67bb78fca3e14a10f028422229bd11202d380e8b` /
`f07a14a5ae94dc3329ffa8a52e42e07a5a51a1aed395bfcfb7e62fdbda850e9e`.

Recursive v39-to-v40, v40-to-v41, and v41-to-v42 replay accepted all three
segments without changing the J297 endpoint.  The v42 chain/parent bundle
hashes are
`dfb400f8dc86ab31ca26fa60280fb61f89f0135b9ac891da05c2d7f8a6948811` /
`353a35b66e38eb503c2c6fa9d1f3b711f70f1524aa9ab06b28c5a17bcbf743d1`.
The final chain JSON/log hashes are
`f9795caf94d3954e30df5027beca127c3dbce32393a935b2fc679cc08991dc01` /
`7263b6bd210a43381a6f94655ae4a95fc7d90154868344f53060ebe5288b8115`;
the strengthened-parent JSON/log hashes are
`7f4e77cb42711930bf242c61f53f97bae722c51490746e6489c73ead5da57017` /
`6152c19fbc7a33b6b04633f42ce0ec6e81912c0a90934240a1721ae78a942641`.
The accepted production checkpoint is now J297/J326 45/45 segments at states
620/644, with two/one UNKNOWN descendants.

The following J326 screen selected `1309`.  Its 20-byte compact DRAT has hash
`73a93304db9ba8846ebcd5bb2cbec297f48dfefb294b7a79943b35914d22d602`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`9af859b9d871e3735f84b42299d34b21b4a82c91e74054dfa9fc9490888bc544`,
`e505c097238a1f14d2705f8e34d79666d3264747a09ada4247d1141da681116a`,
`555ca9aabbb9695470b8fbc30dd0a894dbe3d04da82df98eda2bec24a8b2095b`,
`abdb71ea1d8a56c0259be353265183c9ced2cba8334703cca75872dd81a27780`,
and
`070d597f636e6e9ea2e3acea66ee4833c9126cdea650d0d58f2f0820f4c2b387` /
`df466f3c065a1fc3a804fbdbcefddb9d40eb697cd3eb4df9b5c03bcc5894ef47`.
Recursive v42-to-v43 replay accepted state 645.  Chain/parent bundle hashes
are
`2848f062afbd826f6b749afac2a0fb8f097e7a9bf7e68d0876b76614beef17ee` /
`db37da4fca823cbba83c20188c36e3c8310624495bcbae981b6c36a79f78ae34`;
chain JSON/log hashes are
`7958e339d0e9b738b4e504ab920193dd3bfd5469a983f8d934367e28501852fe` /
`e10cec6849c7250605c3d28fc4b8b1f68e678ad513fef02431efd91b486aedf3`;
parent JSON/log hashes are
`bddd178a27c56d770a3663c8fa19024b80d03a2c8feb56b4a0c753a049fb7df0` /
`8b0ff20c57f9acc6ec32b4b3d77fb41341711a0c5a63628566b11448dcca03db`.
The accepted production checkpoint is now J297/J326 45/46 segments at states
620/645, with two/one UNKNOWN descendants.

The next J326 screen selected `1681`.  Its 56-byte compact DRAT has hash
`7d7677972e78d0d8b03d1029e6f0cac5d9f17534fbf9273fc17b263aae805ad6`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`b17215c0360f05e6dbcf724b0eeaf689c652d8588aedc05efbac0df8195d7c79`,
`24bb48e8c1ca978be682f7c76153e5030b8e82805e09bcbf2726eaad9550b7c0`,
`33593c967016d162fd3426becacd116d467fbd1b41334f05dc1a2e2ed6eeb6fd`,
`2f50106d20a98485ebd15298b96e3a43a2275bf5568ca848a0ba404ecdbf4909`,
and
`dcb36ba3ff1b10a1e6562555bacf69118cdd1baa90ae69f1ac0eb8121383f2d1` /
`6c03c5829ecf473e3086e406cd9ef639d99551810421d605c96b89c71b090c97`.
Recursive v43-to-v44 replay accepted state 646.  Chain/parent bundle hashes
are
`b5e34828aea8881e96bddbcc52d5517e3a01d66835b286fc3f761612ddc80f32` /
`1ba3bbd3ce1c034d6477021404a7f6abfbcc66b091f7ee451ca3f4f71e781dc1`;
chain JSON/log hashes are
`42c5400aa92e17346b86f1b9d62d6dc3d167675bba055211ce1efe63bfc6026d` /
`bc2d1ef18490b848536c9daf72d4619c3750fcc7334c21a1df2ba755d29665db`;
parent JSON/log hashes are
`0c8b0f3844c7200faafaa07132251427cb95e0747df9c1c4cd164dd3ee28a829` /
`b801d371ef2625931fc717b448f25b82d1849edf3bc7574c2b86a89cab001d9d`.
The accepted production checkpoint is now J297/J326 45/47 segments at states
620/646, with two/one UNKNOWN descendants.

The following J326 screen selected `1597`.  Its 20-byte compact DRAT has hash
`f7a9ab0056e78bae6951136d474e95c29cbd811515649bd59370cdf15ced9413`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`3a1177adf5cf95a3d78087e5815b92164b01edee769801845830c15abe1a40f7`,
`1ffcfb940afff22f4cd980a1e86413374825f2d1df7f798f894927262dc196c9`,
`484cf54fbdbc9c4a0942aea50686352d114a7f2ceb8cd87487f4fef2ac45d90f`,
`9a47461a721db4b1d175cf25d128bd0873d64bd7297467d1278dbfc3c62c431b`,
and
`dbdb541fe9720fa715cca4632e47e74a7e802d1bdfdf8a0cfa416b2e21a8f496` /
`198d26223f794db2ea679f0dc264c87f98e83083f70bc2842fbd956d0346839a`.
Recursive v44-to-v45 replay accepted state 647.  Chain/parent bundle hashes
are
`31bcfa825191b8f9e7211ff7b262ead07aa6b0e7d4f58f11279b408f3843a496` /
`c65d33159e3d8071417fafb94fb1f0c333e1e355f34db3e3702d139271b26d6d`;
chain JSON/log hashes are
`bb68ff0f8965605c61971ab641cc75cede93f14082351bd6fe8ceedb8b4cbdf1` /
`c8ea99f0ee1dcddceda5189b9a79539361453746fafb0cac9b3108ad6d425637`;
parent JSON/log hashes are
`bd70f26c4954d946bc599cece4f4f1eee645a6881632e6450177bf50dcecfdba` /
`fac35b0c113b8dca93db4dd6b5ed58cb0eaa34a2ae010037d4be7262b8d9bbbb`.
The accepted production checkpoint is now J297/J326 45/48 segments at states
620/647, with two/one UNKNOWN descendants.

The next J326 screen selected `2101`.  Its 26-byte compact DRAT has hash
`f096de32d63f02fb7cc6c457781e55129642799802feaace5f1e53503721f1ee`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`f0ddd778bfdb7797fca94a86eab8095eefa70ba1faa262b89343c065ac8caf7c`,
`e69f8fb4f7d795a46655ea91ea937c8d7fa443294e2884cdead35c8f2dacb460`,
`09a0075d70a3ba6bf7de76f1835650e60115e3bb5f1b00a4bba063bccb865f10`,
`a337a6023f8d1b094d1deaedae7ec530bb2e89833b9328ca82660b73a6ed61ae`,
and
`5772a6c62eba88f43cf9f025a3f720a21e3608264bea65687d3cc883685a12ef` /
`d105d201be794f304f72785e3d779279d689ecc98133a1da25bf0ac165ad36f5`.
Recursive v45-to-v46 replay accepted state 648.  Chain/parent bundle hashes
are
`61c340b53f3886bd7d9fc19743f41715d51307444242f6d83450d815c6519a5c` /
`5e477c3271fdf475f16c640aca6ca556a29b0942fd50e0a4b162c36ed2010668`;
chain JSON/log hashes are
`8b76f0ff08ef0cb2589e802b5a4e492143155ea4523aaa4eca89cb97e6263d47` /
`9309ccda871a836d0851b7e196e1a34da5c7cb8b958f996274fd61621ac62c62`;
parent JSON/log hashes are
`9d9b7f6d9ac0b8e001a2cda0645d60b5849b633e53ddacd16912576f91075e19` /
`6c30c58602194ddf63e2cc3f01d583be8740cbc9d1a197a561a43cae286a9b7d`.
The accepted production checkpoint is now J297/J326 45/49 segments at states
620/648, with two/one UNKNOWN descendants.

The following J326 screen selected `2005`.  Its 14-byte compact DRAT has hash
`23d1812b39f8e72f993a89daaafbfb3831c9830f42098a03a616405f4db18e66`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`b076bd4f267b29c6fa6da0850b5d4cc718a1832cc5016ba0d664b22c8116405c`,
`6ea8146de4c34163925b1b3611e9a0b5d7a887e2fe0148c1f66becb3d10293cb`,
`d72fb0cfca3509467285e78b1707785a37e7779069903de6bbddcc36f9f65889`,
`12078de6f1bfb504786b1d77e9437aa12691e06440325b6f31c65bbaebe2486c`,
and
`ab211b7381b6f1f1df78e5b6ca9618f38fb712002df9bfe3959edcc76b83079a` /
`54c0ba8989c2f6b58fa01736997fb5ac2d01fc06dba7735961b6c2cfb83ba4c6`.
Recursive v46-to-v47 replay accepted state 649.  Chain/parent bundle hashes
are
`974e920aff0cb08c54c903834a0865550f0e317aab20dd02552dc625ab4e3c9a` /
`eee597e9620ca336dcb4dcbd76dbec531ec671ac6cb6c68b533b39ae6a8d6e4d`;
chain JSON/log hashes are
`7c8c319ead3f0d5fee646ffb6b86edfad56e599daff43d4a774d62798c175880` /
`410cd62e48e788d6022769d38f36259a8d91b973b6415f7c7b75d21623b3e54b`;
parent JSON/log hashes are
`5520cf11063476975fa47c6854f3b524525322ab8666d6499b9a01dfb9d13c2b` /
`48653ab28a3669f89b728f95bdc60fc65a41594b62423cf5a87b8a5debdf1acb`.
The accepted production checkpoint is now J297/J326 45/50 segments at states
620/649, with two/one UNKNOWN descendants.

The next J326 screen selected `1612`.  Its 20-byte compact DRAT has hash
`6d989123b66492b376a96af36be1ed499361aaf2e321b62bda8e566fc6ef1a1d`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`66d0f86d6ede11002ba07fbd1d1875de6834b62f422fab833416ad1edba3a9b5`,
`4f3035d264ed359df718fa1488a0b55c201412b53de85fe0e48d9e30d447d8ff`,
`422f5785217207324dde319513e0ce0083d3d6da79cb639d5f421e477dcc7545`,
`0ce9b6442aa3bb8c1320bb28c92daeb2ab9ca04f1f5305e834454efb8da3a361`,
and
`3e585bd139d61036ea795f66e06f6f1bf5dc1f0a59d87a542480387b38c41826` /
`3bdf85dabab0abaad21a278d647dc5b35491f14811649e5cd6b4c1aad98d8763`.
Recursive v47-to-v48 replay accepted state 650.  Chain/parent bundle hashes
are
`500cdb2467f84030b2fc9b03681ea7609dbf1c5960fe7d6f521122d4cdd6ce4c` /
`91e45aa91d042b2aa8e66f7e7da8fc8c3d519fded0ddfc358622d9d529997efc`;
chain JSON/log hashes are
`9e418aff3f721f1cd80eda4868352d6cc65f15ac9fc257401350b873662e48db` /
`d90f6adbb99e5a9b6437b7c6b2c41c53beb36a1df264684c62c43c262d09adb1`;
parent JSON/log hashes are
`6e27ddb13bdffd4a5514e38eec9a733faddd157344caa26ef350fe4e2229560f` /
`ea62c6446c970d4dc2b7895f84552114e0d5b7213cb018110543d9fc5339f28f`.
The accepted production checkpoint is now J297/J326 45/51 segments at states
620/650, with two/one UNKNOWN descendants.

The following J326 screen selected `1398`.  Its 14-byte compact DRAT has hash
`e87ddbbfefaf37f905f1ec36234d761c1f2afea95be53778668702c94c4e362c`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`4fd3ab35a2b74e2c427d86d7ce71d7f31ace736d1b2a6464c04771fe544720ea`,
`762657df23dc9ba9910396e8053b93b449c63afde40b85d23e1b49503ac0f4a0`,
`8382b2e4479cece9fab00bbeeee38d6f52d5a3a9d1d5635929b1ce6f1cdc7bf4`,
`16e34c35b03617d22c8be94316df1ce4896fd3843164caa7af42f77a48291ed0`,
and
`d476cab8815352da91fdbf517f567f268a52acf319efcd70554492ae617be89d` /
`1e07fd209f3af1ad378122c16d6d3e4e75683894cc920438df2e9bb8a58b992b`.
Recursive v48-to-v49 replay accepted state 651.  Chain/parent bundle hashes
are
`799cdda42047b8a56c2460f37bb23c40832b19fd204a52a39f9f979408241457` /
`bd9853dfa111192486894067bc1572683d0ed6bff22c290693b4bec41cb83c7b`;
chain JSON/log hashes are
`aeac43b0a9105417a4063915bbdd8bcf4ac3ae4e2847f2cef8f81c7e3164ae85` /
`c5c2cf33513228da4560eff086e09887346f35264a482d334d3d166ddf562d54`;
parent JSON/log hashes are
`5f1a0ad842e06c531282a2d6408693f2dc6a0e3db7307a73d8489b54efb71a95` /
`f58d65db350eabf8f148c60281d92f44b5d3c16ef1a08f22c31c0ac608cde03c`.
The accepted production checkpoint is now J297/J326 45/52 segments at states
620/651, with two/one UNKNOWN descendants.

The next J326 screen selected `2238`.  Its 126-byte compact DRAT has hash
`40fc031782ff81ae05b20fa9a4af30724e223aeac6885c0a0ead3487bf20a5bd`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`04abaf8034a975f407f0e45a2a6b7b1c330158a46a0a1e31b49af5f8d3e30db4`,
`2589828274a475b97a5085b7f7ca1759a070b9a6794a3e5d46956ba48695e5c5`,
`e0357efa4d85d94e9227f2d27f44f6ae54517568f23076f29ec55b9c61d712d6`,
`a39f3e564cc8d2713470a78b0b028acccacc8cabd7adfb3c7373f9d2aec20384`,
and
`6134c7888c40da851e533a07bd282ce7056034f09d380892b6b6e03e7aae4393` /
`5f3fc0032226c8a7204570bb6db4290263d18cce53ae4d754cd7405f4894dcc8`.
Recursive v49-to-v50 replay accepted state 652.  Chain/parent bundle hashes
are
`ef78b3b29a4afcc33849a4b2fa02afc04d75577c15df433bdc9cc55cf0382da6` /
`92d78656e160359396f3ebef940a90543697167f4dcddc31c98e72ccc238d2c0`;
chain JSON/log hashes are
`fbab33381860290dea383d0100ef9d69e815e5415271f6e6cba305544ee72400` /
`86da0a8e903c9073cd438f21ec5eec03e9b395fe03d68e13a7a14e175d22a6a9`;
parent JSON/log hashes are
`388db78cb52311980640bcc324e862bc81a04b670503196c6ff1e7e92c338dd3` /
`211365f989c3cb291be053daac7d07b6eb28b849c7e79630aedcf568241c2870`.
The accepted production checkpoint is now J297/J326 45/53 segments at states
620/652, with two/one UNKNOWN descendants.

Resuming J297, the next screen selected `1270` and `2274` for its two UNKNOWN
parents.  Their 14- and 152-byte compact DRAT hashes are
`669a0f2b27e9a79b4aae900a4329fd2526ddb8a4a96697ea7bc6e3961569f28b`
and
`3b17d99ac9f2cc51811535af786ddbc6bf742fbefdb9968d5e161e468f054e95`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`737247d445038285f2b435c357e799f0b5e86104ce400935f7e795e78c5000e8`,
`28e76dbc6f9ad9361d29c06be33386c189f0b284b43618ab597c1a05ff35bfbb`,
`7bde4c4a5cfdd179af08b7a4fa2201ff33d41436016b8e0381877e6154470b78`,
`0866e0eb41a0418f2334e4a3a7a23f2ce44ea7550b3b1546a6ec4081766c9074`,
and
`286dbd0e3e58c2d44c028c82b01988aec768bdead584a92cfe330c4c4ad0fb57` /
`19432cb4ed541440723185e846675b5f3e8f535f27b0f5d643367bf7a53bf88a`.
Recursive v50-to-v51 replay accepted J297 state 621.  Chain/parent bundle
hashes are
`6c5941812e33d5a88da5c5eddc0669aa1bb9d0aa92abc8607bd9e375f91c6847` /
`4903cda54bad1362239ffaa1cc3ab3c4741fdd361e93cfe0f6670a0fd9f4e436`;
chain JSON/log hashes are
`1547bebc8f3b3c9a449b120d926bd8c9ed117fb029223f5163143d45de6f56fe` /
`71f3336017c5afe575397a6019b0218d37ba03426fb0a8b6c326bbfa66e6aa28`;
parent JSON/log hashes are
`2fc58361bc0e18dc24008d2b171488b0e165eadcbb6aadbafe32fa68457934fd` /
`1c9d40bd46279902decc97b86cdd48303ec5b9c628af3e67f568353355974824`.
The accepted production checkpoint is now J297/J326 46/53 segments at states
621/652, with two/one UNKNOWN descendants.

The following J297 screen selected `1259` and `1859`.  Both compact DRATs are
8 bytes, with hashes
`653710e169723877f8296d4954e6d04b939848162b908078d5659b820f51a250`
and
`09163090cf89f8d4c4bc726e161a34cf960c96bcd4da8fa2b252867c24aab953`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`deace3ad57256a9e4844be74c5383b846afe85cb13a5e8d6ca84a93c71ca9f33`,
`5b358c9c85b37af6e29df7930d5f268bc82743ff9f0b5b560ad3536a85fb9d2a`,
`6cbf851709e3665a5654efe22d52b2fc7f84d5b619d1837ce83afc318b882a24`,
`553775959e377e273a73351ef8f1b8a6de54d3d73f4f9492701dc35acb7613ab`,
and
`e80167e071bb95a809924e958e13f28c31a94f55b56e434421e95cb31a4e0e73` /
`3e4827257c6c3086b43c7a7bfb129e7ca43b35a43927e7fea8d4ee0f9e82e4f0`.
Recursive v51-to-v52 replay accepted J297 state 622.  Chain/parent bundle
hashes are
`47e96e6a684cbe3e0e249ece2b6c1a7d472a36fa33e6ad930cfd389de17232fc` /
`19494234843c954bd5ec8bc2d6fe87a74a83e6248618327e0b1377bb343a954b`;
chain JSON/log hashes are
`56ca597b15fe9e030e2e83ae98eccd1336d4f2dcf3d26bcfeafe755030823ce7` /
`5195a5876db373f77196fb16f4da9b3643401ef682b1934ec05257615edd6675`;
parent JSON/log hashes are
`ebc48e950ba39619d732fd7fa37ded5bf555cc23dc0a76ab728e4b97f8bfd046` /
`e9fe6cec8f375bd23a24300e6974422d8fedb3b0324a4f42b4f0e527dda08daa`.
The accepted production checkpoint is now J297/J326 47/53 segments at states
622/652, with two/one UNKNOWN descendants.

The next J297 screen selected `2159` and `1901`.  Their 26- and 20-byte
compact DRAT hashes are
`00214a635b3577534a510037a4750391a3fead8d82ea5a54535d5c1ec82cee5e`
and
`8dead93bb9002c7aab28d0df1bc4c2246d5a0b41d7c701837396f609fcfc271a`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`8cb48ddee7d3ffcccdbc0765737ce850b3cc05bd37b0589dfb2497bd8ad29043`,
`78c06d170fdcaadfbf4b27018e2cb25f57c82dd623ae9fdce90dcc2ab5a5ccde`,
`c8c15d147e8ea33c8c7f2ad3ac53bb41ed2ef0988582fcdb7cd4099efd969226`,
`94535ce2438c3794eaf3b7f879b472d2d3996dc3d3dab667708c33d6f696ccb4`,
and
`1883b6845ac291ba32ed12094375e5f7ca92e484115a779598a9e693a4baa57c` /
`0739eda7d70ded1109cb944a72f3683f8b1db7b1190989fda34c886bd54d7cc8`.
Recursive v52-to-v53 replay accepted J297 state 623.  Chain/parent bundle
hashes are
`21fb085941ab29dab925fa12f4be8065c7e0c69d5691cf477c046eeb5c278196` /
`f8eac5eac2f235db917e6b19d8b26ce38955659f864c4b5fa2ba01c2aff1dfb6`;
chain JSON/log hashes are
`42c8e781af85471415b78a602c09554d291cc2f395d112c91d3360f7b0ce6e70` /
`0afcbddbfb50c875b29aa478a3abfae7d347a2d8c2c39a69720a031c07555da0`;
parent JSON/log hashes are
`238e3a688996b9b193f867d553b80b2c3e70c020494d4afbd93c693e2c924d1c` /
`6de8c7f5d5a176a432b7edcbb9564c83e45c13a8e7c273f6744c1386e72d5220`.
The accepted production checkpoint is now J297/J326 48/53 segments at states
623/652, with two/one UNKNOWN descendants.

The next J297 screen selected `1994` and `1915`.  Both compact DRATs are
8 bytes, with hashes
`cf94b18722492664aa4e5b92709b4075a3537937e480a9a882d11486c6773ad8`
and
`c706bd047633bc83dee06e2e41aa6e85e4f4574e15643b81bf10eab5508cc808`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`995bb578b478f04867c8ec051102202adda0640d38b3e850870b9753985962d6`,
`c4465a8ae60fc0ff20c14034cce0580eaca061eb3a5eef16de952ab7c6f6362e`,
`d2df75a4792cb263898f8befa4db1d31510f8e7b9f3e8c8a733496c4bf846bbc`,
`214c06218222eec8331c150585c35f15219c07a2d5c08fdd07940e8109d3fe94`,
and
`fc37a9a30ee17d0d60323f6bfd099fbb6d47dc03ccb4df4a0526eb4427a562ff` /
`ef970e845c84d2fbcca47ce34692d6dc8272a337ecab3b356692425530106039`.
Recursive v53-to-v54 replay accepted J297 state 624.  Chain/parent bundle
hashes are
`47a685dfdf9a36f756100a1589d2d2eb2b285ff8b344939aa9b54f5ac73e539e` /
`c60f63fba88dd9b78c326d9b7097b9bfad43b1220bdee7e291252f6c622bab2b`;
chain JSON/log hashes are
`a84ca07847b730ec0d610529d226ece22903a0581fa9b539bc148c98a2e413c7` /
`a8a77dcc06e20eb3046d11ee41cadf065c7a7a1f11a4e804e77df8cf7ba8201b`;
parent JSON/log hashes are
`9c08a1a06c10d71fe8723f70b5e5e18315f67c6984bd1edd2e6e732d2c79847f` /
`4cd6004a2fba6cfe0f04090ec79dda59ceef00d4d444e5c1a7e54bea57987913`.
The accepted production checkpoint is now J297/J326 49/53 segments at states
624/652, with two/one UNKNOWN descendants.

The following J297 screen selected `1410` and `1899`.  The two contradictory
negative-polarity children have 32-byte and 38-byte compact DRATs with hashes
`8653b2a536bc6f133e61bcaab8c77c17746c5fa20bce6a1416e5270a33d5980e`
and
`630a82d7f4fe3e7e0d5751b7721ea461ab033cd50054a965cc261e92df9e3300`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`7852312cd224d9900fa8f30a2a4c363b8aab381b30bbc24c77c4a5c181684340`,
`a736bed92f70011a80010cd07f8c57cdf5e74bdb1efe473897d04f9da01f920d`,
`eaf66fda6e9cd8676bc309f540fa5282da682b33502a2d238ffb0cfe184c8da0`,
`14135d3f70564008c89eaf8017a8ee7fe113c245b3191f2b70aac090254517f9`,
and
`978e9e919b4e3871387518e7370ac621425bfd4341c4e477586d869ebe5a60ec` /
`3156094eb8e387fe62cc507ed85c493bc5aa7c6f0b44145ed4605870343f8309`.
Recursive v54-to-v55 replay accepted J297 state 625.  Chain/parent bundle
hashes are
`1be98c00026b5f71c978f0296e91c67ab797b552c09155eade7820cff8f2ff39` /
`3ec100e6c97b15eb9d4902c9a03f6d32fe162fc16290ffec7268ed48347ddfec`;
chain JSON/log hashes are
`57ff0ce4cf83515e15969c11185f923417980e492c5a1e8e8a977e815e92e471` /
`9226b3c3eb79847c63f165b827ecaecb12b7971e3505891ced8e09afba5faa96`;
parent JSON/log hashes are
`342c8892cce5debabb4325d1fe8d99106fd88484ab6819b4e415111d4259ff60` /
`86ef31071c6033cee0b29d82bfd3c0bbe63721aa1ca520595121ed35d8800592`.
The accepted production checkpoint is now J297/J326 50/53 segments at states
625/652, with two/one UNKNOWN descendants.

The next J297 screen selected `2239` and `2304`.  The contradictory
positive-`2239` and negative-`2304` children each have an 8-byte compact DRAT,
with hashes
`86aec672e5e9602fca4ba777e4db66954c23c7af79b9907b919f2399c601b20b`
and
`2fe829f94ff64fb8aef34012a8f33019a00097308732effa6f731b0b897d2150`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`a5f3f01971fc11d3411944cecf6676a769f009fa9d8767319baeab31eb7ac282`,
`6ec5372fb7e1d623ef03a5d790f2aa618cc1eaad4bb939e223e725511bad8f6e`,
`39113a763b198db456ca112169bd95aad23dde1d3db923e1b70c52dd669117a6`,
`ea74f4eba19bf42be6b2d6a88774f98ebb5bf7e0691fc97a770cc078fc01e52d`,
and
`acadd893e389eaaf385defe4083a8c22c01509a652f5ab81fa9e202f45868e1c` /
`2cf4a8d715e6990d9cc1bf2ac3ed6e41d95e370ed7cdc502bc206fa4814e750f`.
Recursive v55-to-v56 replay accepted J297 state 626.  Chain/parent bundle
hashes are
`ca315d020792ff44e1582afbb8ea9dd89947e78b4f352ebbd134897830abf2de` /
`cd69ab53f5af4d698056b9c60287c11e3d400227b1e52f8fd262c08308cf27ce`;
chain JSON/log hashes are
`2bc404944c9da04405a6aee745464232c2107e18b5a58e2539c1ae02788cd058` /
`92ead67258d98acd8a2649c3f66d66392b0b10e39320c084543a893767bdf7fb`;
parent JSON/log hashes are
`494efcea45733bb516ecb01e332a6a492becd5cdc5bce2b4a1a7199be3bb08d3` /
`a5af361b5c17837007d47b311fd328064830080cbc67af82d547978f362d2599`.
The accepted production checkpoint is now J297/J326 51/53 segments at states
626/652, with two/one UNKNOWN descendants.

The following J297 screen selected `2332` and `1844`.  The two contradictory
negative-polarity children have 20-byte and 8-byte compact DRATs with hashes
`28eede789abf9f273f3a170bb376c1d8ca78e63818ed3dc031b3502ed2d47680`
and
`1b020a4fd851ec7cccaba8050db0424aec14916fafadbb3adb0644a86e95d6d2`.
Selection/refinement/terminal/state and local-chain JSON/log hashes are
`96e3a8f84d69a303c90bfbf3a2373d1f8409496feccea7196f73a78fb0e089db`,
`abdb048fa280352bb59e7526c3c049e27b687efa962f7d32f084e97a5fb6333b`,
`c5ce6f93b39fbfc3b9d5417b2efd91f26f795e75f411e348ee54885301d8e979`,
`5ef600f157aa4ca8736c37bbb8c27f34ef958a3b73f44f6fc08c0c1860617c94`,
and
`10721e7f05f0ee2cf34bfc36d8e95b8be86f49c8cdff8000fb3707559619f843` /
`07619f7b9c6845e3408b2469dbc9d859a0150ff587ba27473a048369d5a3cb3a`.
Recursive v56-to-v57 replay accepted J297 state 627.  Chain/parent bundle
hashes are
`b610b530fc573b24d7aaba86ebb2bfc2da26a8ee871d685d314dfe677f9eb5e3` /
`53bf0e0ac7fd066cf76c8c3f6e44f09515c90ecc2da8786b0cb6275631788120`;
chain JSON/log hashes are
`8ccf00e3b4ba2371efdb10cbd3dabccae7da4953bd3486a59e16333013080aaa` /
`856172ac53dd81a2750032bf5b2022392824a5628d78edd164d86cf6b28239b8`;
parent JSON/log hashes are
`a2fd0142d0e7efdab1d1bc5d04f3958f87eb58055ceafe57889d66b8217ac2b9` /
`f692f4c11ce42362184acc92967f903e01f4626d04a92a1ba207bd3889fdd609`.
The accepted production checkpoint is now J297/J326 52/53 segments at states
627/652, with two/one UNKNOWN descendants.

A separate exact J297 parent-0 state-623 leaf search completed.  CaDiCaL
produced a 489,119,715-byte compact DRAT with hash
`685e9722c01c062c010381cf457b8b91c91798dc414076bdb9603467dc8ee818`;
its complete one-cube manifest has hash
`e2bed74b14384b28f9a7c8f8d44c483a57e34ebafcac69c2823d6a1abf0dad5c`.
The producer replayed both the 1,619,892,057-byte source proof and retained
compact proof to `s VERIFIED`.  A fresh independent manifest replay then
reported `audited 1/1 verified=1`; its log hash is
`07521dbcbd17729a5484e9074d6fd0768dfdfc6e92c49eab2ccc038b4c25ca8c`.
Strict ordered UNKNOWN-only composition replaced row 1 of the hash-bound
state-623 manifest.  The resulting two-row complete manifest, frozen state,
and composition-log hashes are
`725ce3272506693831155ba1ff7d36f55b3c5be04a71811c882ad366c18bbecc`,
`54ef201ddbcbe25b43f07da33a1ad0fff730dd253a9569cb60b01ccb36f6e137`,
and
`8e3d08389d4cc9d6590dd9a5f8972b8c6b7a490bbbebf35080abb5a8c7ae8571`.
The 489,119,715-byte artifact is hard-linked rather than copied.  A zero-round
chain replay of this composed manifest is running before acceptance.

The current J297 v57 terminal has UNKNOWN rows 0 and 2.  The former is the
unique descendant of both the 717-literal parent-0 row-1 ancestor above and a
shallower 716-literal state-599 ancestor.  CaDiCaL and Kissat have each
produced and producer-checked a direct compact DRAT for that shallower
ancestor; an independent replay of the 601,296,897-byte CaDiCaL version is
running.  `tools/audit_selective_ancestor_closures.py` now formalizes this
overlay: it binds the base chain bundle/audit, replays either a complete
selective chain or one verified direct proof row, and removes only terminal
UNKNOWN cubes that literally extend the certified ancestor.  Duplicate
coverage, SAT rows, and formula/cube/hash mismatches are rejected.  All 81
`tests.test_cube_tools` tests pass on the ARM builder.  The direct overlay
bundle has hash
`f9d570ec0dbedde29a8723cd2f7f92efee7339aab5c27b481fc285e3f2def7e0`.
At that checkpoint neither pending replay had yet been accepted as a selective
overlay, so the authoritative strengthened parent-1 endpoint was unchanged.

Both pending ancestor checks have now completed.  The strict state-623
composition passed a zero-round whole-chain replay with `complete_unsat=true`
and `final_unknown=0`; its JSON/log hashes are
`bb450765f2fa51d01de803ff6058f29af0b496ff848382e4e1f68e6325eaed09`
and
`c31ea08fb77c9f7ba8c9043290d9d416aa6683a76a2f0ae3c63eb432d8b10f75`.
The full seven-segment selective chain was then replayed from its one-cube
ancestor through the complete state-623 terminal.  The resulting overlay
audit and log hashes are
`c364ad0c0a6d2fa96dd19cab7c7518f429c6f65dd6befe067a485a5e1cfdbe64`
and
`6353f92a1d9cb06237224b319542fc0b6a67aab131e4c4cc0a208d47bbcb1f0a`.
It proves that J297 v57 UNKNOWN index 0 extends a complete 717-literal
ancestor and reduces the effective J297 residual from two rows to one.  The
independent replay of the shallower 601,296,897-byte CaDiCaL proof also passed
with `audited 2/2 verified=1`; its log hash is
`ea389d56d1c9bad8343b7ff358048de4fb8c86bdc43cb6f0d4b24730235d02df`.
That direct proof is an independent cross-check, not an additional reduction
of the same descendant.

`audit_selective_ancestor_closures_extension.py` makes this result usable at
later production checkpoints without replaying the 489 MB proof again.  It
requires an accepted selective audit and a separately replayed exact-prefix
chain extension, reconstructs the certificate's ancestor cube, and recomputes
the extended terminal UNKNOWN descendants.  It rejects checker, bundle,
audit-join, formula, cube, row, hash, or overlap mismatches.  All 83 cube-tool
tests pass on the ARM builder.

Six additional screened rounds advanced the ordinary production chains.
J297 selected `1917/1568`, `2042/1382`, and `1225/1441`, with compact proof
sizes `476/28`, `238/20`, and `20/448` bytes.  J326 selected `1671`, `2103`,
and `1410`, with 26-, 14-, and 32-byte proofs.  Recursive v63 replay therefore
ends at J297/J326 states 630/655 with 55/56 segments and ordinary UNKNOWN
counts two/one.  The chain and strengthened-parent bundle hashes are
`ecfd41d52e653b9a846ccdfcd294bbf5c2033c9a589dcbfd0f59bd020ded3ddb`
and
`97ed5589aa661d2955998b12021127b17b8e1c5aa19cbee98bf842861d710416`.
The latest chain/parent extension audit hashes are
`9588bc41a20e2b19954474975cefdde511b6bc7952ba32319ded05320029da90`
and
`bb12e41f11dfdd0db1950ad4c48f9491f1b6c9d8a816c8bce9f58f328a9332a2`.

A direct v57-to-v63 suffix replay has hash
`43f024c33f4cabc95a00f92294010808641df9e9dac4faadbd1b539462e7e37f`.
Propagating the accepted selective closure across that exact suffix closes
v63 J297 UNKNOWN index 1 and leaves index 2; the propagation JSON/log hashes
are
`911afa6a14de2bc654784481cf9f0488160178501a5744f38b17210b44826364`
and
`2faec5be95552f603495125327a8b45287ec479a07ce79381efb67dd71fe017a`.
The current effective strengthened-parent residual is consequently one J297
cube and one J326 cube.  This is a certified reduction, not a proof of either
strengthened parent.

`audit_selective_residual_chain_bundle.py` makes that reduced frontier a
reusable production boundary.  It verifies an exact, hash-bound projection
of every effective residual, replays a normal one-root materialized chain,
and joins the result back to the selective audit.  It rejects a projection,
seed, lineage, formula, checker, case order, or terminal hash that is not the
one claimed.  All 85 cube-tool tests pass on the ARM builder; the
implementation is commit `4a26e0f`.

The first J297 residual continuation selected variables `1443` and `1225` in
two rounds.  Its contradictory sides have 212- and 38-byte compact DRATs,
ending at state 632 with one UNKNOWN.  The terminal manifest and state hashes
are
`b5ca189e4460a40476819a45e39f484b6201d311e068fb9d39aceaac649112d1`
and
`20d07933d8fdbee8d460cc944abf8945cc63754d9f4f73e7c9f18119bc42895a`.
The J326 residual was independently projected to the one-row root
`ea3d87dea2477d30ade3559a9a4be49ede27ca626bf9ee04c3153fc92c3a6b6d`
and given an audited one-millisecond UNKNOWN seed.  Its self-contained next
round selected `1842`; a 20-byte compact DRAT closed the negative side and
left one UNKNOWN at state 656.  Its terminal manifest/state hashes are
`fe8cfda8b1ec27dab9ec9a65c3a5608b5ff3c718825078b0c32c9cfe15605722`
and
`93129060c9922f14537da609ccc0f901535b1db3390ad131402e83630903cebc`.

Two deliberately strict audit failures prevented reuse of a two-row seed and
then of a frontier manifest bound to that old seed.  Recomputing the J326
round in a fresh one-root work directory removed both mismatches.  The final
two-case residual chain bundle and audit hashes are
`761bf6bff5f1597b045f9aa5ba2bda286e69002be85c7b8afd6b41c49ddc3008`
and
`f6963bc519da8442ee309877aec3cd8a69d968d1ebc6876aee9123f286581a6c`.
The final selective-residual join audit has hash
`368f1ff9ecc1a82fa4ef2e5a1ec9b7ae619d259dcdc2658a91ad0be67173c747`;
it binds both projected roots and reports J297/J326 state 632/656 with one
remaining UNKNOWN each.  Four-hour no-proof CaDiCaL/Kissat probes continue
on earlier exact ancestors in tmpfs.  Persistent large-proof production is
deferred until one of them reports UNSAT because the ARM root filesystem has
only about 4.8 GB free.

The same two self-contained chains then advanced another 16 rounds per case
without increasing either frontier.  A one-second screen first moved them to
states 633/657; five 0.25-second rounds reached 638/662; ten 0.15-second
rounds reached 648/672.  Every round independently refined one parent into
both signed children, replayed the contradictory-side compact DRAT, and
retained exactly one UNKNOWN.  Across the final ten-round batch, proof sizes
were 8--332 bytes and the selected contradictions took at most 0.079 seconds
under both screen solvers.  The state-648/state-672 terminal manifest hashes
are
`84290c9eb8c150e5ae7b13f4aa5c665e6d508396324d8f1610a1f02029f02484`
and
`9a5ae30a2454b6ff96063218fd258138d4899536b9f1b5395dc390be3a51d15a`.
Fresh whole-prefix replay reports 18 J297 and 17 J326 residual rounds; its
audit hash is
`8d39c339b01a8dc2d65e356c61582598dd3343edbb00049d144b6ba59ef9b73e`.
The corresponding selective-residual join audit hash is
`5eef4ce0b2cb0eb374ab5f042656ca7bcbe3aae8fabac67a00a647f7e1df3faf`.
It still reports one effective UNKNOWN in each case.

Twenty further 0.15-second screened rounds per case also preserved constant
width.  J297 now ends at state 668 after 38 residual rounds; J326 ends at
state 692 after 37.  The new 20-proof batches total only 426 and 966 bytes,
respectively.  Terminal manifest/state hashes are
`882a5dffab1bbd238316fd1bd0dc90921ae2a2f586b907eb049a90c7c7706866` /
`c7cd8dfc152df7f24b06ac5346d6a5e809c02e2d9ee684bc4ddc618e23a88412`
for J297 and
`4a37e994e0692d133c0ad4a80c3f01df18a489db319bbf8e628ce075028898a3` /
`5a4aab5b31ee64acdc1e7fe6bff3b2ad187261582e79b2560d643a9cf313561e`
for J326.  Whole-prefix audit and selective-residual join hashes are
`5abbb178a67ec914928c3889aec25673403ee9bbc953a77966a7e18f2a247635`
and
`a80ff39df4c9ef1c75138dd3f265d1a0a61603faa21d3f8cf7128efd7fd4b593`.
Both still report one UNKNOWN.

The exact current UNKNOWN leaves were exported to tmpfs with hashes
`cea6423b5bbdf96b21b4e8971329c7f2379f88df2da4ddf9ca89b10fb086756c`
and
`cca3f8732b44d1cb669a108e60c3ff45e9c69859a1b04466bcd4f09252e85d24`.
Fresh four-hour CaDiCaL/Kissat no-proof probes now search these deeper leaves
in parallel with the earlier ancestor probes.  An UNSAT result on a deep leaf
would require only that terminal proof plus the already replayed residual
chain to close the corresponding effective case.

One final 20-round batch per case advanced the constant-width chains to
states 688/712, or 58/57 residual rounds.  The batch proofs total 728 bytes
for J297 and 278 bytes for J326.  Terminal manifest/state hashes are
`ee253ce8c5aa24d809ae0a85cdd3584f9d9ad2be32ca9f4f3c76b46b9e4dc2d0` /
`3ad6d531ea3c592163ccbc8553eb8e7e4204ef7ef1bc8eac3f2d754c4e88e828`
and
`792b2f330f05aae9e2d9b9f81ea1a2b1267cf4401b837f06b8b4804bac35275e` /
`a938ec7e30d31ed5c4b3c188a774ed261820a5af7ee7041f273b218cdd406bff`.
Whole-prefix replay has hash
`132c1a693203a1e8c557ab8bda279875daf0a494909f789a488682efa85fe162`;
the v7 selective-residual join audit has hash
`bf022cedc123d7845e97879efe632e60bdb29b4d9a86eadeb63b941529116412`.
Further screened expansion is paused with about 3.3 GB left on the root
filesystem; all eight old and deep no-proof probes continue in tmpfs.

The ARM builder also exposes a separate 2 TB `/data` filesystem with about
1.7 TB free.  The four v199--v202 residual root/work directories were copied
there with hard links preserved.  Per-directory checksum dry-runs reported
zero changes and identical file counts.  Their original repository paths are
now symbolic links to `/data/ramsey55/...`; the verified duplicate root-disk
copies were removed, restoring about 1 GB.  A fresh 58/57-round replay through
the links produced the exact same JSON/log hashes
`132c1a693203a1e8c557ab8bda279875daf0a494909f789a488682efa85fe162` /
`8b52e9fe8d790ec5a3b9cd85e567d29721f24fd0aeb8da38ee7ca66c92d5add9`.
Future residual telemetry therefore writes to `/data` while all manifest
paths and audit identities remain unchanged.

A 50-round continuation batch was resumed through those links.  In parallel,
two iGlucose deferred-proof jobs were launched on exact later leaves exported
from J297 state 697 and J326 state 721.  Their ICNF hashes are
`878aff96e0eac5d04c3918548a22ea6c05407728c9842cfb5b22809635d3c4c3`
and
`ce9946a6f2fa35f2b287ae8e3ebd5786922531fd6709f88d03be5f3dc3fb4db5`.
Each first searches without retaining a raw proof; an UNSAT result triggers a
second certified run, compact DRAT generation, and checker replay entirely in
tmpfs.  These diversify the existing CaDiCaL/Kissat probes without consuming
root-disk certificate space.

The relocated 50-round continuation completed without frontier growth,
advancing J297/J326 to states 738/762 and total residual-chain lengths
108/107.  Exactly one sibling per round has a checked compact DRAT; the new
proofs total 1,382/1,938 bytes.  Terminal manifest/state-snapshot hashes are
`88a2351ed1cd12034aff93678d73b6eafff30f0dbffd1960d4167dd71deb69e6` /
`bb4eb819155e871814d3735de15bddf93c2937a391d8ebd01c9ef3528266658d`
and
`832692d5051da40c552438b9f9aa39ebbef759a93335abcc26558ee69c37f135` /
`5abe2f9aa5b2600db6aee93bb3acd04eb471f48299cb6434470510bc9564e87f`.
Fresh whole-prefix replay passed with JSON/log hashes
`d06b786915dd20cf29b9726315d4f5841bc530a5efdb6cd4b32749c33fb8210d` /
`d5ff13a2d9f8803103eea5f8d57b0bd3d04902e2842611a8b8e2f4bebb1f2f3e`.
The v8 selective-residual join also passed with bundle/audit/log hashes
`df090add36e2645371f86298130b1b92653b6fb543956680c75c6d31c82e9749` /
`6f0f7417e816b4cebd0f27915c44d8a3ec082bd0a92c64ccc64c2dde230925d1` /
`a02f9113d6f84193a20712e4d3e6cdbdd575085fbd2ed07e2bdc08d197f56e08`.
Both cases still have one effective UNKNOWN leaf.  A further 50-round batch
has started from the independently audited 738/762 checkpoint while all ten
diversified solver probes continue.

The exact audited UNKNOWN leaves at states 738/762 were additionally exported
to tmpfs with ICNF hashes
`8f7af087e3913343b962721798999a40d9e1565d5dc3e036ee5b60069a2d7883`
and
`971eb11de255d399e622c225057d3beb99456fc0fe770ee7f1365effe58ddd42`.
Four lowest-priority four-hour CaDiCaL/Kissat no-proof probes search these
deeper leaves.  This brings the diversified long-running solver count to 14;
the new jobs consume only scheduling gaps left by proof-chain screening.  An
UNSAT result can be certified separately and joined directly to the v8 audit.

The next 50-round batch again preserved width one and advanced J297/J326 to
states 788/812, extending their effective residual chains to 158/157 rounds.
The new compact proofs total 2,728/1,242 bytes.  Terminal manifest/state hashes
are
`c83df79fc05ac2f1cc79dbe5cbc3b07ea05f9a3d9dd3143dcbab790d2a4e29b3` /
`d576534bfd1d80d2dffc32d84fbe218b58e3066eb7850ec09f47590311fe7278`
and
`d039a7e988ac2211bd3789fa655301dbc716aedeeb7068d6a9abc2c2861f3960` /
`cff99ca850ec76d4ba04b49dc969c57110a11fd140bb314c62850e8c4b4ed137`.
Fresh whole-prefix replay passed with JSON/log hashes
`d718dc1f8956e39a3c2c6e512d153a9437e909517f02932636c7d726cd6ec9b7` /
`fb22625e633806d5a6172d6a3506689d51bbf71d473afdffa989cb576c08f198`.
The v9 selective-residual join passed with bundle/audit/log hashes
`bd1f2ac59c78956dbc82c10734b7307a16e85d745a2b4c280aafd442fc049d69` /
`a861e529046d1c59d41913febdc5661202d497ffa00ea9bf41ef3a84c0a4c583` /
`0ade4ef0f98c26317a906e980e481f5bfa6f2919592ce253faf0f9700c7b077d`.
The terminal cubes still leave 935/933 unassigned candidates in the screened
1201--2400 range, so a third 50-round batch continues from the audited
788/812 checkpoint.  Both cases still have one effective UNKNOWN leaf.

A third 50-round batch preserved width one through states 838/862, bringing
the residual-chain lengths to 208/207.  Its new compact DRATs total
2,126/1,624 bytes.  Terminal manifest/state hashes are
`3258aefc2612aa46193586c90765d0e3d3687ffe02fb02a42158b0ca8c390b63` /
`63ec07ac919cf802a7efd9c680e34d7fe3a05b37c331e4bdc2cd8895154ad2a6`
and
`5979652a11f990f07dcd8829d6f6dea2c0e0cd5092c125d1ad776afdf8d62911` /
`8ee972f2ccaab81fc63920474cdf94e780a77ef2a36cab7e8ec43ae878674c76`.
Whole-prefix replay passed with JSON/log hashes
`c4250c8e5f0b5e3da4d17931353cb799e970f183d3b96eb3dcd28ac14c96b115` /
`810b5c33161c712ba20c859f144cd0514a8737a14616fca6ac33c976dc6d1377`.
The v10 selective-residual join passed with bundle/audit/log hashes
`5861c56ca3ac409f3f06c437e1893bec13793ebca1e9eab977ccfdc54262be06` /
`2d62a609962b08dfb7e586404b23e531a4bdc5b13a161456add0abc449192cab` /
`d86543f648afc03bbba3cdd5a42d1c0f5466e9f2bbdadd7bfe7ccf9d1410e19e`.
The terminal cubes retain 885/883 screened candidates.  A fourth 50-round
batch continues from 838/862; all 14 long probes remain live without a result.

The fourth 50-round batch reached states 888/912 at constant width one,
extending the residual chains to 258/257 rounds.  Its compact DRATs total only
964/1,306 bytes.  Terminal manifest/state hashes are
`917d0bb68dc4abf1d48b1af4ca1a3018913f6082d750d0216945a6de9d918432` /
`077f2900eaf0a80474d3d53dd7badc0a556318aa8f0c2412e1aa251203e56994`
and
`4fe5a4ffb472e5bc597dd2f6cb1e903eeef91116fb1e3ac4ce18ec579359db7a` /
`6c9c0b8c8e94fddf12490f35b3ac2994e89d1d2b135b0de0d0c509fb9640b667`.
Whole-prefix replay passed with JSON/log hashes
`9085d8b7e5d05df9a453d1de5d475da52aee963f847350e607e2fe57f639b7ee` /
`d25439c4e08fa1cc83791f6084ec00ecd0e821e19d9a5fe99093792f0a920600`.
The v11 selective-residual join passed with bundle/audit/log hashes
`71fc6615bc50c052c4babfa4d32e8e61fc22e144bac993504a64ac12c810c475` /
`03ea805857cbeacf36651af6341c8bad6c7ee80501d093423a42f17ec806c8bf` /
`a8bbd9036b2af04348a2f88945adbf537fbae81cefbb0c7db3bd97b5a0c903e1`.
A fifth 50-round batch continues from the audited 888/912 checkpoint.

Two older long searches also published complete proofs for the exact
state-607 J297 row-1 child-1 cube (`ee349df8...9c9a`): a 579,664,879-byte
CaDiCaL DRAT (`7c650e1a...a2d`) and an 827,999,955-byte Kissat DRAT
(`ceee9990...e70`).  Exact prefix comparison shows that cube extends the
other state-629 UNKNOWN and conflicts with the current effective root in one
literal.  Thus these are independent cross-checks for the selective-overlay
side, not closures of the remaining J297 residual.  Both complete proof
directories, plus the completed v144 Kissat directory, were checksum-migrated
to `/data` behind unchanged repository-path symlinks, restoring root-disk
headroom.  Fresh low-priority replays of the two v135 proofs are running.
The 827,999,955-byte Kissat proof has now passed its fresh replay with
`audited 1/1 verified=1`; the replay log hash is
`07521dbcbd17729a5484e9074d6fd0768dfdfc6e92c49eab2ccc038b4c25ca8c`.
The independent CaDiCaL replay remains in progress.

The fifth 50-round residual batch preserved width one through states 938/962,
bringing the chain lengths to 308/307.  Its compact proofs total 1,736/920
bytes.  Terminal manifest/state hashes are
`77f135208d2f05eee7cec66e7c47cac4de4d667811b0a9574899ad378670aa88` /
`6a1f7e3fdb4ff2672e7e473b5ba7cbac3a17790b5ddf6a1547044e36f6d2261d`
and
`014298bf219f864c3a5f798d307bd70507589197e1d24f8ff6e4d092f4ad2901` /
`6ce8661a1253312af25aa1c0f4135937bac67d48d5dab188ed9dfd3813dc38e3`.
Whole-prefix replay passed with JSON/log hashes
`ed154ae86418536ae5810cced57de7321645b61a78cbe33fa56e1ffd116cbb92` /
`24ede01d98f7a402f0d8ea81aa46f9b675c84d4fee6ae6577ea4874cb45a06a6`.
The v12 selective-residual join passed with bundle/audit/log hashes
`02f52f9b10cc7401ace1db7f478943691528c2f70969cdb0a25659aa8dda5b83` /
`202f72be68969a43afb3f97e6e48f7819f1d17b45a220868672f7542e31c36c3` /
`f87c47b57a5d667483868520daf079f593be7d89e2b6a5143f9d5c39e7e4f286`.
Both cases retain one UNKNOWN; a sixth 50-round batch continues from 938/962.

The 0.15-second dual-solver screen did not reach the nominal end of that
batch.  It safely stopped at J297 state 957 and J326 state 984 because no
candidate variable had an agreed one-sided UNSAT result from both screen
solvers.  The failed rounds are retained as immutable diagnostic artifacts.
Their parent hashes are
`9fdce2bb99585baa88d4639c60d184b38b250f482eb9da271665bd61d5a5823e`
and
`bee64dd0f60908d47b698403ecaef7a562d22d5818894aafb6c91d051fbee5fe`.
At J297 round 957, CaDiCaL returned 57 UNSAT and 1,475 UNKNOWN results while
Kissat returned 1,532 UNKNOWN results; the TSV hashes are
`ec2271ccd048eee35f17201d31765fb6a9d630ce77f4221ce5abefa8c4aff707`
and
`e73917bf38ace69c2d7c52a1b0e2d176e6cc129082f067ff51c37454fb0b9689`.
At J326 round 984, the corresponding counts are 70/1,452 and 0/1,522, with
TSV hashes
`690cb83a2040045e53eb0764f6ab0c6c94a95fe1863405bdafdb5eef4c861474`
and
`84b1f42704dd1ec9beb4679e5e09f4a073720c1f0a4660d91bf31ba9fae1d3fa`.
The identical refinement-log hash is
`3c81285006992e13542629503084d139d2434bd663cffc7de02eafb421f57111`.

Fresh v203/v204 segments continued from the exact checked `r0956`/`r0983`
manifests with a 0.5-second agreement screen.  Their first screens contained
64/58 dual-solver-agreed one-sided candidates, not merely the single candidate
chosen by the ordinary refiner.  The existing queued refiner replayed every
candidate as a new complete binary split.  The proof producer then generated,
compacted, and checked the contradictory sibling under the progressively
stronger exact parent; the heuristic screen results therefore do not enter
the proof trusted base.  All 64/58 rounds retained frontier width one and
reached states 1021/1042 in about six minutes.  Their compact proofs total
87,070/56,624 bytes.  Terminal manifest/state hashes are
`60d3c30e3c1ce37d186b329bdda0e5f7928d1788187daa57187044d52117e0c0` /
`4e033fef0c7417577cbba5cbe9c262cea69bfa21818f0d45d5c133f7c44df5ca`
and
`6dc1e131324d1ccde5a9ee6c471992c558ce9d74183b93f64cfbdefe3f4871d7` /
`9f9149648ce2ec16f1a65367843b582274c66105a15a4b035fca3e67f8bd3651`.

The v4 whole-chain replay checked all four segments from the exact
state-630/state-655 roots, including `identical terminal manifest` equality at
both 957/984 joins.  Its bundle/audit/log hashes are
`0db93e32c0ce2d8c2f2c4d511ea649eb40c226d72cc8e8b32449409429a88478` /
`47b341555b3a691da792bd9884645e68555ce6a56e8286facc449c71005c0591` /
`4582fdc437e575925aff297eab9352fd7be097e0ec72744a59a90d4c2f4336a9`.
The v13 selective-residual join passed with bundle/audit/log hashes
`8146b9782383a407178ed3e39da6a3631573bb41ccab39f790ae9fb33d96a0f2` /
`e5276b1da00f4e836ea11f65905bf290e03d543f8e85582ea5f054d55b9d5de5` /
`ca21dff2a4fc8ba6278a74f5bb28867dfb3e0ff89bcc4a844add7214711d35a5`.
It still projects exactly one effective UNKNOWN for each fixed-pair case.
The superseded v203/v204 screen processes were stopped at checked states
979/1006; no force signal was required and all partial-round artifacts remain
available as diagnostics.

A second screen-only batch at states 1021/1042 supplied 8/19 more agreed
variables.  Their queued proof chains reached states 1029/1061, with terminal
manifest/state hashes
`7caca66138a84f66e7d0c6e5cd4408283478782d9b1b3807b8303d83dce520e3` /
`8c5f2944ebed90a219bbaeb1633fbd467ac039a68d19e17494b67853811f3322`
and
`3670556a5f88ffcb1556614a1577ec3dc18c3fa98e65b9fe21da97804a0e0bfb` /
`803f400d8395253f8df4cea490a46548782eb4d0cf96fd7e9d6501825dfc1fc2`.
The v5 whole-chain replay passed with JSON/log hashes
`c48163bd8a7f1200a477ec62423c2104bb23cb4c791818ec833b7927962b405b` /
`fd480eee468a8b3bed770f7465a7f8958ec217da8223a7e5c30d966effd6bcc1`.
A one-second screen then supplied 1/2 further variables; their checked queued
steps reached runtime states 1030/1063.  A two-second screen-only batch is
searching the remaining candidates before the next whole-chain replay and
selective join.

The independent replay of the 579,664,879-byte v135 CaDiCaL proof also passed
with `audited 1/1 verified=1`.  Its log content is identical to the independent
Kissat replay, hence the same
`07521dbcbd17729a5484e9074d6fd0768dfdfc6e92c49eab2ccc038b4c25ca8c`
hash.  The four oldest diversified four-hour no-proof probes returned UNKNOWN;
this is only a timeout result and contributes no proof claim.

Subsequent 2-second screens contributed 2/4 further forced variables, and a
five-second plus incremental-screen union contributed 7/6.  Recertifying each
binary sibling advanced J297/J326 to states 1039/1073.  Whole-chain v7 and v8
replays passed.  The v8 bundle/audit/log hashes are
`5a31befd8775dfb556765069165dbb8b8960a605bec0eeff2e11d4404e6c2308` /
`d2c2ae35876208036cae40ac9aa9ecb7c19f16791515a8f0519201828ea04945` /
`4f1ef871e75b71291e5512a838978de32108ffca7ff5cdb7f87f62afcc81eacd`.

Screening the previously unused auxiliary ranges 2401--5000, 5001--7500,
and 7501--9746 at 0.15 seconds exposed 689/689, 709/709, and 546/539
CaDiCaL/Kissat-agreed candidates.  The committed
`export_screened_forced_queue.py` tool binds the exact parent, variable list,
screened cubes, solver TSV hashes, polarities, and deterministic ranking.  Its
six queue-manifest hashes are
`8eaab67c514f5b2b75f4eec66d5eb7b1b8e686543a81cdca34252d50a00d1246`,
`8de541642770422baa507568b1528797eee37a42e5322b1a0ad0bb0a3322e686`,
`4e4302dbf15d53f665215693b637346f46b556cb2092cbc9dec5051551ca94ce`,
`796e4222648c3669b74844283b3e2297911fd43fadb793a9440eea21bbc4c219`,
`024e99f25b40b052b97266a3bb3cbd01ab7768d022d1c9a24d389b42fcc5954c`,
and
`d3cfece420c23bb7b7b7ff06730f4bbca558fc2b5ef4d02635f9c633549ff3a5`.
The screen remains heuristic: every accepted sibling is regenerated with
proof logging, compacted, and replayed by `drat-trim` under the progressively
stronger exact parent.

All 1,944/1,937 initial candidates were recertified without frontier growth,
ending at states 2983/3010.  Independently materialized predicted leaves have
hashes
`dd034c89488f2da33422e914d89497453905f4a11b525f554289bd18cc19ef05`
and
`634081076a74780a9c0baaa73e3b752f34f2dcd8124259cfdfcb96426d198451`;
the actual terminal UNKNOWN rows were byte-identical to them.  Recursive v11
replay passed with bundle/audit/log hashes
`ad495f9faa10be43651d15a21d04a61ee136b72d70485a75deaee721cbabc938` /
`5fbbcfd4a9ae82efac591501133c3d980d786a1bf00fcff10c9ce4730486cc0f` /
`5f1cfb34c03946ac4b420f209df735827ab06d866116f4ebba20bf63064e7a66`.

Iterated 0.15-second screens on these stronger leaves produced waves of
292/314, 10/8, 1/2, 2/0, and 1/0 candidates.  Concatenating them in dependency
order and recertifying 306/324 siblings advanced the chains to states
3289/3334.  The actual terminal rows again matched the predictions exactly.
The v12 bundle/audit/log hashes are
`069d2030bc53416f0d37d5728e98639d79157b229e23c9f6de5edab669020f29` /
`b0c93df67ae80e8e39c2a30edf048ac42abfedacd524ace13a0d56e19a60e8e6` /
`402433a0855539181bc355ac96140552ee7eb24de3b16acf84e36b3b10912ae9`.

At a 0.5-second screen budget, the next waves contained 319/331 and 19/17
candidates.  All were freshly recertified to states 3627/3682 with one UNKNOWN
per case.  Recursive v14 replay passed with bundle/audit/log hashes
`d291e9f7192a58aa00148adbbf474debfc1fc748604356f00b92545df652d48b` /
`06a4e2552bdc907acb1e7e866c11fa9fa1b01869123981a8b6628e6b93f467a4` /
`7fc93e1bf64ade3d5ee834e3a36f7828611b46419345b470e91ef481068098d7`.

The next two 0.5-second waves contributed 8/6 and 6/2 candidates.  All 22
binary siblings were regenerated in proof mode, compacted, and checked.  The
exact chains now end at states 3641/3690, each with one verified sibling and
one UNKNOWN row.  Their actual terminal rows are byte-identical to separately
materialized predicted leaves with hashes
`a1e75f03818f52022f81127f580b5a77c462eba4f5a910c3208e4ac772976728`
and
`5b46a8c4c1d107cc08170890c25edb63b43e33fc1ab661e827610d25533a5562`.

The v16 incremental whole-chain replay binds these new segments to v15.  Its
bundle/audit/log hashes are
`216b4cf29737fa009c8ba7a7a057a1fe09a048b19d3569da84c4dbe8950d6bf7` /
`0b98d1612faf6adccdcfd61ab212c62ef22a02676a404341cfe4a0b3ccead4da` /
`83550c386dd9cd99bf7070234685dc6a9dc8b14ae64bd2a68978cce8dd9edb6b`.
The refreshed selective-residual join passed with bundle/audit/log hashes
`9212fd315319efaab5b0761bc3a409ca7534feedab747c014f4be69756dd294e` /
`e98116f22c4a1fa9d3d8a9d73b74cfb95c852dc052b448c34fd03dac914ed7e4` /
`0c39b7c32f2cf3ca7550bfc51fb6c5fb05adc31a65f32c45c1b42dd5e20d86e0`.
It projects exactly one effective UNKNOWN for each fixed-pair case.

The final 0.5-second J326 screen supplied one further candidate, which was
recertified to state 3691.  At a 1.0-second budget, the next J297/J326 waves
contained 21/22 candidates.  Subsequent staged waves contained 11/6 and 5/5.
All 70 new binary siblings were regenerated in proof mode, compacted, and
accepted by `drat-trim`; the exact chains reached states 3678/3724 without
frontier growth.  Their actual terminal rows again equal their independently
materialized predictions, with hashes
`f628a76950abf0623e30050dbf9e95cd16eb19229de6258cc0f15821982eaae0`
and
`6ea270f79df9c6e418af34bdd6021bb5effbdc1d9b64643c6270d37bae445037`.

The optional `--staged-screening` mode now makes repeated dual-solver screens
less wasteful.  The first solver scans every unassigned variable; the second
solver receives only variables for which the primary table reported a
one-sided UNSAT.  Standard projected TSVs still let
`export_screened_forced_queue.py` require agreement, while the selection
manifest additionally binds the full primary variable list, ICNF, result
table, solver binary, and log.  The final proof trust path is unchanged:
every accepted split is still regenerated independently with compact DRAT and
checked.  All 190 tests and `ruff check` pass.  A full J297 run scanned 5,967
variables, confirmed only 20 primary candidates, retained 11 agreements, and
reduced wall time from roughly 27 to 12.5 minutes at the same peak screen-job
count.  A two-variable ARM smoke test reproduced the known `[8561, 5807]`
queue end to end.

The v20 incremental whole-chain replay has bundle/audit/log hashes
`175d30fe0024b169bfaeeb17e169f556a27b35a8844a560dc368db2f4cdfed7c` /
`2d25551e266e7f83ed6d436c18f44be81fd37561fb5ab608ede650e45a7feb4e` /
`2059f97659813617c70a327f536214f16227acb196e3924692432e76d0613913`.
The corresponding selective-residual join bundle/audit/log hashes are
`bf7b13a1f2fd4768367d40e27aeb2a07c25dcd5e35e939126e9d46f33136f672` /
`a80dffbd7c44f813d4954caf86cbd2d05360e4601a9e4c3af39e88eeef94dd8a` /
`e9e69edb57dbcb5274085f387dafb9f261a2095a97c2cadf7cbd7b831b02a248`.
It binds 17/18 continuation segments and still projects exactly one effective
UNKNOWN for each fixed-pair case.  Further staged 1-second screens and
diversified direct probes remain in progress and diagnostic only.

The next staged waves retained three J297 and two J326 candidates.  All five
contradictory siblings were regenerated with compact DRAT and accepted by
`drat-trim`, advancing the exact chains to states 3681/3726 without frontier
growth.  Their actual terminal rows again equal their independently
materialized predictions, with hashes
`36f38922fc942bd497e0fd48b443d816da7c63666dd037f35b9d408355298fe1`
and
`23082e3b638adae7c42b010844aa255130489929e79c2361950f6d97994ae3dc`.

The v21 incremental whole-chain replay has bundle/audit/log hashes
`4baf83cac762ca1c24d87cfb857ebccd1bd4c621db8193bd62049ec09ab247ad` /
`e430e634f6e33c4322a3c8147b3809dc7be1761db4e19d045505b490d1b3a608` /
`c65791ce3393614cd689d3bf89c0f3ae7a1dd407c269c2533a0ec6304eb8b495`.
The refreshed selective-residual join bundle/audit/log hashes are
`fc1ec6d32d845fbc7acc8754081008091f89510c61f1392fda6f9b9f901ea4a0` /
`aee4e29484c3b8c3a48ed367ed40e02f46725daa15d26d934e9d018b9bf89d87` /
`2e2a2c131645e812eba6a399f1d417e69918e3056d95bf07d535137ec2a76365`.
It binds 18/19 continuation segments and still projects exactly one effective
UNKNOWN for each fixed-pair case.  Further staged one-second screens are
running on these exact stronger leaves.

The next J297 staged screen scanned 5,948 unassigned variables with Kissat.
Its only one-sided candidate, variable 9046, was not confirmed by CaDiCaL at
the same one-second budget.  The zero-candidate agreement queue is bound to
the exact state-3681 parent and has hash
`9aea25573c9cad5e2e48777bba047e02bbbb4a0e0df6448628254eed2372bbdc`.
This is a dual-solver screening fixed point at one second, not proof that the
remaining leaf is satisfiable or unsatisfiable.  A two-second staged screen
and independent four-hour CaDiCaL/Kissat probes now run on that stronger leaf.

For J326, Kissat found eight one-sided candidates among 5,891 variables and
CaDiCaL confirmed three: 5232, 5263, and 9121.  Their exact-parent-bound queue
has hash
`532a34ed18cdd87504064b3fba8dca16848fed15fee105e390c21795846fa049`.
All three contradictory siblings were regenerated with compact DRAT and
accepted by `drat-trim`, advancing the exact chain from state 3726 to 3729.
The actual terminal row is byte-identical to the independently materialized
prediction with hash
`d58d631f21b9729cb79a19dd176d53f40776967554ddb20ba0202378068583af`.

The v22 incremental whole-chain replay has bundle/audit/log hashes
`d25d24f112a1746acf657d57dda72d928da8e490a88fbd2c9c686520dfa43809` /
`7214ed3b0d582615ca91226c73e35568ba3a8e0474a795c704a834f3e75ac251` /
`db9b03fa6260908bf16f5fafa981a0bced2ad5bdcec970c66544e58eb3db40da`.
The refreshed selective-residual join bundle/audit/log hashes are
`c228f344658e423363e49018a0d9e72ccd05eb68504c6859bdff6f611b41e127` /
`a2669a8db6435230874e9d56dda4f3144e627a783bdec1ba75e124152532a439` /
`7c48009146aebe48d0fc6ab6f620283fa50b2b50f0fd77fda584124d87c9ea31`.
It binds 18/20 continuation segments and still projects exactly one effective
UNKNOWN for each fixed-pair case.  A further one-second J326 screen is running
on the exact state-3729 leaf.

Cross-solver agreement is useful screening corroboration but is not part of
the final trust path: a candidate is adopted only after an independently
generated DRAT proof passes `drat-trim`.  Re-examining the complete primary
tables therefore recovered candidates that the one-second confirmation stage
had missed.  The J297 primary-only queue has hash
`025e81892dc79cfe86ce7412fe72467d5edc9438e5ae36f758e884dfae086f06`.
Its sole candidate, variable 9046, received a fresh checked Kissat proof and
advanced the exact endpoint to state 3682.  The actual and predicted terminal
rows match with hash
`dc70151dde1f1683fe99080e665810c1de8a5024fd20cc07b9f148a32b621af0`.

The analogous J326 primary queue has hash
`069bc9a6ea9540390f71ea19a218726c0a3e8992bcf85f524d106180d9098530`
and contains eight candidates, including the three cross-solver agreements.
All eight fresh Kissat proofs passed `drat-trim`.  This gives a clean segment
from state 3726 to 3734 and supersedes the shorter three-round v22 segment.
The terminal row equals the independently materialized primary-queue
prediction with hash
`09a9f2461b8026b7f280fc906fac3be4289462be36671b4e5c8986612d62668a`.

The v23 incremental replay starts from the common v21 base and appends the
one-round J297 and eight-round J326 primary-queue segments, so it contains no
overlap with v22.  Its bundle/audit/log hashes are
`0d09ecbd37f42d44f6c001963e1ec59d3c3b48f07b052dabfe4deae553395baa` /
`e59b8115ebd7eea4bc027cfeedf91e5ab8cf3e2dc6eb53cbcb49b8244970384f` /
`9b4ccaf7823caf498683e6e8aaad2371503d8792cd98cf1990b163959f9c072d`.
The refreshed selective-residual join bundle/audit/log hashes are
`763c9472049a8f117f1f10dc06d150ac52496262f8bcec1ca13615b897307755` /
`4e4641790140d161a3486db8d11180e73bd44a54553f318c967e2c9a7c0da2cb` /
`bdfba54e55dc1c3925fd28d93c1c4010d1b5322cf3fd979cbeb9aed0aa266297`.
It binds 19/20 continuation segments, ends at states 3682/3734, and still
projects one effective UNKNOWN per case.  A reverse staged screen now gives
CaDiCaL a full-variable pass on the latest J326 leaf to search for candidates
that a Kissat-primary pass cannot see.

At two seconds, the next J297 scan produced 15 cross-solver agreements and 19
Kissat primary candidates.  The complete primary queue has hash
`de09997d82205f23e10df9f9e19a9601cdad251f4c049b2a3ff981d4bd0a3158`.
Every candidate received a fresh Kissat proof accepted by `drat-trim`, so the
single-round v23 J297 suffix can be replaced by a clean 19-round segment from
state 3681 to 3700.  Its actual terminal row equals the independently
materialized prediction with hash
`3ba53864de9e480eb60d70d3d5640761c262c8ea80c5901a59826d2d244264a8`.

The reverse J326 scan found eight CaDiCaL-primary candidates and Kissat
confirmed all eight.  The reverse primary queue has hash
`c9bee68f6514c01d1f0b75651c969da7320d2f110096022aa318747523ef2179`.
A preceding Kissat-primary scan also exposed variable 8500.  It did not
reproduce after strengthening at one second, but a two-second targeted screen
did reproduce it and its formal DRAT passed.  Both queue manifests bind the
same exact state-3734 parent, so composing the eight reverse candidates with
8500 gives a clean nine-round proof segment through state 3743.  The actual
and predicted terminal rows match with hash
`6abba530077d70d4c4ac70a5cf930159d66e0f1454402c90dd1be5037088bcf2`.

The v26 incremental replay starts again from the common v21 base and appends
only the final non-overlapping J297 and J326 suffixes, superseding the shorter
v23--v25 candidates.  Its bundle/audit/log hashes are
`d82e0b50c214972d9a289c4a30514d373c1b598e4b17055508bff3a322e90e26` /
`aa650880c1131d331c520e3d2098168936654bfa389b4f3aa519a540f06b7529` /
`8bb0d494f5cb70c94598d9f82cde899cd97cfa31b27e1c6028436d08595f91e3`.
The refreshed selective-residual join bundle/audit/log hashes are
`c7124f0a2cc774b86869d55e357fcec4005dacd8365c80a143842a4b0f66b344` /
`e2c99a70828bfeaec47d92ab7974f93f9dbc4f0b273364bb37b45bcfc68fc62f` /
`954ebc8a7d67d84359bd48dc79747321ce1074ed5c69c64bd0d733f5f009b699`.
It binds 19/21 continuation segments, ends at states 3700/3743, and still
projects one effective UNKNOWN per case.  Fresh four-hour CaDiCaL/Kissat
probes run on these stronger leaves, while a CaDiCaL-primary two-second
reverse screen searches the latest J297 leaf.

`tools/import_materialized_cube_proof.py` prepares the integration path for a
successful recursive tree proof.  It does not trust the producer exit code:
the supplied checker must first accept the proof against an independently
rendered augmented cube.  Only then does it emit a standard materialized-proof
manifest binding the formula, ordered cube family and target index, proof,
producer/checker binaries and arguments, optional producer log, and all
artifact hashes.  Existing proof composers and chain auditors can therefore
consume a checked tree proof without a hand-written manifest.  All 191 tests
and targeted Ruff checks pass.

The reverse CaDiCaL-primary J297 screen at state 3700 found three more
one-sided candidates: 2321, 2576, and 872.  Fresh CaDiCaL proofs for all three
passed `drat-trim`, advancing the exact endpoint to state 3703.  Its actual
terminal row equals the independently materialized prediction with hash
`14a3bc7c2eaf3a3ad75722529dd8f6679be1ef5127fb10b6133879a91ed877ea`.
The v27 chain bundle/audit/log hashes are
`ad9e8eb904cb15268701d23ad55ac3f175264ce8c08acbb2a74ac62d96a6265b` /
`9a7db118b6318373107d0c16e070689fe7ab6871cd08a2aa650cd449696d5e75` /
`8b267719834d5968d0fca86bb1137e1cada495b2d06bbd5cbcc42cf92d2b6ccd`.
The corresponding selective-residual join hashes are
`3c4626c9fe3ed0a0f5a5f8cc2a3301590ac7207517baeeea297faa050d80775a` /
`cbb6f467081f649c203b3d8bbf72b053e19d74f6e7411a6cb5564d804a806eea` /
`d9659372cb4ad716420e79aebd0f822d34b4a7c76e9e5aeeda2d2eee36c10839`.

On J326 state 3743, a forward Kissat-primary two-second screen found nine
candidates in proof order: 9046, 8719, 6888, 8864, 9471, 7860, 9083, 872,
and 8925.  All nine fresh Kissat proofs passed, reaching state 3752.  The
actual terminal row is byte-identical to its prediction with hash
`549dda26fa2062f2abf65eccf9b9ac177fef47fee55addbada8b725cb93679a2`.
The v28 chain bundle/audit/log hashes are
`59e3b9591be6499dd9917e5eaabc0ba8bc71cb727e2a48d9140a965469a74d39` /
`d573aad2a4adee7961b767bad35fb9b8552ab267d3e8ff26e9a4fda7d7b9326d` /
`1ccd8d6b5d24c3993c7f458d61a1e72b863ee4f920221a7d2a19eabb6a560502`.
The refreshed join bundle/audit/log hashes are
`0e20397338e0ae00ef5d6be0c7df0d9821ed8836b42e6850cc13ef21adae2564` /
`7dbf2f85417a0e59cb42cafdb2aeefca385ff29636d3bbb544fd4d0284228157` /
`d179805323fe51035df348ccc7023d941672b5a88a679706491f2af84b204f96`.

The earlier J297 forward screen exposed variable 8719 against the weaker
state-3700 leaf.  To avoid carrying stale-parent screening provenance, it was
screened again against the exact state-3703 parent; Kissat and CaDiCaL again
proved the same contradictory side within two seconds.  A newly generated
Kissat DRAT then passed `drat-trim`, advancing J297 to state 3704.  The actual
terminal matches the exact-parent prediction with hash
`d74b5927a13d1f1ef4a3fe3236224ee7071387d7f85aa6ddf740b6653f6685ee`.
The v29 chain bundle/audit/log hashes are
`c1c88cf2fd7995e191d500fd0326b1a2b5e7c068aa60d5e7aaaa8d711f13a68d` /
`5ac64a0e0bc5e84c309279b4a4acfd59a166e2d59dd8ea8cc177d835496d4017` /
`42ae898fa5262ed1b3185f1a53f451fb234cef50830df5d60e9669648c2c885e`.
The refreshed join bundle/audit/log hashes are
`94e29a901fe6e7a291541458aa54497e20f4bb0f234cb29c0be55785ef031794` /
`7942da4574b8625990a5a17f41a17e6ce69747838f3ad832c945604d4756a1c9` /
`f6a2479c5210f046789f79a2e890c61227f619b14495121707ac6b8d34d13fe9`.
The audited effective frontier is still one UNKNOWN per case, now at states
3704/3752.

Two proof-producing recursive CaDiCaL trees continue from the slightly weaker
state-3700 and state-3743 leaves.  At the latest checkpoint they had recorded
95/93 splits and 92/91 closed siblings, leaving estimated pending frontiers of
4/3 and proof streams of 871/864 MiB.  Their output is not accepted merely
from the producer status: a successful root proof will be replayed by
`drat-trim` against the independently materialized augmented cube before the
checked importer can bind it into the chain.  Four-hour direct probes and new
two-second forward-J297/reverse-J326 screens also remain in flight.

The next exact-parent screens found five Kissat-primary J297 candidates and
eight CaDiCaL-primary J326 candidates.  CaDiCaL confirmed all five J297
candidates; Kissat confirmed the first J326 candidate, while the remaining
seven retain primary-only screening provenance.  The primary queue hashes are
`a57000817e48b87d363b4b5ced6a8d9cc30528e61a67041f50fe781c1d62ef94`
and
`fa05e39c9ba131480ec752fcb5ac15de55bb365b9766f5056fb037de2df97179`.
Their ordered variable lists are `[6160,7434,5604,6514,4890]` and
`[5279,8901,7678,1067,8042,5786,9629,8537]`, respectively.  Every one of the
13 candidates then received a fresh compact proof accepted by `drat-trim`.
The exact endpoints advanced to states 3709/3760.  Their actual terminal rows
equal the independently materialized predictions with hashes
`54a50a6c6dd2d8343feaee46668c1568fa4e8b10c74a5203d6e4d10f8af1c99b`
and
`f09f664b39a4d7c0f907a8ec34ceec0d0228be51792959532516587b3e3de407`.

The v30 incremental chain bundle/audit/log hashes are
`e5835dd5f1c5466ffd6d549e13111228b1b084c5c0c587da1c4ee17ec0ddae26` /
`e7ef1e3d7cf71d7e5fdfe59d5782435abe9999dc975e067f497c118bb749a94b` /
`1f59c71f5b9895b51b678c80cb939969cb2df9cf11b4bb279b893f634c41f97c`.
The refreshed selective-residual join bundle/audit/log hashes are
`4290d1deab46b5bbe940530090ed4a4be13eabf8225057b262773c0822cae362` /
`1ad60b11505d55e2ee025c0b08f009e9c1af65a3e6135ab4f08d098456aac794` /
`5088b3e67df358a0cecc5c7e34af7407fa6b50c267de88b6286e174fd8b03d9c`.
It replays 22/23 continuation segments and still projects one effective
UNKNOWN per fixed-pair case.  Reverse-J297 and forward-J326 two-second staged
screens now run on the newest exact leaves.

To add parallelism to the separate root-proof route, the state-3704 and
state-3752 high-budget recursive producers were stopped briefly while their
proof streams and result tables were copied, then resumed.  Replaying the
snapshots reconstructed exact live frontiers of four J297 rows and two J326
rows.  Their independently materialized root augmented CNFs have hashes
`ec1adf42531c3fcb9d41492efcd0207c9f96ee2d2e45ba2bef163e96300970d2`
and
`dda5442bd75d6e74fa104d29cb6ecfaf819ab06c29c1183fc30280a477ca8d4b`.
Each live row now has an independent explicit-stack proof-fragment producer.
J297 fragment 0 has completed, and composing it against its own exact row
produced a standalone proof accepted by `drat-trim`.  This validates that
fragment's output but is not a root proof: every frontier row must close and
the prefix-plus-fragments composition must independently verify first.

The next exact-parent screens yielded two more cross-solver-agreed J297
candidates, 8901 and 7980, and one Kissat-primary J326 candidate, 6706.  The
agreement and primary J297 queue hashes are
`4652eb5b74bfcbb3a2450f02c42b482c37b33add6e4808b902260fc13f62cad7`
and
`221771e9e247d8856a47669c69d5b8de606f92c510b0d81edafa09704e884c0c`.
The J326 agreement queue is empty, while its primary queue hash is
`03f351b5fc7b3867f504dc688484f3c37ff78d34cdf4a055e09b2e5874fe79af`.
All three primary-solver candidates received fresh compact DRAT proofs
accepted by `drat-trim`.  This advances the exact endpoints to states
3711/3761; their actual terminal rows are byte-identical to the independent
primary-queue predictions, with hashes
`c6ce95910a77c0f23c63d72f8a804454b68a96f61e959cd4dca27a334e24ae1a`
and
`c5ec9aa0ea4c0059173ba246760cb1391626c3570e47a078e36b46273be008f0`.

The v30-to-v31 chain extension was independently replayed.  The extended
bundle, extension audit, and audit-log hashes are
`a98cd644398fb65d81c07722efe685c978fa31ce0577d83e2ce566ae680795ee` /
`5601fd9c6797bffa9cc5190fab4d1ed2640d2fb303a6d663dd79a80ad9773a8b` /
`aae3563a9c78eeba9e531b9455bc197e648bdea78571c6f6a003753112b01abe`.
The corresponding selective-residual join bundle/audit/log hashes are
`4029be4a56eb15bfa7b9582f09b3e1963bf2450c797bedc276d1678583088506` /
`8b65919cb78a1c2b80ce3d981f9f3041d89ab56bb172cf934e39da0aabaee171` /
`c1754516ee1c03c68b9abd518e4992ec637845fdc2b9fe0a6d8abd21df64c37d`.
It binds 23 J297 and 24 J326 continuation segments, with exactly one audited
effective UNKNOWN in each case at states 3711/3761.  A subsequent full replay
of all 47 continuation segments also passed.  Its audit and log hashes are
`96a9dcee33c728a0ae7693aab6b2a6776868406f8b77311e39a5f6cf18b3a3b6` /
`a3d2b19dc8523931efee040db8f2877846ef468f2d430e5d22ef8c801e15743f`.
The full-audit-bound selective-residual join bundle/audit/log hashes are
`bdff1daa8e7fba74262b4bfe63f90c017825d78f0f9a1c44ddd0d9d2dc9e3c4f` /
`51b9484785e7faceee73bfc035d6272fbceec7b9164f334d901f880d961fc899` /
`9bf7106a4f6a568186bcf9447751a8eb97f57191111d2ce02ce8e98e5c73c857`.
New forward-J297 and reverse-J326 exact-parent screens continue on ARM.

Those exact-parent screens each exposed variable 8743.  Kissat and CaDiCaL
agreed on the J297 contradictory side.  The J326 candidate was reported only
by the CaDiCaL primary screen within the two-second budget, so it was not
accepted from screening alone.  Fresh compact proofs from the respective
primary solvers passed `drat-trim` for both candidates.  The endpoints advance
to states 3712/3762, with actual terminal rows byte-identical to their
independent predictions.  Their hashes are
`609e64ce4737e66321cb1ecd88f68ea419a50aa400be63109a508dae6603ba22`
and
`085f48627810fb8d921d65e433f067401951512ccdcc2cb93544b3702c3b0319`.

The v32 chain bundle / v31-to-v32 extension audit / audit-log hashes are
`d2425a54c319fb62abc82bd2d9ad97c3157cd57f0fe609bc0cb09dbe8f461c8d` /
`c53b8dbde32b3012fe651644be77d5d94122eca4d7f998993dea78c499fe264f` /
`008e969b7f71ca55ad5b6cf1caac4b44cf1d367bdadacc2519ff23143b5f87a0`.
The selective-residual join bundle/audit/log hashes are
`05ce1d9016986ccae33e3a1732e3d7067d350ae90634c5915f0c2d71dd4f388e` /
`acdc6360b8c54b75de69d99345d32521653ee41c55372ad02bbf6edc3688077c` /
`b56fb8f7c596a6d3d2d7d56f16731471097e7f3a9597b9be226d1147116f25b4`.
It binds 24 J297 and 25 J326 continuation segments and still projects one
effective UNKNOWN in each case.

The three unfinished first-level proof fragments also received a second safe
checkpoint layer.  Their producer processes were stopped for approximately
five seconds while proof and TSV prefixes were copied, then resumed and
verified running.  Exact DFS reconstruction yielded two and four live J297
subroots plus three live J326 subroots.  Nine independent high-budget
explicit-stack fragment jobs now run in parallel with the original producers.
The copied prefix hashes are
`af32795ed546d3595b352a311559dd122fc7b71503a42f2ce75e9b96bd088e6e`,
`5d1ebb11b013977d922dcb1ac9093907d2f5dd890342a694d4ad02df6f8baf5a`,
and
`d7d51e18fccf46791886b0ed21415088972713a8e309a2e582cba9d061aa4de8`.
No subfragment status will be promoted until the corresponding
prefix-plus-subfragment composition verifies against its independently
materialized augmented parent cube.

A resource audit removed computation that had become strictly dominated by
the newer proof paths: three low-budget fragment hedges, four non-proof direct
probes on the weaker state-3700/state-3743 leaves, and two weaker recursive
trees.  Their incomplete files were retained, but their processes were
stopped.  The proof-producing state-3704/state-3752 CaDiCaL and Kissat jobs,
the original high-budget fragments, and all nine second-level fragments were
left running.

The next screens found three CaDiCaL-primary J297 candidates in proof order:
4400, 5968, and 9276.  Kissat agreed on 5968 and 9276.  The J297 agreement and
primary queue hashes are
`aa061bcf14cddb936a8c3749876216c4584a3dd25615fb448f80825c91aed85d`
and
`44a54089823b8be341223248a0b4f26c4edb9d6def8aa7860ed12b28fe30742a`.
The J326 Kissat-primary queue was `[5978,5604]`, with CaDiCaL agreement on
5978; its agreement/primary hashes are
`fe204ead09a5331b17327210bc6e841626593052a89978fef784ad3f7965b6c5` /
`dca6ea15eb294f50dfad2a17a0b38198d7618aed7d0c379b94bcafc6365ce562`.
Fresh compact primary-solver proofs for all five candidates passed
`drat-trim`.  The endpoints advance to states 3715/3764, and their actual
terminal rows equal the primary-queue predictions with hashes
`606eb8dedfc77966cedcf75b49fbfd81bc43d238a89828720ab4dbf154fd410e`
and
`f812c6404a4999b0c6d4627018fbf350a43e6587fde83fc54e2d597102880988`.

The v33 chain bundle / v32-to-v33 extension-audit / log hashes are
`268495ed3fe80b73803d66737b64898a58dec6cd8c8bb3e300fb1fb856ba4def` /
`d9b069c65467916836bf86e5fc6536649065ef656688162201160b944f44d8cc` /
`4035276ad34e7faba3de780d37b494ad30d16251950f3a570378286e06204cb7`.
The refreshed selective-residual join bundle/audit/log hashes are
`902e28c4bbc97903b531ff28444a2074e38a57795ed61fa408e995b0ba7ca26d` /
`69b3b82f3d8905ead0ccadf648f0bb01a1a112a2090006b7019e24b7625abf2d` /
`339d072afda1f5421ac44c97c44bf94569c6a7a9a3f66e809150aaf61068419e`.
It binds 25 J297 and 26 J326 continuation segments and still projects one
effective UNKNOWN in each fixed-pair case.  Forward-J297 and reverse-J326
screens now run on the exact state-3715/state-3764 leaves.

A second, later checkpoint was taken from the still-running strong
state-3704/state-3752 CaDiCaL trees.  The producers were stopped only for the
copy window and then resumed.  For J297, the copied proof prefix and replayed
four-row frontier have hashes
`1a95c662b564e6c919aa61d61270053960cc19f09a02af46ab4930e2c03ab271`
and
`433679b71f11382c04b80ade656085996e5911fe1521a4ac3deb2db20ddd5fdd`.
For J326, the corresponding prefix and five-row frontier hashes are
`0eba17a529fad6594cd478ff7f745d5c3fe4d37788d3f610ca87a50aa567fd74`
and
`5e276bf59ee5cf30e72e848e84510ec580fb28257a4b223aa048321ffd0b539d`.
Independently materializing the two root cubes again produced the earlier
augmented-CNF hashes
`ec1adf42531c3fcb9d41492efcd0207c9f96ee2d2e45ba2bef163e96300970d2`
and
`dda5442bd75d6e74fa104d29cb6ecfaf819ab06c29c1183fc30280a477ca8d4b`.
All nine frontier rows now have independent high-budget explicit-stack proof
producers.  A standalone replay of J326 fragment 0 passed `drat-trim`.  At
this checkpoint 2/4 J297 and 2/5 J326 fragments have completed; the remaining
fragments and the final prefix-plus-fragment checks are still required.

The forward Kissat-primary two-second scan of the exact state-3715 J297 leaf
completed all 11,828 polarity cubes and found no one-sided candidate among
5,914 unassigned variables.  The exported zero queue has hash
`1f01d151d25cfee4a639440fb37f19cd6ebcffc41dccdbd6b3fd516b6c3ff6fe`.
Its independently materialized terminal is unchanged, with state-3715 hash
`606eb8dedfc77966cedcf75b49fbfd81bc43d238a89828720ab4dbf154fd410e`.
This binds a solver-budget screening fixed point only; it does not prove that
the leaf is UNSAT.  A complementary reverse CaDiCaL-primary scan now runs on
the same exact parent.

The reverse CaDiCaL-primary scan of J326 state 3764 produced four candidates
in proof order: 2576, 4559, 1586, and 1298.  None was confirmed by Kissat
within the two-second screening budget.  The empty agreement queue and full
primary queue hashes are
`19b462fce5272943b0d6cc6738f83f5532df987c0f1a43774f55ef5233558422`
and
`0a3b25efacaa3524bd3e635f77dba3fab601f7bbe03ee23d2f80e4cd77881ea4`.
Every candidate then received a new compact CaDiCaL proof accepted by
`drat-trim`, advancing the exact endpoint to state 3768.  The final proof
manifest and state hashes are
`ed4828e7acbd28d5a1f32f139c60b629a244eafec969e41ab3e552dc0a58e85d`
and
`0fa7d18d673d162e699a8209a874597d90bca552ec9c8fb20057809fa0a7536f`.
The actual terminal row is byte-identical to the primary-queue prediction,
hash
`2c1af809b124c02613698bef0eb3114fc4ed1ae965b00a7e93fb124341864cf0`.

The v34 incremental replay appends only this new J326 suffix to v33.  Its
chain bundle / v33-to-v34 extension-audit / audit-log hashes are
`72d2d1e75291a0418b8262a9841d052f17aca9de63ca98901ab1f3e0aeef1af7` /
`4a1db9ea498f06ba0233393102c16967d9396039c92a9362a842ea92f8e03533` /
`07a863d966d96283be79b6a26185ac2b1786450cf889d981e93a74f348820da6`.
The refreshed selective-residual join bundle/audit/log hashes are
`c350150ee8455e818ad8a4d34bd2b2aedb1e64ca889cc373d687acfe0180d24d` /
`5e5594b2b0b5c64d64641ba5b59c1f48fc36ac9631d4412af60aac6c0a011a48` /
`0d86e2ba06df6489050f0d1be608128496f50d44b3bfdd513b99e773a9506654`.
It binds 25 J297 and 27 J326 continuation segments, with exactly one effective
UNKNOWN in each fixed-pair case at states 3715/3768.  A forward
Kissat-primary scan now runs on the exact J326 state-3768 leaf.

The complementary reverse CaDiCaL-primary screen of J297 state 3715 found a
single candidate, variable 4559; Kissat did not confirm it within two seconds.
The empty agreement queue and one-entry primary queue hashes are
`a31e906a6e88398a260b946f5f108e80dd476c2ad116a67a34f9c22eec80e69a`
and
`8ba64d2b58bb38a170ac4941913c840c455644bf65695bb820d65dae40ff0bfa`.
A new compact CaDiCaL proof passed `drat-trim`, advancing the endpoint to
state 3716.  Its final proof manifest and state hashes are
`ef6c25b50819e3d0799bb8644e015073041c35b84f81f80b3bcd31a507de036c`
and
`c3dffebc70d23f0e0de193e3f69b6b7d047d80843f3ea916edebab320e7614c3`.
The actual terminal is byte-identical to its independently materialized
prediction, hash
`6c773ac1a56b348d28aa492f2534f7bcdc7fe0e1127bf8f1d0b5e623f8b71acd`.

The v35 chain bundle / v34-to-v35 extension-audit / audit-log hashes are
`4eb59f6b9b794ab8d98d7a949982d51d596c704466b5ff601acf34d1a9324820` /
`15035e1177597ca92e213fd663f69f79d7b9db8c74b1d41338d9c84295455d39` /
`263ece9a429bc9a303ba26d2bbfb3729f2090d58c1a9c8ad53d4ebca7a5ff000`.
The corresponding selective-residual join bundle/audit/log hashes are
`21a26b9eb80b974087b9b97cc4ad61e059f8fe25c5538694442e9015b657d65d` /
`3fb3a8f33c0401fe51bd2dfe85c3f2c8dbc5dbaa735d478c45448acb39cd9616` /
`ce438b0a63304693aed68b44418db99bb881d7e7dfe0620bc74c0466e4b42f4b`.

The forward Kissat-primary screen of the exact J326 state-3768 leaf produced
three candidates in proof order: 6332, 8561, and 4993.  CaDiCaL confirmed
8561 and 4993 at the same two-second budget.  The agreement and primary queue
hashes are
`f3d58f909c5fe4cb91872ef8de66e5bb424275573af76de3412d1430028b3e4d`
and
`57a5b022e504ee618b38c330ef861194276df0729925f49504939590061a3c64`.
All three fresh compact Kissat proofs passed `drat-trim`, advancing the exact
endpoint to state 3771.  Its final manifest and state hashes are
`e84ad08cbdaec2b449f9150eed2cad1ed06d3c4156d74308c89bd59a2cee9ea6`
and
`cfbb01434b349c240a75ddd0770e29948d743208113245ea2a73c07ca598b20a`.
The actual and predicted terminal rows match exactly, hash
`609bd2e966b0d10dbaa9ac3e4caf0892b253e9d3ca3af83c198c2e5576fb5e6a`.

The v36 chain bundle / v35-to-v36 extension-audit / audit-log hashes are
`ca31894117e634473f239b6d2e13587564ab6262faa671ceb246c400f8b84ef3` /
`64f27308cda10ae551513509d3871965b04f4046ef885e90f73ba920fbcc13b9` /
`c118735c52852cf21eb90aeafb104f32ebbde9214f36a9168af675b4097e746f`.
The refreshed selective-residual join bundle/audit/log hashes are
`9132b6702a501dee0ae6ed70e31ac37e8327d21023cb307b6ad2545d0879618f` /
`6e9ede98b68df2f6e1d4fe73d336784bd627e040a0423beef2a53de58d08d322` /
`da8ccb32cb055e44165804445b4f7f434374b1e62c39ba6940ee1659f73ddf69`.
It binds 26 J297 and 28 J326 continuation segments and still projects one
effective UNKNOWN in each case at states 3716/3771.

After the first of the new screens released its 16 worker slots, a third
parallel checkpoint layer was added beneath the five unfinished late
fragments.  Each source prover was stopped only for its own three-to-four
second copy window and immediately resumed.  Exact DFS reconstruction exposed
three plus four J297 subroots, and one plus two plus three J326 subroots.  The
J297 f2/f3 proof-prefix hashes are
`75cc4ab75362de9dbb39217b51f9ad7b207a4f7603e34796d429062730ee1228`
and
`a80dded06ce490db28b2f4bbc513d2969f3b0091064f2767bf532239520cc3a3`.
The J326 f2/f3/f4 prefix hashes are
`771660df24c492e045b60306d76c3695599b7b8b0cb474486a73936116069bdb`,
`cee808e313526d9ce28480df0cc6b82a5d5649671fad79534de3701b7df86663`,
and
`ce721495ee0bf17245b50862fd379e5c6bbddcf88a49d9b5a7c92a68ac64aa6a`.
All 13 subroots received independent high-budget explicit-stack fragment
producers.  The original J326 fragment 2 subsequently completed, so its
strictly redundant child was stopped and its partial artifacts retained.  At
this checkpoint two J297 subfragments have completed.  A nested fragment is
accepted only after prefix-plus-ordered-subfragment composition, a final empty
clause in a separate standalone copy, and `drat-trim` replay against the exact
parent-fragment augmented CNF.  Only the verified no-empty fragment form may
then be embedded in the final root composition.

The forward Kissat-primary scan of the exact J297 state-3716 leaf found one
candidate, variable 5139, and CaDiCaL confirmed the same contradictory side
within the two-second screening budget.  The agreement and primary queue
hashes are
`81a956db3aecf6c79507cd8e00b0dce662d5884503ae6b137cdbf0088cf04acf`
and
`e8e24ad01265042f519e94d5ed43d68491c7935cc1a4318bd8533a666b82e8d9`.
A fresh compact Kissat proof then passed `drat-trim`, independently of the
screening run.  The endpoint advances to state 3717; its proof manifest and
state hashes are
`1dfcc28de42624d80af6144a8b9c9d7992e683dc5eb1b11cee591f681057deeb`
and
`d405091f5afead83151a8e0daabdb0a0c138fdbccd1fa80e34aba78ee8a43bc4`.
The actual terminal row is byte-identical to the independently materialized
prediction, hash
`343020bf56c06ac1d9f4c57c1ce64c580f639687fb09827e89f6e730ebc059ff`.

The v37 chain bundle / v36-to-v37 extension-audit / audit-log hashes are
`07eb96ef38b3359deb42acfff357ebefe33f60ba1c538edcf5e2e8e0a161c233` /
`2dad3dfe102520f4148a91a42d8591b4ba0a75dca7ef3def2710c4189550e181` /
`0b76f95a20d2485ef359b4fadceb9b78f148cf21d6957370df454bfc9e65b009`.
The refreshed selective-residual join bundle/audit/log hashes are
`0096a501ae1070b06142743a769196c3c81764e77d1697567ee3adf8b6c06d25` /
`0354c41db0d47c16c37a417d6b512788a5b7bd3768dc72d92e42ae6639a66e3e` /
`2e75bc4f9792447810648b7ce30661eb6edc41477de2d857c45c00dbcb2bb89f`.
It binds 27 J297 and 28 J326 continuation segments and still projects one
effective UNKNOWN in each case at states 3717/3771.  A reverse
CaDiCaL-primary screen continues on the exact J326 state-3771 leaf.

One further third-layer producer, J326 f3-sub-0, has completed with
`status=20`.  Its sibling f3-sub-1 remains open, so the nested f3 composition
and standalone replay are still pending; this isolated completion is not yet
used by a parent-fragment or root proof.

The reverse CaDiCaL-primary scan of J326 state 3771 then completed all 11,692
polarity cubes without a one-sided candidate.  Its exact-parent-bound zero
queue has hash
`1f7d83b6dac59224d56c69f666cb552a77dbbb50f35eecd0107bb8b3510cd237`.
The complementary forward Kissat-primary scan was also empty, with queue hash
`12692e6e51a3b8e6b6b1e8e094029bbc392ecd593d5828ffaa6cf020073c1773`.
Both independently materialized terminals are unchanged from state 3771,
hash
`609bd2e966b0d10dbaa9ac3e4caf0892b253e9d3ca3af83c198c2e5576fb5e6a`.
J297 state 3717 likewise produced empty reverse CaDiCaL-primary and forward
Kissat-primary queues, hashes
`5e1181aa703974f0683cccdee7e4ef6751d0b15dddf5e15c95546b19120eb0c9`
and
`1e6c6c916a5f67840115dcd5d1f4b57409a043f288acc690e7561ca48ee67b82`.
Both independently materialized terminals remain unchanged at
`343020bf56c06ac1d9f4c57c1ce64c580f639687fb09827e89f6e730ebc059ff`.
These observations bind complete two-second screening fixed points only; they
do not certify either leaf UNSAT.  Both exact residual leaves are now fixed
points in both solver directions, so subsequent resources are assigned to
proof-producing trees rather than repeated screening at the same boundary.

The two direct 14,400-second Kissat attempts on the state-3704/state-3752
roots both ended UNKNOWN, with neither a SAT model nor an UNSAT proof.  Their
partial manifest hashes are
`dcdf1a1e7d8d8262e1aad79876a51df1a57a6d02637d3b37f3c433fd7c622f8a`
and
`0ae35cffc7f7435a9e12e70cec7aa4770076f7ef283bc9d0ce8ab4de497fc03b`.
Independent allow-partial audits each report one UNKNOWN and have the same log
hash
`3d9c660d9fe1ad748481036a6378c600bbec37efa5e948ac800d08be7a4e6508`.
The corresponding whole-root CaDiCaL trees also exhausted their global
budgets with `runner.exit=3`; their proof traces are incomplete.  The usable
work is retained by the later v372/v373 proof-prefix checkpoints and their
descendants.

`tools/replay_cadical_dfs_prefix.py` now reconstructs a single-root
explicit-stack frontier from an immutable TSV prefix, rejecting inconsistent
attempt/depth order, repeated split variables, and SAT rows.  Its manifest
hash-binds the source root, TSV snapshot, optional binary proof prefix, and
output frontier.  The full Python suite passes 194 tests under
`PYTHONPATH=src:tools`.  On ARM, a real regression reproduced the existing
four-row J297 and two-row J326 checkpoint frontiers byte-for-byte, hashes
`f5fcd8687995dbb2c7df26b9cbf00267c5f3c217e950ac3a97e8866fb7418b53`
and
`b82c235d6f671878c3eac6a23e45d7c157e22a04f26f388d2e7b0341e9c25812`.
The tool and tests are public in commit `e94301b`.

This replay supported a fourth proof-parallelism layer under six remaining
third-layer roots.  Each source writer was stopped only for its own 1.8--2.3
second copy window and then verified running.  The reconstructed frontiers
are:

- J326 f3-sub-1: two rows, prefix/frontier hashes
  `7bcf96372844794bbfc8c3c8c54538a8c80d903736b0359a8615d0c05dcb819d` /
  `981390830d1237b9a98233770d22820588829affb4ad36b91f39e0ab7fdf6326`;
- J297 f3-sub-2/sub-3: four rows each, frontier hashes
  `bb18637bca5497309a5f9c1db1d310c3919f4f7cbea129249102c6ad79b69e01` /
  `20d564c73dc44ccc32b1a33a1910d55fd78b8c4224db6c2cfc9063216cee39f5`;
- J297 f2-sub-1/sub-2: two rows each, frontier hashes
  `149a85faaca06e5dbfa308ea81a78ce6de0e4107d17063b319f7ec719d05b21a` /
  `5805cd0a6325d1a41edcff200e92e694ca631be636610fa92cb8782699d4f2ab`;
- J326 f4-sub-0/sub-1/sub-2: 2/3/4 rows, frontier hashes
  `bd80a65bb70bf88056d9607c4f9f42b0e44933ca8de9ae4472f6ac956f093327`,
  `56d04c87b8155abe9cde3dca1f2a8091165cb996930d3658275e2b5043b760c0`,
  and
  `6996b2f6d9b24001cea40f8554bb67e8c09b281f30ebc1c1368709b341f575e8`.

All 23 reconstructed open roots received independent high-budget fragment
producers.  At the first post-launch audit two had closed.  No fourth-layer
result is promoted until every sibling frontier closes, its no-empty
prefix-plus-fragment composition is checked as a standalone proof against the
exact augmented source-root CNF, and that verified fragment is recursively
composed at the next level.

A fifth checkpoint layer was then taken beneath the two unfinished J297 v387
f2 children and the two unfinished J326 v390 f1 children.  The four source
writers were stopped independently for 0.47--1.02 seconds, copied, and
immediately resumed.  The hash-bound replay results are:

- J297 v387 f2-sub-2: two rows, prefix/snapshot/frontier hashes
  `63c18941439baa0a3b2863288b3482f97c0c6c0344d897bbee0d7a54deaf89d3` /
  `b9683a3d74017771f9b4865a5c5c50a5fb7bb005846a3e826dabb544dbad92b1` /
  `52e2d74f4ca2b6c5bb49bf7d0d7089b8f3682fc5cef3413044ab684e56491c57`;
- J297 v387 f2-sub-3: four rows, prefix/snapshot/frontier hashes
  `afeead6f6c4acde5d22467eb932ed38da10b1070165dfcc6a53ef2fde98f7206` /
  `d7964e813d8a9f4f14adcf1eb90940ed7f20ea13f240114c7af74e20291c5dba` /
  `518bf9102f2a66a6ded811d8b1cdb6e7b4648dc04e97b80c8f1cff0ca436fd2b`;
- J326 v390 f1-sub-1: one row, prefix/snapshot/frontier hashes
  `a87202a5449bbb452e6d48dee31659e96f523be0d0a2449792e971d96190694c` /
  `260bf7d4394603214a238811515569e52accc1cada847907e7c9c909f5a2deb3` /
  `31d5a289935991a03a74886187433177cd16ccdb091c33c3dc041318a1dca316`;
- J326 v390 f1-sub-2: three rows, prefix/snapshot/frontier hashes
  `99d0c7761e9d27d172b9674e7609dd3813e154f64236bc0395dac0a32ae1ba45` /
  `caef343e4a6aae1cffc78903942e0782b01c4a62eb0715c80559b0d0c26b7869` /
  `3666b720bb7e6cf1e0f13ab548c6af93a997e99482fefd019b70aef9dd7c034a`.

All ten fifth-layer rows have independent high-budget fragment producers.
The first child of the three-row J326 group has closed; its two siblings are
still open, so this is not yet a composable parent fragment.  Machine load is
about 47 on 64 cores, with 165 GiB available memory and 1.6 TiB free on
`/data`; the present bottleneck is search-tree tail latency rather than
hardware capacity.  Further splitting is paused in favor of completing,
composing, and independently replaying the existing groups.

`tools/finalize_cadical_dfs_checkpoint.py` implements the promotion gate.  It
checks the replay-manifest prefix hash and frontier count; requires each child
producer log to record `proof_fragment=1`, `root_index=all`, `status=20`, and
one cube; validates binary DRAT clause framing and rejects embedded empty
additions; then writes both the recursively embeddable no-empty fragment and a
separate standalone copy with exactly one appended empty clause.  Acceptance
requires the configured `drat-trim` to emit `s VERIFIED` against the exact
augmented source-root CNF.  Its output manifest records SHA-256 and size for
the CNF, replay manifest, checker, prefix, ordered children, logs, composed
fragment, standalone proof, and checker log.  Three focused tests plus the
full 197-test suite pass.

Later resource sampling showed about 26% idle CPU with effectively zero I/O
wait, so two additional selective checkpoints were taken.  v393 covers the
two long J326 v386 children:

- child 0: one row, prefix/snapshot/frontier hashes
  `397d8903ec15f3cb4a7a837fb51e4c5f27f535d33b51d2dd689f560c2e619ef2` /
  `c91e465368b5dff592a2bf02b0bfd0da078db8b377add1c8ee33169b6bc4cd09` /
  `01c9e07bd0a43dfb3b16a2c34a1112b25ca71617786c1f0699be3e57811be423`;
- child 1: three rows, prefix/snapshot/frontier hashes
  `73439f3b9ead86331fb4efbc8a4ce9533c31b1c0a5526f3001081fe5e1812f4f` /
  `9367bc4c1ffbffea5b64e6d5543b1cb1dba8b0dd21ba7f6bc5e5b573267c9c03` /
  `aad047231c80a2eb5032158c56b7f84ea49ec67f86736618d472124159e99128`.

The one-row checkpoint was retained only as a recovery point because a
deterministic duplicate would not add parallelism.  The three-row side was
launched, adding two net solver cores.  The original v386 child 0 subsequently
closed directly.  Its 1.2 GiB no-empty fragment passed standalone `drat-trim`
against the exact materialized child CNF in 1,264.335 seconds.  The augmented
CNF / fragment / standalone proof / checker-log hashes are
`ad3681a84591f6551ba7c8b9f52096b557364545c8d1ab3ad32d5db7d898b541` /
`54c527e5f64988c5daa0f0e2eac7578687799d2359dc61992af40ec083bd8ab4` /
`90d2abb532fa622b2415efb14180291d41dc113445e939abd69b7a6832a0c48a` /
`e8637529b536146fdf30474acdd07662f1d749dec488c9c303eef7438c33141d`.

v394 covers all four long J297 v389 children.  Its f10/f11/f20/f21 replay
frontiers contain 2/3/2/2 rows and have prefix/snapshot/frontier hashes:

- f10: `860176b27e4081fe37bca92466716740d894bc301d2bc7ee0dbd5a17a4948a77` /
  `b46d7b9caf59cf78b607a335b5683e84cc8e2b14a5881e9fa57bd7ca855bbf70` /
  `76cc43f28bcbaa17807a09368788516d074c358e6da40052045be10d7579ab57`;
- f11: `662acc7fe72ed51c631632dfc814cf4df2b12f136a1814a7320ca536446e0c3b` /
  `f08f5d2af1b98578c656d290fbb1da6dd56004eabaf401b4d928cf1d963b2ec1` /
  `fc84f8c775177d9ac2e3aa4dcc12991d28030def715311fb7c369ea8239c689b`;
- f20: `2bcc501c30f85946647659af155721145dcb5932e85530451ebc20389fbd910f` /
  `301b3ea2962b4cd01504a886954a5125a8c484b01c769ae8bc975caf5bbc2219` /
  `93695bd8eeadcc290ae9206ebe08b5d64468438aa4bdd21a4e37d733fdb47162`;
- f21: `66b5ae145858ef7fb12e17fe0aadc3e42f8ccb343e1ba7c361c5dafda239d39f` /
  `2fe4d3dae710f345d19a1bb79c32b1ae52357cc059456a74a2954bb093fd077e` /
  `daa3583eba2543c06dbbc54b1983314aedac8937f6307506eb73d1b70a9271ad`.

All nine v394 rows received producers, adding five net cores and raising CPU
use to about 92%.  The first child in each of the f10, f20, and f21 two-row
groups closed within minutes.  The original v389 f2-sub-0 then closed
directly, superseding the f20 checkpoint; its remaining f20 producer was
terminated with its 605 MiB partial proof and TSV retained.  The f10/f21
siblings and all f11 rows remain open.  No group is promoted before all of its
children pass the finalization gate.

After more direct parents closed and old races timed out, v395 checkpointed
the remaining v390 f0-sub-1 and f2-sub-2/sub-3 roots.  Their writers were
paused independently for 1.3--1.6 seconds and immediately resumed.  The
f01/f22/f23 frontiers contain 2/2/4 rows, with prefix/snapshot/frontier hashes:

- f01: `4324df36a7a290b4b1d4622e479d4e47048c49c07b4b7abaf643b5743e6a206d` /
  `d407fcf04c2c069f2e3498606e725bcf65c6a8810fbf0946b58f79c35bef7fcd` /
  `6f9e5fedc39dde2de1f1c819c9c6d5bc466eb12f37eba5f8af75c6134d291cf5`;
- f22: `dbef1a68a4b92fe300484fd9a63b4fdaa9dfe2821ce33b64c2c9bb551b0c164a` /
  `2c2a2f8b52df8369f1054348ba61d90aa22226a5d8277bd4f9b1c76c7e67e8ff` /
  `cd579be2ecf834f9ce227c696ad3a58fd70aa6dc3e40013ff3386691450bff98`;
- f23: `822fb7de2b77603229e92ecca2397c8a626280c3f8ce59ee3a548a2816f2980a` /
  `e2c831d4c9017e10f5e0b9aa3e7ebf280641125f41255a439b7e05a7bb604323` /
  `f758e8900c8bc9db4afdf59bab857a2827c8d25c5a49321e10187136c6026881`.

All eight rows received producers, adding five net cores.  f01 child 0 closed
within one minute; its sibling and both other groups remain open.  v390
f0-sub-0 and f2-sub-0/sub-1 have already closed directly, so v395 targets
exactly the remaining sides needed to complete those parent groups.

v396 then checkpointed the three approximately 1.9-hour J297 v387 f3
children that had no deeper descendants.  Their writers resumed after
independent 2.3--3.0 second snapshots.  The f31/f32/f33 frontiers contain
2/3/3 rows, with prefix/snapshot/frontier hashes:

- f31: `c30296b7b4634d8cda9aa34c6165cbf7499ecc73dc5d35f0736b0d3a134a072d` /
  `332bd8df11a8ab2acfddecdc969d9651f39e170b2e0f3ba6fe7c0d9084a2169b` /
  `fedc3b55ba47c4781ef360f62834dd0e59d840832d74192ad794607659c91b42`;
- f32: `305cf7f481ae0b9217f4f13ec09038a3bb6057daaad09d3f896d6b88e9cc7463` /
  `e0d996f3f8ecbdb78ab0b72bfbf3215805806cc8f1d417f1894845ef2e7b6256` /
  `555a441958eee000c7fb36096356cc297591b07217c3a786717a9acab84b24bc`;
- f33: `3138888bbb37ff087b64d43a76191ee22571dccdfd24f53aef48152d0164d941` /
  `5352cd4a03ba84f5b675fc82002e0f2627b9c94138f1def069d0ee6e5fe3d127` /
  `358f246cd6609edff162972d20b03181887b766a6bb228b546b5e45fd2a409ce`.

All eight rows received high-budget fragment producers, adding five net cores
and bringing sustained CPU use to about 90%.  No v396 child had closed at the
initial post-launch audit.

v397 targets three J297 groups that were each blocked by one final sibling:
v391 f2-sub-1 and v394 f10-sub-1/f21-sub-1.  The source writers resumed after
1.5--2.2 second snapshots.  The f2s1/f10s1/f21s1 frontiers contain 1/2/2
rows, with prefix/snapshot/frontier hashes:

- f2s1: `cc1bbe62c849f0aeb00fb67a0ae5e59792f39e042b73d17025f2f85c5695a426` /
  `bcbd1b1e616d454fcabf96fcdc17a3f6d3978d0d51d235a426dc7da11b5721f3` /
  `ce4abe1113419ea83cf5bb391b3240f35d5f07367740e00b572ef414e97caf29`;
- f10s1: `236e6bf10514f5aed6dc7304d6a93753ad372db8e7c7049dd113da9ab4fb4e69` /
  `9b5934040a13b205e55f268c6d8ddab49306584c6aed80e29321462337aa93c8` /
  `59cd6cf7ee10902662ff7d9dbe6b1ef5238b48ff666bcc8df1a0e9e522eb4b79`;
- f21s1: `ba13e66154b080e4bbcb727f3befe8184111185fe42d9f23701dcb62f964492a` /
  `89828152cb34ac29c2e7b5d800969e9bd6757f942b34c209ccdbfef4624cee97` /
  `a9c9ed9412252f5997e3da1a211c4dfa89303f59de71c4bff94ac4c543dbf03b`.

The one-row v391 recovery point was not launched as a deterministic duplicate.
Four high-budget producers cover the two v394 blockers, adding only two net
solver cores.  Neither two-row group had closed at the initial audit.

v398 and v399 target three more groups blocked by one final sibling: J326
v395 f01-sub-1/f22-sub-1 and J297 v396 f31-sub-1.  The source writers resumed
after 1.2--1.7 second snapshots.  Their f01s1/f22s1/f31s1 frontiers contain
2/3/3 rows, with prefix/snapshot/frontier hashes:

- f01s1: `d75be4111283016ccd6cc4ce51ffb019ede88c172ebce2563ba64af50e68da63` /
  `42bed09a4c7255e863ca996a8dbfddd10f78508d28bd22e33572e8e46e1689ae` /
  `fa82f1028dc84eec1b16adf11540cf893c42f00c7e0319df4ccb4c44a54ecbfe`;
- f22s1: `ed11d2a376a8f5011d571c14cf1c9d905a0ca48332b24053ec038f2accd8453b` /
  `f9b4e81572b20fef6063a1b86c59de821052c758b1b8d4b19610bb4deaf49c6a` /
  `c7a1043ec47e7d47be92315fd53ff4a61a46b77eec7dbbb068ccf29a19580714`;
- f31s1: `62f71019d0d50a1b0f09dec02153d5af9f03c6287b1ebf93215ad4c4e175eeca` /
  `f5b38d7e7871fd062606474724205ed2ed8f9b473975fbb2520bbeb46433c623` /
  `68f8c37d04c78be7d64ce436bab08fa63222ef24b245ffcc825028b04bbed7b3`.

All eight rows received high-budget fragment producers, adding five net
cores.  v398 f01s1 child 0 closed immediately; its sibling and both three-row
groups remained open at the first post-launch audit.

The original v387 J297 f2-sub-2 producer later completed with `status=20` and
`proof_fragment=1`.  This superseded the v391 f2 checkpoint before its last
child closed.  That remaining redundant producer was terminated, retaining
its 1.9 GiB partial proof and TSV.  The original v387 f2 group consequently
has three of four direct child fragments complete and awaits only f2-sub-3;
the same last side is independently covered by the still-running four-row
v391 f3 checkpoint.  This isolated completion is not promoted until the final
side closes and the exact parent composition passes `drat-trim`.

Because the remaining v391 f3 children had each run approximately 2.6 hours
and collectively represent the final unresolved direct child of the v387 f2
group, v400 checkpointed all three.  Their source writers resumed after
4.6--5.1 second snapshots.  The f31/f32/f33 frontiers contain 5/2/2 rows,
with prefix/snapshot/frontier hashes:

- f31: `72883b65ad5866c56211028a317bfcaa8f827a8baf6a4014a92b2ef1306180f1` /
  `ed66c304fe3f96372e548e11fd7452c3951e7a7feaeda0f35589558a0d62584c` /
  `a1d3668af6756a987816f862c62913396ca1b87b91c0ababdf6cea72158d1f25`;
- f32: `913b4249dda52fad440db5df12ff97820b5b068fd2b8bd2411c42e8c67ec82a2` /
  `6d90017a0ee57d3d8f6226c2f46523d2b1f8819f7a52d4afeb3536490ab6c7db` /
  `999b6e1b8c2b95c61ca525f8492795736706b295715c8e276d3a406ed4a5b685`;
- f33: `d504ca105d4aa08e099e65cb361c3973836a61a9669215fb5626ef42ada6b90f` /
  `31cb18e274dde7b3aba661f2e795025c80df2a7f66c072ba509b016674371539` /
  `049bca7160ad5140949c65c6fde8322f066d71879f04abd7b75c53aeb065318f`.

All nine rows received high-budget fragment producers, adding six net cores.
Three of the five f31 rows closed in the first minutes; both f32 and both f33
rows remained open at that audit.  A v400 child group is promoted only through
the same no-empty finalizer and exact augmented-CNF replay gate.

The v400 f31 group subsequently advanced to four of five rows, while f33 row
0 also closed.  After the lone remaining f31 row had run 36 minutes, v401
checkpointed it with a 0.974-second source pause.  Its two-row replay has
prefix/snapshot/frontier hashes
`aa94765a0d7fc028adb16620cdf0d6b9cda486aca6df6220e22c828dc7c9cd06` /
`fc3ca35e73b6822dc8d21f54bc4ef8534a950ad7ad830617079b44f6aee6e509` /
`b16f46b3a043f975d8e09212c1f53fef869fb65cd3d59bf435e64456b6e2c405`.
Both rows received high-budget fragment producers, adding one net core; both
were open at the initial audit.  Completion of either the original source or
the full v401 pair will finish the v400 f31 child group, subject to finalizer
replay for the checkpoint path.

v401 child 0 then closed with `status=20`, leaving child 1 as the only open
row on that checkpoint path.  v402 checkpointed the child-1 writer after a
0.470-second pause and resumed it immediately.  Replaying 24 snapshot rows to
maximum processed depth 13 produced a three-row frontier.  Its proof-prefix,
snapshot, and frontier hashes are
`34f9a91e3d12a2ab57513cf620e82357f04adc085986cc4b1903e97209c718b5` /
`79ef57aeec135a29f54deb950ff061b93ad77dd36007049d693e598f968d8593` /
`65d8429a76b4a8ddcd92a8a3bb2c38c0accabea24aa53635532acb3f61de2955`.
All three rows received high-budget fragment producers, adding two net solver
cores while the original v401 child and its v400 ancestor remain live.  This
checkpoint is promoted only if all three child fragments pass the same exact
augmented-CNF finalization gate.

Three more last-sibling blockers were then checkpointed selectively.  v403
covers the J297 v397 f10s1/f21s1 child-1 writers.  Their source pauses were
2.829 and 1.946 seconds, and replay produced one and two open rows.  The
f10 proof-prefix/snapshot/frontier hashes are
`002d8df44816e889ee467c8e1fc122bf92b41a94e796368982ae0f7db3419b5c` /
`6a7f4484b5b9c82fa11bb6ed9cfc8a365b399a20db4a598fb401ba01604930fd` /
`10a7814e5225a2ccbea337b0e3a0736f304008dd536c3f5517aa019c53ffd1d7`;
the f21 hashes are
`fe875a0036d851187a2760a14ca3872e609c51b6f116d1e8b4009f9d32ed3b6b` /
`a7380c0ec5eaa454143d28d95369f382362841d12f6404498deb71c66cd58041` /
`836383f63e67e0747cfa19d2c33fd3c89b54d814fe540a5185320e7dd376bdae`.
The one-row f10 checkpoint is recovery-only; both f21 rows received
producers.

v404 covers J326 v398 f01s1 child 1.  Its writer paused for 1.939 seconds,
and replay produced two rows with proof-prefix/snapshot/frontier hashes
`0d0c7f4d9868b6e2456c3f9dc6cbf6a28d42b6ca3b158f6c80f977e9b35a5f4a` /
`80e3500248856bc6cbf762b6d75a3aea84bbb57784451a6e6a5d235e50fb334e` /
`3e5b80b612488511cc28becbc5190268d74a19fd000a196ac95d61ab0c3ddde0`.
Both rows received producers.  At the first combined post-launch audit v402
had already closed two of three children; v403/v404 were still open.

The sole remaining v402 child followed a serial-looking split chain: each
60-second split had one side close quickly and left only the other side open.
v405 preserved a recovery checkpoint after a 0.260-second pause, but exact
replay again produced only one open row, so no duplicate producer was
launched.  Its proof-prefix/snapshot/frontier hashes are
`517ac22ff97edb5e1e17fca5640da7799117d7e9fd42508bcec95698fd60ffe2` /
`51d9073895f1dfe8c0501359aad81c9f409267ed89b56cd34e52771274c23c05` /
`739fc5a734b8498454e3ba23676d653ea4d698813228264f5b9d4017390dfb8c`.

The available cores were instead assigned to three sibling blockers on the
same critical v400 path.  v406 checkpointed f32 children 0/1 and f33 child 1;
their writers paused for 1.368/1.089/1.543 seconds and resumed immediately.
Replay exposed 2/2/3 rows.  The proof-prefix/snapshot/frontier hashes are:

- f320: `a8b72bbb6d5f854f9afca288ded08c2ca72889064ace43eae5b3d4bc82b18c24` /
  `41c284bda6b211add1d05bb2dff9503d060635d53558e9679008373964d78432` /
  `a4ff080930e08a25013c933310bd680eeac7973389a7f782e190ae86df30120b`;
- f321: `291576503f374beb8f91667f90899283fe5889bb0db0e7a707e700635eba1764` /
  `037d4d0d5d57cec33aa72f80d4e576fc42baed1cecbdfa64bb47e601d73a136c` /
  `4a95d1796bb1ff4e3070fad776fde0e37d23ad5f83dc49a2db6d5462bdccfdf7`;
- f331: `6d1be8112e1a872af20b58747e1829974607174978715279d68c0fb2970cc6de` /
  `3b999495d5e3699668d34d8ab4c86f8ccc208bd611c9b5cabca757f208f4097d` /
  `2a2538372fbe0b2a4cc893545d743926b1cd85062de6274c018fa4062a1e23ad`.

All seven replay rows received high-budget fragment producers.  They must be
finalized as three separate exact augmented-CNF fragments before replacing
their v400 source children.

Although v405 has only one row, it also received a deliberately different
producer configuration: five million initial conflicts, ten million maximum
conflicts, five seconds of lookahead, and a 600-second solve budget.  This is
a strategy race rather than a deterministic duplicate; if it closes, the
v405 prefix and its fragment can replace the remaining v402 child after the
usual standalone check.

The final available solver cores were assigned to v407/v408, covering five
large last-sibling tails.  v407 checkpoints the three J326 v398 f22s1 rows.
Their pauses were 1.922/1.814/2.354 seconds and their replay frontiers contain
2/1/4 rows.  The proof-prefix/snapshot/frontier hashes are:

- f220: `15fecfb59661bfe7b351751fc5076b69f4eaae7a61ac6fbe2a9603bbe0aa4a1d` /
  `2ffa758dcf4aa8a8cf9ea078042145692cd802a9def9b76f4cf3fef3c82a8043` /
  `36a267770f3eae6e4474469464deead4bd5ab3ee30ac91435d41b8af78b7e76e`;
- f221: `8f0980da8c10781b4ddd304fb7b9adb4a9b815288ad6a0975ca2b5674d0075a8` /
  `c4cea451229bc371ed63e22c06f5a0f4b8d52e23b3807d8053d405213be6a39c` /
  `6cbfb6eeec156d355737be83dd6811eff1078270dac2be2b6d0bdc0934646e89`;
- f222: `a0c883818bad4f4fbaa082ea45415eea2b577eb0c9082c041803b2cd81f6c16c` /
  `ef6afe40bb93f09a51e004e21cd414c85d3d00cd7779b6ba420aeb24925a58c8` /
  `743fb1b416d387249159ea6d17c24ee8ef9b85caf28d23b0d5c4cc166d434538`.

The one-row f221 checkpoint is recovery-only; all six rows from f220/f222
received producers.  f222 child 1 closed almost immediately.

v408 checkpoints the two remaining J297 v399 f31s1 rows.  Their pauses were
1.688/1.960 seconds.  f311 replayed to one recovery-only row with hashes
`b0984031d46f930ef0f6dad6765b3a7f61d997c2d941143d64143e94e4618e5c` /
`4107122e19ddec33ccf04d0a553203dbf1d73ca19123848a533fe8eb202b1e1c` /
`6b6c628b70b7f65fd2bdb62e4fa60ba3cdd57df6292fa3709b916d410a4e1a87`.
f312 replayed to two launched rows with hashes
`6bb71c54385a9e475fdb0606839b6e9c9efd405103f2cacd6c6700251bf5765d` /
`26d488fa1d4703f42353da85d7560c1c71b828c44b7c5ff3768545f122bc48c1` /
`d6eab5ced0c360ab084ba863824c50ca26a9d90b65f9e1c5e262afb1f7b51e11`.
The resulting workload uses about 90% CPU, with enough headroom reserved for
the OS and later proof checking; no further checkpoint expansion is planned
before a child group closes.

v408 f312 child 0 also closed immediately with one attempt and no split,
leaving its sibling open.  While the original v402 final child continued its
serial chain, a later v409 snapshot caught a genuine two-leaf frontier at
maximum processed depth 19.  The source writer paused for 0.531 seconds.  The
proof-prefix/snapshot/frontier hashes are
`d68df5a8beb864d548dcdc9191e7296412d08f20fcd7989f325f123d2d99d719` /
`acd159068bb89a30b847f590effb9db67b38c4f02431e0b76a28eeded6baa623` /
`51218a7eb40b8ea6dd455ee0d650f24d180df75b1d63230a17cb5bb5ccefc6e6`.
Both rows received the 600-second/high-conflict strategy.  If both close,
v409 can replace v402 child 2 after exact standalone verification; otherwise
the original v402/v401/v400 races remain authoritative alternatives.

A later audit found that original v399 f31s1 child 1 had closed directly, so
the one-row v408 f311 recovery point is now redundant and remains unlaunched.
The still-relevant one-row v403 f10 and v407 f221 recovery points each
received the same distinct 600-second/high-conflict strategy used for v405;
this raised sustained CPU use to about 92% without creating another replay
layer.  v407 f220 child 0 subsequently closed after 21 attempts and 10
splits, advancing that two-row group to 1/2.  No complete checkpoint group is
promoted yet.

v409 strong child 0 closed directly in 498.702 seconds with one attempt and
no split.  Strong child 1 exhausted its first 600-second node, split on
variable -3751, and closed one side in 2.278 seconds; a standard 60-second
strategy race was therefore added for its sole remaining blocker.  Several
older four-hour ancestor races then exited on schedule, freeing enough CPU to
start nine high-budget alternatives on existing v403 f21, v404, v407 f220 /
f222, and v408 f312 rows.  These alternatives do not add replay depth and may
be substituted row-for-row only after `status=20`.

Original v404 child 0 and v406 f320 child 0 subsequently closed, advancing
both groups to 1/2.  The v404 high-budget child-0 race became strictly
redundant and was terminated; its 60 MB partial proof is retained.  The freed
core was reassigned to a high-budget race for v406 f320 child 1.  At this
checkpoint v409, v407 f220, v408 f312, v404, and v406 f320 are each one leaf
short of a complete finalizer input.

The finalizer now supports the recursive promotion needed after those groups
close.  Each ordered `--child PROOF EVIDENCE` pair may use either the original
producer log or a lower `ramsey55.cadical-dfs-checkpoint-finalization.v1`
manifest.  For the latter, the tool requires `checker_verified=true`, a
certified no-empty output fragment, a standalone proof carrying the appended
empty-clause marker, complete hash records for the lower checker inputs, and
an exact SHA-256/size match between the supplied proof and the lower output.
It then scans the supplied binary DRAT fragment again and runs a fresh
standalone `drat-trim` over the entire upper composition.  Thus a lower
manifest is only ordered provenance; the upper checker remains the soundness
gate.  Tests cover successful recursive composition, proof-hash mismatch,
and an unverified lower manifest.  A real-checker integration test uses an
inconsistent two-unit CNF and empty no-final-clause fragments: the lower and
then upper standalone compositions both pass genuine ARM `drat-trim`.
All seven focused tests pass on ARM.  The full local suite passes 201 tests,
with only this test skipped because the local checker binary is not built.

Seven cores later freed by expired ancestor races were assigned to a third
search strategy on the existing one-leaf blockers.  These producers retain
the standard 500,000/1,000,000 conflict and 60-second solve budgets but set
`maximum_primary_split_variable=990`.  If CaDiCaL lookahead proposes an
auxiliary variable, the runner therefore falls back to the highest-occurrence
unused graph-edge variable.  The first rows split only on variables 893,
654, or 668, confirming the cap.  One primary-only race covers each of v409,
v406 f320, v407 f220, v408 f312, and v404; two cover v403 f21.  This fills all
64 solver slots at about 94% CPU without adding proof-replay depth.  Any such
fragment is interchangeable with its exact same-row standard/high-budget
competitors only after `status=20` and the normal finalizer gate.

The six old `order45-strata/checkpoint-compose-d20-legacy-20260815` solver
processes were audited before further allocation.  They are already in the
kernel `T` state, use no CPU, and their proof files have not changed since
August 15; no process or artifact was deleted.  Five of those available
logical-core slots were then assigned to primary-only alternatives for both
v406 f321 rows and all three v406 f331 rows.  Together with the earlier
alternatives, the machine now runs 63 active proof producers while retaining
all six paused legacy recovery processes.  CPU is saturated, so no further
search duplication is launched before a completion frees capacity.

None of these checkpoints proves strengthened parent 1, either fixed-pair
formula, the order-45 formula, or `R(5,5) <= 45`.
