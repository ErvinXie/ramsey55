# Extension multiplicity landscape of the public 42-vertex graphs

Updated: 2026-08-11

## Definition and trust level

For a fixed Ramsey-free graph \(G\) on 42 vertices and a new apex attachment
\(x\in\{0,1\}^{42}\), let

\[
m_G(x)=K_4(G[x^{-1}(1)])+
       K_4(\overline G[x^{-1}(0)]).
\]

This is exactly the number of monochromatic \(K_5\)s through the new apex.
The Lean theorem

    reference42TwoViolationCatalogWithComplements_all_atLeastTwo

proves \(m_G(x)\ge2\) for all attachments to all 656 public graphs.

The finer bounds in this note were obtained by the same deterministic
decision-tree search and independently checked in Python, but their trees are
not currently embedded in Lean. They are reproducible computational results,
not claims about an unknown 42-vertex graph outside the public catalog.

## Observed separation

For the 328 representatives:

| representative indices | exact minimum or checked lower bound |
|---|---:|
| 41, 255 | exactly 2 |
| 256 | exactly 4 |
| all other 325 representatives | at least 6 |

Therefore no public representative has minimum 1, 3, or 5. Colour
complementation preserves the minimum, so the same separation holds after
adding the other 328 catalog entries.

The lower witnesses are explicit regression data:

| representative | attachment bit mask | violation count |
|---:|---:|---:|
| 41 | 131467062783 | 2 |
| 255 | 6410183167 | 2 |
| 256 | 21409014271 | 4 |

The Python test suite recomputes the violation sets for these masks. The
“at least” directions come from exhaustive cover trees, not local search.

## Connection to the K43 near miss

The two public equality bases are not arbitrary. In the known 43-vertex
colouring with exactly two monochromatic \(K_5\)s, the two bad sets share four
vertices. Deleting any shared vertex leaves a 42-vertex Ramsey graph:

- deleting vertex 0 or 38 gives representative type 255;
- deleting vertex 28 or 29 gives representative type 41.

Thus the only public bases with extension minimum two are exactly the two
types exposed by deleting the common core of the near miss. For the vertex-0
deletion, the repository stores an explicit isomorphism and checks that
reattaching the deleted vertex recreates the two violations.

Representative 256 is the unique next layer currently observed, with exact
minimum four. Its simple invariants are close to the equality types rather
than obviously exceptional:

| representative | edges | degree histogram | graph/complement \(K_4\) counts |
|---:|---:|---|---:|
| 41 | 427 | 19:8, 20:17, 21:12, 22:5 | 1185 / 1133 |
| 255 | 428 | 19:9, 20:15, 21:11, 22:7 | 1200 / 1131 |
| 256 | 427 | 19:9, 20:16, 21:11, 22:6 | 1187 / 1141 |

Edge count and degree sequence alone therefore do not explain the sharp
separation.

There is, however, an exact edit relation at the boundary. Remove edge
\((34,38)\) from representative 255 and then apply the explicit permutation

    0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22
    24 25 26 27 28 29 30 31 32 34 35 23 36 37 38 33 39 40 41

to obtain representative 256. The test suite verifies all pairs. Thus one
base-edge deletion moves directly from extension minimum 2 to minimum 4.
This makes the 255/256 pair a particularly concrete laboratory for finding
which local obstruction doubles the unavoidable defect count.

The change can be seen clause by clause. Deleting \((34,38)\) destroys 13
red \(K_4\) constraints and creates 10 blue \(K_4\) constraints, all of the
latter containing both endpoints. The exact-two attachment with mask
6410183167 for representative 255 violates two old blue constraints. On the
edge-deleted graph, the same attachment additionally violates
\(\{10,12,34,38\}\) and \(\{12,19,34,38\}\), giving exactly four. Transporting
the mask through the displayed permutation yields the recorded exact-four
mask 21409014271 for representative 256.

## Reproduction

The complete lower-bound ladder through six can be rerun with:

    PYTHONPATH=src python3 tools/analyze_extension_multiplicity.py \
      --jobs 10 --maximum 6

To avoid regenerating already checked smaller trees, the two final stages used
during development were:

    PYTHONPATH=src python3 tools/analyze_extension_multiplicity.py \
      --jobs 10 --maximum 5
    PYTHONPATH=src python3 tools/analyze_extension_multiplicity.py \
      --jobs 10 --start-bound 6 --maximum 6

The second command is meaningful only together with the first: by itself it
does not certify the skipped lower bounds. On the project machine, the
bound-six stage took about two minutes using ten worker processes.

## Research implication

The equality problem is much thinner than the full extension problem. A
promising next target is a structural characterization of bases satisfying
\(\min_x m_G(x)=2\). If one could prove that every 42-vertex Ramsey graph with
minimum two belongs to types 41 or 255, the equality side of the 43-vertex
multiplicity conjecture would be sharply constrained even before a complete
42-vertex classification.

The unexplained gap from 2 directly to 4 and then at least 6 is particularly
suggestive, but it is currently an empirical/catalog-level fact rather than a
general parity theorem.
