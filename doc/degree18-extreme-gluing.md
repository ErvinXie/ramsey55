# Degree-18 extreme gluing experiment

Updated: 2026-08-12

## Mathematical reduction

Let (F) be a hypothetical Ramsey(5,5,43) graph and let (v) have degree
18. Write (A=F_v^+), and let (H) be the complement of (F_v^-). Then

- (A\in\mathcal R(4,5,18));
- (H\in\mathcal R(4,5,24));
- the complete public catalog for the H-side has 352,366 graphs.

The three-vertex subgraph identity used by Angeltveit and McKay is

\[
 \sum_v\left(e(F_v^-)-e(F_v^+)
 -\tfrac12d(v)(43-2d(v))\right)=0.
\]

For a degree-18 vertex its summand is

\[
 c(v)=213-e(A)-e(H).
\]

The exact bound (E(4,5,18)=85) implies that a degree-18 vertex with
nonpositive contribution must have (e(H)\ge128). The complete 24-point
catalog has the following upper tail:

| H edges | graphs |
|---:|---:|
| 128 | 843 |
| 129 | 147 |
| 130 | 32 |
| 131 | 3 |
| 132 | 2 |

Thus only 1,027 of the 352,366 H-side graphs can participate in this
critical degree-18 case. Moreover, nonpositive contribution requires
(e(A)\ge213-e(H)). For (e(H)=128), A must have exactly 85 edges, and the
official extreme catalog contains only 74 such isomorphism classes.

This does not by itself prove that a hypothetical 43-point graph has a
degree-18 vertex with nonpositive contribution. The global excess identity
only guarantees a nonpositive contribution somewhere, possibly at another
degree. The reduction is therefore one finite branch of a prospective global
argument, not an upper-bound proof.

## SAT formulations

`tools/generate_degree18_fixed_cnf.cpp` fixes H and leaves the 153 A-edges and
432 A--B edges free. It supports:

- lexicographic sorting of the 18 cross rows;
- the degree interval (18\le d(x)\le24);
- cross-first variable numbering for controlled cubing;
- the critical lower bound on `e(A)`, together with the known upper bound 85.

The sequential cardinality encoding is exhaustively tested on every primary
and auxiliary assignment for all instances of size at most four. Direct SAT,
Kissat/CaDiCaL portfolios, Satsuma fixing and march_cu all time out on the
representative generic instances. A graph-aware manual split is much better:
fixing four-bit prefixes in several cross rows closes orders of magnitude more
branches than fixing A-internal edges or completing one cross row.

`tools/generate_degree18_pair_cnf.cpp` then fixes both A and H. Only the 432
cross edges remain primary variables; degree counters are auxiliary. For the
pilot pair H catalog record 35 (128 edges) and A catalog record 0 (85 edges),
the original formula has 8,633 variables and 95,472 clauses, compared with
26,917 variables and 568,091 clauses in the one-sided critical formula.

### Fixed-side automorphisms

The original pair formula missed a legal symmetry reduction. Nauty and an
independent exhaustive backtracker agree that A record 0 has automorphism
group order 8, while H record 35 has trivial automorphism group. The generator
now enumerates and validates every fixed-side automorphism and appends a
lex-leader for each nonidentity A automorphism. A minimum member of every
orbit satisfies all of these inequalities, so the strengthening preserves
satisfiability.

The lex encoding and the automorphism enumerator have built-in exhaustive
self-tests: every variable permutation of length at most five is checked
against the semantic lexicographic relation, and every graph on at most five
vertices is checked against brute-force permutation enumeration. The old
formula is still reproducible byte for byte with `--no-symmetry`, with SHA-256

`f12d41fbb2550e2e494bd9fea161a1f7d283d5232d5e316e585dc5763bf87681`.

The strengthened formula has 10,162 variables and 104,646 clauses, with
SHA-256

`8a0fdd4ce464f1a3925668faafc47901317349700c7895224cdd84b7fcf024ae`.

Its first 95,472 clauses are exactly the old formula's clauses; the only
change is 1,529 new prefix variables and 9,174 appended clauses.
`tools/verify_cnf_strengthening.py` independently parses both DIMACS files and
records this exact-prefix relation in
`r48-symmetry-strengthening.json`. Consequently every leaf already proved
UNSAT under the old formula remains UNSAT under the strengthened formula, and
the existing cube frontier remains a cover after the transition.

## Adaptive cube-and-conquer pilot

Neither CaDiCaL nor Kissat closes the fixed pilot pair directly in 60 seconds.
However, CaDiCaL look-ahead at depth eight produces 256 cubes of which the
conquer step typically closes about 255 immediately. This exposes a narrow
near-model tree instead of a broad brute-force search.

