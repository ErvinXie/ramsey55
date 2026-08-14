# Nonseparable-identity experiment for order 43

Updated: 2026-08-11

## Question

McKay and Radziszowski's 1997 nonseparable subgraph-counting identity gives a
sum of local contributions over the vertices of a hypothetical Ramsey graph.
Engström later supplied a shorter proof of the identity. The experiment asked
whether, for ambient order 43, the local contribution could already be forced
to one sign using only the known \(R(4,5,d)\) edge ranges and small induced
subgraph constraints. Such a sign separation would be the kind of theoretical
compression needed before a finite upper-bound computation becomes viable.

Primary references are the
[1997 paper](https://users.cecs.anu.edu.au/~bdm/papers/r55.pdf) and
[Engström's proof](https://arxiv.org/abs/1002.4304).

## Exact scans of available graph data

`tools/r45_identity_scan.cpp` counts the relevant three- and four-vertex
induced types and evaluates the exact integer local functionals. It was
cross-checked on small examples against a separate Python brute-force
implementation.

The scanner processed the official edge-extremal \(R(4,5)\) archive and the
complete set of 352,366 \(R(4,5,24)\) graphs. These are exact evaluations on
the available records, not universal extrema for orders where the published
files contain only edge tails. The observed combined contribution intervals
were:

| split degree | observed interval |
|---:|---:|
| 18 | \([8380,46996]\) |
| 19 | \([-952,37470]\) |
| 20 | \([-10474,33406]\) |
| 21 | \([-17394,26342]\) |
| 22 | \([-24204,22532]\) |
| 23 | \([-29862,19674]\) |
| 24 | \([-39708,16868]\) |

The degree-18 records happen to be positive, but the data are not a complete
\(R(4,5,18)\) census, so this is a clue rather than a theorem. Both signs are
already seen at every other degree.

For the public 43-vertex two-violation colouring, exact per-vertex values are
strongly degree-correlated: all degree-20 vertices are positive, degree-21
vertices are negative, degree-22 vertices are still more negative, and the
total is zero as required by the identity.

## Rigorous small-local relaxation

`tools/local_identity_bounds.py` enumerates all labelled Ramsey-compatible
graphs on five or six vertices. For each possible larger-graph edge count it
takes the exact convex envelope of the local functional subject to:

- the full distribution of induced \(q\)-vertex Ramsey-compatible types;
- the correct mean number of edges in such a \(q\)-set;
- the published edge range for the larger \(R(4,5,d)\) graph.

This is a rigorous necessary-condition relaxation: every real local graph
obeys its bounds, although points in the relaxation need not extend to a real
larger graph. At \(q=6\), the combined intervals are:

| degree | rigorous relaxed interval |
|---:|---:|
| 18 | \([-115128,920988/5]\) |
| 19 | \([-2879268/25,26205413/140]\) |
| 20 | \([-581908/5,2764738/15]\) |
| 21 | \([-583848/5,936624/5]\) |
| 22 | \([-578036/5,193376]\) |
| 23 | \([-1825922/15,30404587/150]\) |
| 24 | \([-623728/5,5416776/25]\) |

Every interval crosses zero by a wide margin. Moving from five to six local
vertices improves some bounds slightly but does not approach sign separation.

## Conclusion

The nonseparable identity remains structurally informative, but the identity
plus edge counts and all induced constraints through order six cannot prove
the 43-vertex upper bound. Continuing the same relaxation one vertex at a time
has no convincing near-term path to closure.

A useful continuation would need genuinely global consistency between
overlapping neighborhoods, a much stronger exact optimization over whole
\(R(4,5,d)\) graphs, or a new identity. This negative result prevents us from
mistaking a weak local LP for a promising proof route and redirects effort to
classification-compressing or overlap-aware constraints.
