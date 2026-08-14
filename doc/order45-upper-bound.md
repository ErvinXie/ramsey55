# Order-45 upper-bound program

Updated: 2026-08-14

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
complementation, and the relabelling equivalence. The complete 74-target Lean
project, including this new file, builds successfully with pinned Lean 4.31.0
on the ARM node.

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
