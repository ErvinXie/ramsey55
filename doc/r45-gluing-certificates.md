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
have 276 declared edge variables and between roughly 2,700 and 3,600 reduced
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

This does not by itself prove that those 179 and two isomorphism classes
exhaust all Ramsey graphs of the respective orders.  A clean upstream HOL4
tree pinned to commit `065c07054483e3132f12909103e6d0e35e912c28` is being
built on the ARM host to replay that enumeration boundary.  Until the global
cover theorem and its merge into the direct d08 fixed-star obligation are
checked, the repository does not claim the d08 theorem, `R(4,5) <= 25`, or
`R(5,5) <= 45`.