`tools/run_adaptive_cube_tree.py` automates this process:

1. materialize each current parent cube as unit clauses;
2. generate 256 depth-eight look-ahead children;
3. solve the children in parallel with a strict per-cube limit;
4. atomically checkpoint only the UNKNOWN children;
5. stop immediately and preserve a model if any SAT candidate appears.

The driver is deterministic and resumable at round boundaries. Its current
results are computational search data, not yet proof certificates: UNSAT
statuses are trusted solver returns and no DRAT traces are retained. Once a
pair tree is completely closed, the same leaves must be rerun with proof
logging and independently checked before the result can enter the formal
trust boundary.

### Balanced conquer and independently checked covers

The first driver assigned one current parent to each worker group. At deeper
rounds, 43 of 44 parents could finish while one difficult parent continued on
a single core. `tools/run_global_adaptive_cube_round.py` removes that tail: it
generates every local depth-eight cover in parallel, independently checks each
cover, then sends all children through one global 64-worker conquer queue. A
14,848-child round that exposed the static tail completed in about one minute
with the global queue.

`tools/verify_cube_cover.py` checks that a local cube DNF covers every Boolean
assignment by deciding the complementary CNF with a small pure-Python DPLL.
The simpler pairwise cube reduction remains a useful fast path but is not
complete and is not used as the correctness criterion. The latest bulk audit
with `tools/verify_adaptive_cube_covers.py` checked 3,531 local covers and
903,936 emitted cubes; all passed, with 53,237 aggregate DPLL nodes. Its
manifest aggregate hash is
`b8cf529ea2a978341c15124cb7183a19e6a57989698e6483bc81d042a5c08ca1`.
The manifest file itself has SHA-256
`d6856e423425814b952df159b6efdb0aa6fc61eafad06ea6b483d0b84a4d9f6f`.

### Portfolio filters and selective primary splits

The look-ahead heuristic overwhelmingly branches on the sequential-counter
auxiliaries: the first 23 rounds assigned no cross-edge variable at all.
This is useful for narrowing degree states, but eventually leaves a CDCL tail.
The search therefore alternates:

1. complete depth-eight auxiliary covers;
2. CaDiCaL and Kissat runs whose `UNKNOWN` outcomes remain in the frontier;
3. complete four-bit splits on actual cross edges;
4. adoption only when a parent has zero or one surviving child.

`tools/adopt_cartesian_refinement.py` and
`tools/adopt_guided_refinement.py` verify every Cartesian group before an
atomic state update. Their selection and adoption manifests bind the exact
state, cube and result files by SHA-256. Unhelpful groups are discarded and
their original parent remains in the frontier, so exploratory branching never
weakens coverage.

CaDiCaL and Kissat are materially complementary. For example, at one deep
checkpoint Kissat's default configuration closed 94 of 212 cubes that had
survived CaDiCaL and Kissat's `--unsat` configuration. Default Kissat later
became ineffective, while `--unsat` continued to remove about 20--30 percent
of some newly exposed frontiers.

The old formula reached round 48 with 229 survivor contexts after two more
global depth-eight rounds and Kissat cleanup. Switching to the strengthened
formula directly closed no current context, because most cubes fixed only
sequential-counter auxiliaries. A global round did close 23 whole parents in
the cubing phase, but still grew the frontier. Explicitly branching on the
first compared bit of each of the three earliest row pairs was much more
effective. The pairs are

\[
 (x_1,x_{265}),\qquad (x_{25},x_{97}),\qquad (x_{145},x_{169}).
\]

Complete six-variable Cartesian covers were then advanced column by column.
The adoption tools retain a split only under a declared survivor threshold,
verify every one of its 64 children in the expected order, reject any SAT
result, and bind state, cubes, selections and results by SHA-256. In the
processed strata, later columns were extremely strong: representative fourth
and sixth-column batches closed 448/448 and 4,288/4,288 children, while a
large fifth-column batch closed 12,925/12,992 before its 67 survivors were all
closed at the sixth column. This closed all contexts that had reached the
sixth comparison column in those strata.

The explicit-column pass closed all 102 contexts that had 12 assigned cross
edges at round 68. They were processed in survivor-count strata, projecting
previously computed results whenever the complete cube tuple matched. The
three contexts with 20 assigned cross edges were also closed by complete
guided splits. This left the round-102 checkpoint with 1,345,640 closed
children and frontier distribution `{0: 144, 4: 12, 8: 65}`.

The same six-column pipeline has since been applied to 43 of the 65 contexts
with eight assigned cross edges. Later columns again supply most of the
propagation. At the round-121 intermediate checkpoint the frontier was
`{0: 144, 4: 12, 8: 22, 18: 78}`. Successive third-, fourth-, fifth- and
sixth-column strata reduced those 78 contexts to 11 unresolved contexts, with
no SAT candidate.

