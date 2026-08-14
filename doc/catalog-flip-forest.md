# Single-edge flip structure of the public 42-vertex catalog

Updated: 2026-08-11

## Result

Make a graph whose vertices are the 328 public \(R(5,5,42)\)
representatives. Join two vertices when toggling one base edge of one graph,
followed by a vertex relabeling and an optional global colour swap, gives the
other graph.

The exact quotient flip graph has 988 edges and six connected components:

| chosen root representative | component size |
|---:|---:|
| 0 | 48 |
| 23 | 96 |
| 25 | 128 |
| 39 | 12 |
| 172 | 40 |
| 190 | 4 |

There are no isolated public representatives. In particular, the two
extension-minimum-two types lie in the components rooted at 39 and 172:
representative 41 is in the 12-graph component, while representatives 255 and
256 are in the 40-graph component.

## Verifiable compression certificate

`data/reference/r55_42_flip_forest.json.gz` stores a spanning forest rather
than all 988 edges. It contains:

- the six root indices;
- 322 transitions, one for every nonroot representative;
- the toggled edge in the parent's labeling;
- whether a global colour complement is used;
- an explicit permutation of all 42 vertices mapping the toggled parent to
  the child or its complement.

The artifact additionally certifies closure under every safe single-edge
move. Among all 328×861 labelled toggles, exactly 2,040 remain Ramsey-free;
the file records an explicit catalog target and permutation for each one.
Consequently no single-edge move from a public graph produces a new catalog
type.

## Exact radius-two scan

`tools/catalog_two_flip_scan.cpp` checks all unordered pairs of the 861 edge
variables for every representative. It does not construct and rescan 121
million graphs. For each five-set, it records whether its ten-edge pattern is
at Hamming distance one or two from either monochromatic pattern:

- at distance one, a double flip is forbidden when it flips the unique
  mismatch and puts its other flip outside the five-set;
- at distance two, it is forbidden when it flips the two mismatches.

These are exactly all ways two toggles can create a new monochromatic
\(K_5\). The complete census is:

| quantity | value |
|---|---:|
| five-set/colour patterns at distance 1 | 3,940,161 |
| five-set/colour patterns at distance 2 | 19,436,558 |
| safe labelled single flips | 2,040 |
| safe labelled two-flip sets | 5,568 |
| safe two-flip sets with neither single flip safe | 0 |

Thus every safe double flip has a Ramsey-free single-flip intermediate. The
independently checked single-flip closure then implies that the intermediate
is in the catalog, and applying closure once more puts the double-flipped graph
back in the catalog. No graph at Hamming distance at most two from the public
family escapes it.

## Exact radii three and four

The higher-radius search uses `tools/enumerate_minimal_flip_models.py` and a
fixed-cardinality SAT encoding. At each radius it blocks every safe proper
subset, so the remaining models are precisely the inclusion-minimal safe
moves that cannot already be reduced to a lower-radius result. After model
enumeration, `tools/verify_minimal_flip_models.py` blocks every listed model,
runs CaDiCaL on the residual formula, and checks the resulting DRAT proof with
drat-trim independently for each of the 328 representatives.

The radius-four census contains 160 labelled inclusion-minimal safe moves:

| models per representative | representatives |
|---:|---:|
| 0 | 208 |
| 1 | 80 |
| 2 | 40 |

Every one maps back into the public catalog. Their component-to-component
moves, using the roots above, are 48 from 0 to 25, 48 from 23 to 25, 32 from
25 to 0, and 32 from 25 to 23. No new catalog type occurs. The independently
checked residual UNSAT proofs establish that the 160-model list is complete.

`data/reference/r55_42_minimal_four_flips.json.gz` is the permanent compact
certificate. It stores every four-edge set, verifies that all of its proper
subsets are unsafe, and supplies an explicit 42-point permutation to its
catalog target. Its solver- and nauty-free verifier reports:

    verified 160 inclusion-minimal safe four-edge models, their proper \
      subsets, and all explicit catalog isomorphisms

Together with the lower-radius closure, this proves that no Ramsey-free graph
at Hamming distance at most four from the public family escapes the catalog.

The local single-flip criterion is exhaustively cross-checked against full
clique enumeration on all 861 flips of a representative. The two-flip scanner
is a compact C++ exhaustive computation, not yet a Lean theorem.

The compressed file is 60,880 bytes and has SHA-256
`86c047ac9e8b3efffa2da8704305bcd5395c49d3dc6acbf118e9170b996c4625`.

Nauty is used only while discovering which catalog entry a flip reaches. The
committed certificate does not ask a verifier to trust a canonical label or
an isomorphism program: `tools/verify_catalog_flip_certificate.py` checks that
each stored map is a permutation, compares all graph pairs under it, locally
recomputes exactly which of all 282,408 flips remain Ramsey-free, checks that
all 2,040 safe flips occur exactly once, checks the rooted-forest order, and
verifies that exactly all 328 indices are reached.

## Reproduction

With a local nauty `labelg` binary:

    PYTHONPATH=src python3 tools/generate_catalog_flip_certificate.py \
      --labelg /path/to/labelg
    PYTHONPATH=src python3 tools/verify_catalog_flip_certificate.py
    sh scripts/build_catalog_two_flip_scan.sh
    PYTHONPATH=src python3 tools/check_two_flip_candidates.py

Generation canonically labels the 656 graph/complement records and all
328×861 single-edge toggles, finds a spanning forest, derives explicit
isomorphisms by joint colour refinement with individualization, writes a
deterministic gzip file, and then invokes the independent permutation checker.

## What this does and does not prove

This gives a concise generative description of the known catalog: six seeds
plus 322 local moves reconstruct every representative up to the standard
equivalences. It also identifies a concrete local neighborhood around the two
near-miss equality types; for example, representative 256 is obtained from
255 by deleting one edge and relabeling, while the minimum apex defect count
jumps from two to four.

It does **not** prove that an unknown seventh component cannot exist. It proves
that any such component is at Hamming distance at least five from every
known graph. A full
classification still needs a theorem saying that every Ramsey-free
42-vertex graph belongs to the closure of the six seeds under certified moves,
or another exhaustive argument. The value of the forest is that it replaces
an unstructured list by a small, checkable target for such a closure theorem.
