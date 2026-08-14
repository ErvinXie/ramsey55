# The K43 two-violation landscape

Updated: 2026-08-11

## Scope

This note records exact finite computations around the public 43-vertex
colouring with two monochromatic \(K_5\)'s. “Exact” here means that the stated
connected components were exhaustively traversed by the incremental program
and cross-checked from emitted graph6 records. It does **not** mean that all
43-vertex colourings, or all two-violation colourings, have been classified.

The input is
[k43_near_miss_1.matrix](../data/reference/k43_near_miss_1.matrix). Its two
bad sets are

\[
\{0,2,28,29,38\},\qquad \{0,11,28,29,38\}.
\]

They are both all-zero \(K_5\)'s and share the four-point core
\(\{0,28,29,38\}\).

## Flip objective

For a colouring \(G\), let

\[
M(G)=\#K_5(G)+\#K_5(\overline G).
\]

The program [local_search.cpp](../tools/local_search.cpp) maintains \(M\) and
the exact change \(\Delta_e=M(G\triangle e)-M(G)\) for all 903 edges. Flipping
an edge only affects the \(\binom{41}{3}=10{,}660\) five-sets containing it.
Counts and all affected deltas are updated incrementally.

For the input graph, the two best flips are \((0,28)\) and \((29,38)\), both
with \(\Delta=0\). The flip \((0,28)\) produces the second graph published in
the source gist: its two all-one bad sets are

\[
\{0,15,22,28,39\},\qquad \{0,15,24,28,39\}.
\]

## The initial plateau is C86

Starting at the input graph, traverse every single-edge move with
\(\Delta=0\), retaining only states with \(M=2\). The complete connected
component has:

- 86 labelled states;
- exactly two zero-delta exits at every state;
- minimum available single-flip delta 0 at every state;
- two same-colour bad \(K_5\)'s intersecting in exactly four vertices at every
  state;
- 43 states with two all-zero bad sets and 43 with two all-one bad sets.

Since the component is connected and every state has degree two, its state
graph is the cycle \(C_{86}\).

The 86 state transitions use 43 underlying edges of \(K_{43}\). Each edge
labels two undirected state transitions, and the 43 label edges form this
Hamilton cycle on the original vertices:

    0 11 4 17 15 39 32 18 22 16 14 5 13 1 30 40 35 25 8 23 2 38
    29 27 34 12 19 9 42 6 20 10 37 26 31 36 3 21 7 24 33 41 28

The final vertex 28 reconnects to 0.

Thus the local obstruction has a concise interpretation: the two
monochromatic defects propagate around a 43-cycle, alternating colour, without
ever disappearing.

## Isomorphism reduction

The 86 emitted graph6 records were independently rechecked with the Python
clique enumerator, then canonically labelled with nauty 2.9.3. They reduce to
exactly two graph-isomorphism types:

| type | occurrences | bad colour | automorphism group |
|---|---:|---|---:|
| A | 43 | all one | 2 |
| B | 43 | all zero | 2 |

The two types are not isomorphic and are not complements of each other. Up to
global colour complementation, their complements supply two additional
types.

Deleting a vertex kills both bad sets exactly when the vertex lies in their
four-point intersection. For the input graph, nauty canonicalization against
the 656-graph reference family gives:

| deleted vertex | 0-based representative index |
|---:|---:|
| 0 | 255 |
| 38 | 255 |
| 28 | 41 |
| 29 | 41 |

So the near miss has four genuine 42-point Ramsey deletions, comprising two
copies of each of two known isomorphism classes.

This deletion connection is now checked without trusting canonical labels:
the Python test suite contains an explicit 42-vertex permutation from the
vertex-0 deletion to representative 255 and checks all 861 pairs. Transporting
the deleted vertex's attachment through that permutation produces exactly two
violations. Independently, Lean cover trees prove that every attachment to
representative 255 produces at least two violations. Thus the lower bound is
sharp for that base graph.

## Other components reached

Tabu perturbations found four additional objective-2 components. Each was
exhaustively traversed and had the same signature:

- 86 states and state graph \(C_{86}\);
- bad-set intersection histogram \(4:86\);
- bad colours \(43\) all-zero, \(0\) mixed, \(43\) all-one;
- two zero-delta moves at every state;
- 43 transition labels, each appearing on two undirected state transitions;
- transition-label support degree two at all 43 original vertices.

Canonicalizing all \(5\times86=430\) states still gives only the same two
isomorphism types, each 215 times. The five components are therefore different
labelled embeddings in the flip hypercube, not five new unlabelled
colourings.

The search has not proved that these are the only objective-2 components.

## Research conjecture suggested by the data

A sharper intermediate target than merely \(R(5,5)\le43\) is:

> Every red-blue colouring of \(K_{43}\) has at least two monochromatic
> \(K_5\)'s; equality cases, up to graph isomorphism and global colour swap,
> are exactly the two observed types.

The first clause alone would prove \(R(5,5)=43\) together with the formal
42-point witness. The equality classification is optional but may make a
finite counting or SOS proof discoverable: the defect-cycle structure gives
concrete equality conditions against which candidate inequalities can be
tested.

At present this remains a conjecture for arbitrary 43-vertex colourings. Its
one-vertex version is now a theorem for each of the 656 public 42-vertex base
graphs: every attachment creates at least two violations. Extending that
statement to all bases still requires the unproved completeness of the public
42-vertex catalog, or a different global argument.

## Reproduction

Build and run the deterministic component enumeration:

    sh scripts/build_local_search.sh
    build/local_search data/reference/k43_near_miss_1.matrix \
      build/k43_search_best.matrix 0 1 20260811

Run the perturbation experiment that discovered five components:

    build/local_search data/reference/k43_near_miss_1.matrix \
      build/k43_search_best.matrix 200000 20 77420319

The nonzero process exit means that no zero-violation colouring was found; it
is expected for these recorded experiments.