The last 11 contexts in that stratum were then closed: their fourth-column
run returned 10,460 UNSAT and 356 UNKNOWN children, and all 11,392 children
of the complete fifth-column refinements were UNSAT. This produced the
round-134 checkpoint `{0: 144, 4: 12, 8: 22}`.

The remaining 22 eight-primary contexts have now all entered the column
pipeline. Exact projection of their earlier first-column results yielded 410
UNSAT and 294 UNKNOWN children. The second-column solve returned 7,480 UNSAT
and 1,928 UNKNOWN children. Successive survivor-count strata have since been
advanced through the third, fourth and occasionally fifth columns. Four
representative fourth-column runs returned 3,328/3,328, 15,806/15,808,
7,647/7,648 and 11,518/11,520 UNSAT children. The isolated UNKNOWN children
omitted by terminal progress samples were retained from the complete TSV and
closed at the following column. No SAT candidate appeared.

Further survivor-count strata advanced the remaining third-column contexts
through complete fourth- and fifth-column splits. For the strata with 21--30
third-column survivors, representative fourth-column runs closed
10,923/10,976, 9,772/9,792, 6,466/6,528, 8,861/8,864 and 8,544/8,640
children. Every UNKNOWN child retained from those runs was carried into a
complete fifth-column split; the corresponding batches closed 1,696/1,696,
640/640, 1,984/1,984, 96/96 and 3,072/3,072 children. No SAT candidate
appeared.

The current stable checkpoint is round 185, with 1,690,883 computationally
closed children and 256 frontier contexts. The state SHA-256 is

`b50748229e415eec7055caf4a4946101df887cb315cd5c042da80fb077fbd66a`.

The remaining frontier has 144 contexts with no assigned cross edge, 12 with
4, 68 with 13, and 32 with 18. The next fourth-column batch, for the 14
parents having 31 third-column survivors, has finished but has not yet been
adopted into the stable state. Its 13,888 ordered rows contain 13,847 UNSAT,
41 UNKNOWN and no SAT result; the 434 complete parent groups have UNKNOWN
counts `{0:409, 1:14, 2:8, 3:2, 5:1}`. Those 41 UNKNOWN children should next
be refined at the fifth column. Terminal progress logs are only samples;
adoption always reads the complete ordered TSV, which is why isolated
UNKNOWN rows are preserved even when the displayed tail contains only
UNSAT statuses. The round-68 bulk audit inspected
4,088 adaptive files. All 4,065 nonempty local
covers passed the complete DPLL checker, comprising 1,040,640 emitted cubes
and 61,247 DPLL nodes. The other 23 files are the round-48 parents closed
directly by the cuber; they have empty cube lists, `status=20`, `cubes=0`, and
header-only result tables, and are explicitly classified as trusted solver
UNSAT rather than Boolean covers. The audit aggregate hash is

`2ec4a6aa687ad8160641a04928ff9a2af66e95474a7c6174b0161f869c4530eb`,

and the manifest file SHA-256 is

`3beb51aee1e1ec74e71ccfd27ecd0be7381359dab7419438412c6b9f8a4a03b8`.

Every adopted Cartesian cover additionally has its own hash-bound manifest.

All solver UNSAT statuses in this adaptive experiment, including the 23
cuber-UNSAT parents, remain computational search data rather than final
certificates. The fixed pair is not closed, no DRAT/LRAT proof replay has yet
been performed for these leaves, and this work covers only one `(H,A)` pair
rather than all 62,382 H128/A85 pairs. It is not a statement about the value
of `R(5,5)`.

## Reproduction

On the ARM compute node:

    build/generate_degree18_pair_cnf \
      data/reference/r45_24.g6 35 \
      data/reference/r4518.85.g6 0 build/pair-35-0-sym.cnf

    PYTHONPATH=src python3 tools/verify_cnf_strengthening.py \
      build/pair-35-0.cnf build/pair-35-0-sym.cnf \
      build/adaptive-pair-35-0-v1/r48-symmetry-strengthening.json

    PYTHONPATH=src python3 tools/run_adaptive_cube_tree.py \
      build/pair-35-0-sym.cnf build/adaptive-pair-35-0-v1 \
      --cuber build/generate_cadical_cubes \
      --solver build/solve_cadical_cubes \
      --depth 8 --seconds 5 --jobs 64 --max-rounds 20

The fixed-pair branch remains in progress. Scaling the method to all 62,382
H128/A85 pairs will require a batch scheduler, early compatibility filters,
and proof-producing replay; the current experiment establishes the useful
decomposition, not that the whole extreme branch has been closed.
