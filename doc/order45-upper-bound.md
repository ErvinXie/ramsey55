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

None of these checkpoints proves strengthened parent 1, either fixed-pair
formula, the order-45 formula, or `R(5,5) <= 45`.
