# R(5,5) formal proof status

Updated: 2026-08-23

## Target theorem

The exact-value objective currently pursued is

\[
R(5,5)=43.
\]

In the repository's Lean definitions, the two required halves are:

1. <code>¬ ForcesMonochromatic5 42</code>;
2. <code>ForcesMonochromatic5 43</code>.

The first theorem is complete and kernel-checked. The second is not proved.
The repository now has checked nonextension proofs for all 656 public
42-vertex examples and a formal reduction exposing exactly what would turn
those certificates into the second theorem. The missing step is completeness,
so this repository does **not** yet claim the exact value of \(R(5,5)\).

## Completed formal result

[Definitions.lean](../formal/Ramsey55/Definitions.lean) defines a
two-colouring, the ten-edge monochromatic \(K_5\) predicate, the Ramsey-free
predicate, and the forcing statement.

[Checker.lean](../formal/Ramsey55/Checker.lean) implements an exhaustive
checker over the \(\binom n5\) increasing five-tuples and proves a generic
soundness theorem connecting the Boolean checker to the quantified
mathematical specification.

[LowerBound42.lean](../formal/Ramsey55/LowerBound42.lean) embeds one
42-vertex witness from McKay's public dataset. Fourteen certificate chunks
cover the possible first vertex in groups of three. Lean checks each chunk by
kernel reduction and derives:

    theorem not_forcesMonochromatic5_42 :
        ¬ ForcesMonochromatic5 42

On the current 10-core, 16 GB Apple Silicon machine, a clean certificate build
took about 57 seconds. Chunking reduced the peak memory enough to avoid the
severe paging caused by a monolithic check.

The <code>#print axioms</code> audit reports only Lean's standard
<code>propext</code>, <code>Classical.choice</code>, and
<code>Quot.sound</code>. In particular, it reports neither
<code>sorryAx</code> nor a <code>native_decide</code> result axiom. The witness
check therefore does not add the Lean compiler or an external graph program
to the trust boundary.

## Checked one-vertex nonextension results

[Extension.lean](../formal/Ramsey55/Extension.lean) defines a complete binary
decision-tree certificate over the 42 possible edge colours from a new apex.
At every leaf, the checker verifies a monochromatic old \(K_4\) whose four
apex edges have the same colour. This witnesses a monochromatic \(K_5\) for
every possible attachment.

The generic theorem `checkExtensionCover_sound` is proved independently of
the search procedure. Generated Lean data check all 328 McKay
representatives. A formal colour-duality theorem supplies the 328 complements,
yielding:

    theorem reference42CatalogWithComplements_all_noExtension :
      ∀ graph ∈ reference42CatalogWithComplements,
        HasNoRamseyFreeOneVertexExtension 42 graph.base

The corresponding catalog-length theorem checks 656 entries. Across the 328
explicit trees there are 47,387 branches and 47,715 leaves; the largest tree
has 429 nodes. The compressed reproducible artifact is 395,847 bytes with
SHA-256
`2a6fc3f56195ca962a14c2e15c56278043b222a2a8d568dad3024f6ab09a0e64`.

The aggregate theorem's axiom audit reports only `propext` and `Quot.sound`.
The full details and reproduction commands are in
[the extension-certificate note](extension-certificates.md).

A stronger certificate family checks

    reference42TwoViolationCatalogWithComplements_all_atLeastTwo

which proves that every apex attachment to every public graph creates at
least two distinct monochromatic \(K_5\)s. It contains 145,196 branches and
145,524 leaves and has its own generic Lean soundness theorem. Its axiom audit
again reports only `propext` and `Quot.sound`.

A further deterministic Python census found a sharp multiplicity
stratification: representatives 41 and 255 have exact extension minimum 2,
representative 256 has exact minimum 4, and the other 325 representatives
have checked lower bound 6. The bound-two layer is Lean-checked; the larger
trees for bounds four and six are currently reproducible computations rather
than embedded formal theorems. See the
[multiplicity landscape](extension-multiplicity-landscape.md).

The 328 representatives also admit a small checked generative description:
modulo colour swap, their single-edge flip graph has six components of sizes
128, 96, 48, 40, 12, and 4. A 60,880-byte certificate stores six roots, 322
forest toggles, all 2,040 labelled toggles that remain Ramsey-free, and full
isomorphism permutations. Its independent checker does not trust nauty. This
compresses the public catalog and proves closure under one edge toggle, but
does not prove that no disconnected seventh component exists; see the
[flip-forest note](catalog-flip-forest.md).

An exact two-edge scan found 5,568 safe labelled double flips. Every one has a
safe single-flip intermediate, so the certified one-edge closure returns it to
the catalog. Fixed-cardinality SAT searches then closed radii three and four;
the radius-four frontier consists of 160 inclusion-minimal labelled models,
all with explicit isomorphisms back into the catalog. All 328 residual UNSAT
formulas were checked with DRAT, and a solver-free verifier checks the compact
four-flip artifact. Hence an unknown 42-vertex Ramsey graph, if it exists, is
at Hamming distance at least five from every public graph. These higher-radius
results are checked computation rather than Lean theorems.

## Formal upper-bound reduction

[Reduction.lean](../formal/Ramsey55/Reduction.lean) connects the raw
certificate notion back to finite colourings. It proves:

    theorem forcesMonochromatic5_43_of_all_42_nonextendable
      (allNonextendable :
        ∀ base : Coloring 42,
          IsSimpleColoring base → IsRamseyFree55 base →
          HasNoRamseyFreeOneVertexExtension 42 (coloringToRaw base)) :
      ForcesMonochromatic5 43

[Target.lean](../formal/Ramsey55/Target.lean) combines that reduction with the
checked lower bound in `ramsey55_is_43_of_all_42_nonextendable`. Thus the
formal statement itself records the one remaining hypothesis instead of
treating catalog completeness as an informal assumption.

## Order-45 cube composition bridge

[CubeCover.lean](../formal/Ramsey55/CubeCover.lean) defines finite Boolean
assignments, signed CNF literals, clauses, formulas, cubes, exhaustive cube
families, formula-relative cube covers, and formula/cube unsatisfiability. It
proves the generic results used by the order-45 certificate pipeline:

    theorem satisfies_split_of_satisfies_cube ...
    theorem cnfCubeFamilyCoversFormula_split_head ...
    theorem cnfFormulaIsUnsat_of_relativeCubeCover ...
    theorem cnfFormulaIsUnsat_of_cubeCover ...

The first proves that replacing a parent cube by its two children obtained by
adding a literal and its negation preserves local coverage. The second lifts
that split through a cover relative to the mother formula. The relative
composition theorem proves that independently refuting every cube refutes the
mother CNF whenever every satisfying assignment lies in some cube. This is
strictly the right interface for the d20/d21/d22 edge-pair cubes: their
counter-value cases cover assignments satisfying the counter and bound
clauses, but are not claimed to be a DNF tautology on assignments that already
violate the formula. An unconditional DNF cover is proved to imply a relative
cover, preserving the original composition theorem. Both mother-formula
theorems have empty axiom audits; the split theorems use only Lean's standard
`propext`.

This is the formal composition interface, not yet the completed order-45
proof. Remaining formal work includes connecting the concrete DIMACS encoder
and its variable map to graph colourings and the abstract counter development,
and importing or checking the generated cube data and leaf UNSAT results.

[Order45Excess.lean](../formal/Ramsey55/Order45Excess.lean) now closes the
pure global part of the excess-witness reduction. It assigns an integral
score to every ordered three-label orbit, proves the one-edge/two-edge
`2 - 1 - 1 = 0` cancellation, commutes the three finite summation axes, and
derives that the sum of all vertex scores is exactly zero. Hence every
nonempty simple colouring has a nonpositive vertex. Under the checked
20--24 degree window, colour complementation preserves that score and
normalizes a Ramsey-free witness to degree 20, 21, or 22. The module now also
constructs the padded neighbourhood H graph and complemented-nonneighbour J
graph, proves both are simple, obtains their exact natural edge counts by the
handshake theorem, and proves the local score decomposes into those two
counts. Relabelling preserves the score and moves the witness to the fixed
apex convention. The end-to-end graph theorem therefore derives the concrete
226/222/220 dense branches with `ForcesRed4OrBlue5 25` as its sole external
mathematical input. The complete ARM build passes, and the new axiom
audits contain only `propext`, `Classical.choice`, and `Quot.sound`, with no
`sorryAx`.

The remaining graph-to-CNF bridge must identify these concrete H/J edge
counts with the primary-variable lists and generated counter outputs in the
three DIMACS mothers. Binding the exact published edge-range inputs and the
checked computational leaf refutations also remain separate obligations.

[Order45ExcessTarget.lean](../formal/Ramsey55/Order45ExcessTarget.lean)
composes this graph theorem with the certificate layer actually used by the
global search. `DenseExcessCnfComplete d t formula` is the exact remaining
graph-to-mother obligation for a fixed-apex colouring with concrete H/J
counts and density threshold. Refuting complete degree-20, degree-21, and
degree-22 mothers now yields `ForcesMonochromatic5 45`. The most concrete
form consumes the generated 28/36/45 typed DIMACS cube lists, the already
proved counter-tail inclusions, and one leaf-UNSAT fact per cube. Thus no
fixed-pair H100/J132 result is confused with a global structural cover. The
new factored concrete theorem uses
`CatalogBoundedDenseExcessCnfComplete`: the local-catalog bridge upgrades
these range-bounded encoder obligations to full mother completeness from the
single explicit `Order45ExcessCatalogRanges` proposition. This isolates the
five published order-20 through order-24 range theorems instead of burying
them in the encoder premise. All target theorems use only the same standard
axioms and no `sorryAx`.

[Order45LocalCatalog.lean](../formal/Ramsey55/Order45LocalCatalog.lean) now
checks the graph-theoretic side of the published edge-range inputs. It proves
generically that any injectively labelled neighbour set of a vertex in a
Ramsey-free colouring induces an `R(4,5)` graph. Applied to the fixed apex,
the neighbour block is an `R(4,5,d)` graph and, after colour complementation,
the nonneighbour block is an `R(4,5,44-d)` graph. `Ramsey45EdgeRange` is the
exact external classification theorem schema; assuming its two relevant
instances, Lean obtains bounded natural H/J edge counts.
`Order45LocalCatalogCountBinding` is now proved rather than assumed: generic
isolated-prefix/suffix lemmas preserve the degree sum, and fixed-star
pointwise equalities identify both padded catalog graphs with the H/J graphs
in the excess identity. Thus the upper bound on local excess counts requires
only the published edge-range inputs, not a separate count-binding premise.
The complete ARM build passes 85 jobs. Axiom audits again contain only
standard axioms and no `sorryAx`.

[Order45Primary.lean](../formal/Ramsey55/Order45Primary.lean) now connects the
graph-side H/J counts to the concrete DIMACS counter inputs. It defines the
generator-ordered strict-upper-triangle stream, proves the exact handshake
identity for its natural edge count, recursively verifies `orderedPairsFrom`,
and proves structurally that the 990 triangular DIMACS identifiers are
duplicate-free. It then constructs `order45GraphPrimaryAssignment` for every
45-vertex colouring and proves `RepresentsOrder45Primary` rather than taking
that representation as an external premise. The three representation-free
endpoint theorems prove input counts 190/276, 210/253, and 231/231 equal the
same `edgesH` and `edgesJ` used by the excess identity. The complete ARM build
passes 86 jobs; axiom audits contain only the standard axioms and no
`sorryAx`, `native_decide`, or generated native-decision axiom. The counter
extension is now constructed in `Order45CounterAssignment.lean`; proving the
common Ramsey, fixed-star, degree-window, and lex-leader mother prefix remains
open.

[Order45CubeCover.lean](../formal/Ramsey55/Order45CubeCover.lean) now checks
the arithmetic and ordering of the concrete edge-pair layer. It defines the
same lexicographically ordered, threshold-filtered closed-range product as the
generator and proves membership is equivalent to the H/J range bounds plus
the excess threshold. Kernel computation gives the exact three lengths:

    theorem order45EdgePairCounts :
      order45Degree20EdgePairs.length = 28 ∧
      order45Degree21EdgePairs.length = 36 ∧
      order45Degree22EdgePairs.length = 45

The file also defines the generator's four-literal exact-count cube
`H≥h, ¬(H≥h+1), J≥j, ¬(J≥j+1)`. Assuming observable counter outputs have
their stated at-least semantics, it proves that every allowed dense edge pair
satisfies a member of the corresponding concrete cube list. Thus the formal
gap at this layer is no longer vague. The count theorem has an empty axiom
audit; the quantified coverage results contain only Lean's standard axioms
and no `sorry` or `native_decide`.

[CnfCardinality.lean](../formal/Ramsey55/CnfCardinality.lean) now discharges
both directions of the generic sequential-counter obligation. It proves
directly from CNF semantics that the generator's initial, first-column,
diagonal, and interior clause groups encode respectively `current ↔ item`,
`current ↔ old ∨ item`, `current ↔ diagonal ∧ item`, and
`current ↔ old ∨ (diagonal ∧ item)`. A finite row/width induction proves that
every satisfying state cell means “at least column+1 true inputs,” and
packages the last row as `ExactAtLeastCounterOutputs`.

The file now also constructs the complete truncated counter clause stream in
the generator's exact row-major cell and clause order. A subformula theorem
proves that any satisfying mother assignment satisfies every counter cell when
that stream is contained in the mother CNF. This removes the previous bundle
of per-cell semantic hypotheses from the data boundary; the theorem has no
`sorryAx` or `native_decide` dependency.

The emitted constraint tail is formal too. Two unit clauses around one counter
are proved to impose its inclusive range. The generator's threshold clauses,
including the cases where an out-of-width literal is omitted, are proved to
force the sum of the two exact counts above the requested threshold. Combining
the four units and all sum clauses yields the full H/J range-and-density tuple
used by each order-45 cover theorem.

The converse is now proved as well. Assigning each valid state cell its
intended prefix-threshold truth value satisfies the exact row-major cell
stream; counts inside the stated ranges satisfy the four units; and the dense
sum inequality satisfies every truncated sum clause. The combined theorem
`satisfiesSequentialCounterPairEncoding_of_exact` packages both counter
streams and their whole constraint suffix. Therefore no further Boolean
counter mathematics is needed for mother completeness.

[Order45CounterAssignment.lean](../formal/Ramsey55/Order45CounterAssignment.lean)
closes the corresponding concrete assignment step. It defines the valid
row-major cell coordinates, proves their numeric DIMACS identifiers are
duplicate-free, proves the H and J state intervals are disjoint, and overlays
their intended prefix-threshold values on the canonical graph-primary
assignment. The overlay is proved to preserve every graph input below the
counter base. Its three concrete endpoint theorems construct assignments that
satisfy the complete d20/d21/d22 counter tails from the exact local counts,
range bounds, and dense-excess inequalities. Thus all H/J counter variables,
cell clauses, range units, and sum clauses are now covered constructively.
The assignment is also proved to retain `RepresentsOrder45Primary`, so it can
be reused for clauses earlier in the mother stream. The new axiom audits
contain only the standard axioms.

[Order45MotherPrefix.lean](../formal/Ramsey55/Order45MotherPrefix.lean) proves
the primary-only prefix semantics without materializing millions of clauses
inside Lean. It defines the exact ten-literal order used for every increasing
five-set and proves both signs satisfied by any `IsRamseyFree55` colouring
under a representing assignment. A per-clause shape predicate is the explicit
data boundary for the 2,443,518-clause Ramsey stream. The same file defines
the exact fixed-star unit and proves all 44 units from `HasFixedStar`. The
complete ARM build passes 88 jobs; all new audits contain only `propext`,
`Classical.choice`, and `Quot.sound`, with no `sorryAx` or native-decision
axiom.

[Order45DegreeWindowAssignment.lean](../formal/Ramsey55/Order45DegreeWindowAssignment.lean)
closes the next constructive layer. It proves that the generator's 44
incident inputs for each vertex, in increasing-label order with the diagonal
omitted, have truth count exactly equal to the graph degree. It then constructs
all 44 width-25 sequential-counter tables. Their 800 variables per vertex are
proved duplicate-free and pairwise disjoint, and occupy exactly identifiers
991 through 36190. The resulting overlay preserves all graph primaries and
satisfies every row-major counter clause plus the two `[20,24]` range units
for every vertex, assuming the already isolated `ForcesRed4OrBlue5 25`
graph-theoretic input.

The same file composes this global degree assignment with each concrete H/J
assignment without overwriting the earlier interval. For d20/d21/d22 it now
constructs one assignment satisfying the Ramsey-clause shape interface,
fixed-star units, all 44 degree encodings, and the complete H/J counter tail
from the corresponding exact local counts, catalog bounds, and dense-excess
inequality. `order45Degree20/21/22NonLexMotherFormula_satisfied` records the
exact retained order after deleting only the cross-row lex block. This is a
conditional satisfiability/completeness bridge, not an UNSAT result. The full
89-job ARM build succeeds; its log SHA-256 is
`6910fd89e57a34a301ecd71f9caaaa7236381f7dd3920656a1be24202765df4b`.
Every added axiom audit contains only `propext`, `Classical.choice`, and
`Quot.sound`; no `sorryAx` or native-decision axiom appears. Remaining mother
work is the concrete lex-leader assignment/encoding bridge and exact generated
DIMACS stream shape/inclusion. The external `R(4,5)=25` import, five catalog
edge-range inputs, and every computational leaf UNSAT certificate also remain
explicit obligations.

[CnfLex.lean](../formal/Ramsey55/CnfLex.lean) and
[Order45LexAssignment.lean](../formal/Ramsey55/Order45LexAssignment.lean) now
formalize the generator's cross-row lex block itself. The generic file proves
the four-clause first-prefix and five-clause later-prefix definitions, the
guarded order clause at every column, and constructive satisfaction from exact
prefix-equality states plus Boolean lex order. The order-45 file allocates the
states in the exact generator interval beginning at 36191. Kernel arithmetic
checks 437/440/441 states ending at 36627/36630/36631 and exact clause counts
2622/2640/2646 for d20/d21/d22. The overlay is duplicate-free, preserves every
primary and degree-counter cell, and satisfies both the complete degree-window
formula and lex formula whenever the concrete cross rows are sorted. The full
91-job ARM build log has SHA-256
`56ea53bcee64b56da08aabf9a3c78c774800af7c6d7046f1467697b3f263df97`;
all new audits contain only the standard Lean axioms. The remaining lex
assignment layer then overlays the actual H/J tables without overwriting the
degree or lex intervals. For each of d20/d21/d22, one concrete assignment now
satisfies the Ramsey-shape interface, fixed star, all degree windows, the lex
block, and the complete H/J tail whenever the rows are sorted.

[Order45LexRelabeling.lean](../formal/Ramsey55/Order45LexRelabeling.lean)
discharges that sorting premise constructively. It embeds every cross row as
a fixed-length 0/1 key, merge-sorts the neighbour indices, and extends the
result to a proved permutation of all 45 vertices that fixes vertex zero and
the complete nonneighbour block. The relabeling is proved to preserve
simplicity, Ramsey-freeness, fixed-star structure, both local H/J counts, and
the excess witness. The resulting d20/d21/d22 assignments automatically meet
the exact adjacent-row lex predicate. Consequently
`order45Degree20/21/22FullMotherFormula_complete` prove the three concrete
`CatalogBoundedDenseExcessCnfComplete` obligations from only the already
isolated Ramsey/fixed prefix-shape interfaces and `ForcesRed4OrBlue5 25`.
The full 92-job ARM build log has SHA-256
`70c94b5697a895c9960598daf98916db43435fd3baf7f1233cdcdd3585f0b120`;
the new axiom audits contain only `propext`, `Classical.choice`, and
`Quot.sound`, with no `sorryAx` or native-decision axiom.

Thus graph-to-mother completeness is no longer an open mathematical bridge
for the typed formula. The remaining data boundary is to bind the exact
generated DIMACS Ramsey/fixed streams and complete block concatenation to
these typed formulas. The external `R(4,5)=25` theorem, five catalog edge
ranges, and all 109 leaf UNSAT certificates also remain explicit inputs.

The order-45 file instantiates this theorem at the actual H/J row counts and
counter widths: `(190,101)/(276,133)`, `(210,108)/(253,123)`, and
`(231,115)/(231,115)`. It now derives three formula-relative cube covers from
mother-CNF satisfaction and inclusion of the two row-major counter substreams
plus the generated constraint tail. No separate semantic range or density
hypothesis remains. At the data boundary, the generated mother formula must
still be shown to contain that concrete typed suffix. The state-variable
assignment and its numeric DIMACS allocation are no longer open.

[Order45Dimacs.lean](../formal/Ramsey55/Order45Dimacs.lean) fixes the numeric
counter-variable allocation used by the DIMACS generator. It defines the
row-major cell offset from the lex-clause base and produces all three signed
four-literal cube lists from the formal edge-pair lists. Kernel checks confirm
the 28/36/45 lengths, all six manifest endpoint cubes, and that the final J
outputs are exactly variables 78697, 77148, and 76651—the three mother-formula
variable maxima. The formal DIMACS embedding reserves index zero as an unused
dummy so one-based identifiers remain visible verbatim. Lean reconstructs the
six H/J input lists in the same combinations order, checks their
190/276/210/253/231/231 lengths and boundary identifiers, and defines every
state cell from the row-major allocation.

The file now constructs the complete typed counter suffix for each degree:
H stream, J stream, four range units, and all sum clauses. It proves each
suffix covers its exact typed cube family, proves all 109 typed cubes map back
to the committed signed DIMACS integer lists, and lifts each suffix cover to
any mother CNF containing it. The full 79-target ARM build succeeds; the new
theorems contain only Lean's standard axioms and no `sorryAx` or
`native_decide`.

This closes the abstract input/state/bound/sum semantics. Still missing at the
data boundary is a kernel-checked or equivalently audited statement that the
three generated mother DIMACS streams contain these exact suffixes. The
independent byte-level statement is now recorded in
`data/order45-counter-tail-manifest.json`: a second audit reconstructs and
compares clauses 2,584,036/2,584,054/2,584,060 onward and binds the three
167,810/161,604/159,612-clause suffixes by SHA-256. This is equivalently
audited external data, not yet an embedded Lean theorem. Graph/excess reduction
and checked UNSAT-certificate import remain separate obligations.

[Order45Target.lean](../formal/Ramsey55/Order45Target.lean) now packages the
end-to-end upper-bound interface.  `FixedStarCnfComplete d formula` states the
exact graph-to-CNF obligation: every simple Ramsey-free order-45 colouring in
fixed-star branch `d` extends to a satisfying assignment of that formula.
Lean proves that completeness plus formula UNSAT excludes the branch, and
then combines the degree-20 and degree-22 exclusions with
`order45_fixedStar_normalize_of_r45`:

    theorem forcesMonochromatic5_45_of_fixedStarCnf ...
    theorem forcesMonochromatic5_45_of_fixedStarCubeRefutations ...

For the actual catalog/fixed-pair decomposition, the file also defines
`FixedStarCnfFamilyComplete`: every fixed-star Ramsey-free colouring must
satisfy at least one member of a finite reduced-CNF family, rather than one
particular symmetry-reduced formula. Lean then proves:

    theorem forcesMonochromatic5_45_of_fixedStarCnfFamilies ...
    theorem forcesMonochromatic5_45_of_fixedStarFamilyCubeRefutations ...

The latter permits a separate formula-relative cube cover and leaf-refutation
family for every reduced CNF. This is the certificate interface matching the
current fixed-pair computation; it avoids requiring every labelled colouring
to satisfy one chosen lex/fixed-pair formula.

The single-formula cube form takes a formula-relative cube cover and an UNSAT
fact for every covered leaf, deriving the mother-formula refutation through
the existing generic composition theorem. The complete ARM root build passes
all 82 jobs.
The new axiom audits contain only Lean's standard `propext`,
`Classical.choice`, and `Quot.sound`, with no `sorryAx`.  This theorem is a
precise contract, not a discharged upper bound: the external `R(4,5)=25`
input, concrete graph-to-DIMACS completeness, and checked leaf UNSAT data are
still explicit hypotheses.

The published HOL4 source for the first input is pinned independently.  The
upstream repository is fixed at commit
`065c07054483e3132f12909103e6d0e35e912c28` (2025-05-16), with its HOL4
submodule fixed at `cf03ce2dc756feb6c0bc4b042f879595d21f2e68` and Poly/ML
fixed at tag commit `4557554077078decce4ce5f90da00a713cfc32e4`. Its final
`src/mergef/r45_equals_25Script.sml` blob is
`5e211cf623ee268c0404fc70852b33cdc8307ff0`; it combines the kernel-checked
degree-8/10/12 exclusions and the order-24 witness into the theorem
`r45_equals_25`. The generic reduction source
`src/basicRamsey/basicRamseyScript.sml` is blob
`69b249e6a1fd59e5a77f4b4a710807f98331540d` and explicitly derives
`RAMSEY 4 5 25` before the exact-value statement.

A clean source replay is now active on `sglang-arm-builder`, rather than
merely inspecting those files.  The old bundled MiniSat 1.14p initially
misclassified formulas containing root-level unit clauses because AArch64's
default unsigned `char` cannot represent the solver's stored `-1` Boolean.
An exact-commit `-fsigned-char` build now passes both its internal resolution
traversal and HOL4 kernel proof replay on the retained regression.  Its build
and replay tools, narrow claim boundary, and exact hashes are recorded in the
[upstream HOL4 replay note](r45-upstream-hol-replay.md).  In particular, the
currently running enumeration still uses the deliberately non-executable old
binary and therefore the uniform internal proof-producing DPLL path.  Before
this solver diagnosis, the pinned HOL4 system built successfully, followed by
`src/def` and `src/basicRamsey`.  The checked conditional theorem
`ramsey_4_5_25_hyp` has precisely the three
degree-8/10/12 gluing obligations plus the order-24 witness as hypotheses.
The separate `r4524existTheory` witness stage has also replayed successfully;
it remains logically distinct from the unfinished upper-bound enumeration and
gluing stages.

The global generalized-graph enumeration is the current long-running stage.
Exactly 1,239 generated `R(4,4,k)` theory scripts for `k=8..17` are being
checked incrementally.  A 12-worker trial was rolled back at a clean boundary
after aggregate worker RSS reached 124.9 GiB and available memory fell to
27 GiB without swap; 106 completed theories were retained, and the active
safe setting is eight workers.  The subsequent `enumf` merge has not yet run.
The upstream reproduction guide used 40 cores and about 500 GB RAM for this stage,
so the 244 GiB ARM host trades wall time for a safe memory margin.  This is
therefore a partial replay checkpoint, not a new `R(4,5)=25` result and not an
import into the Lean kernel.

There is now a second, self-contained route to the same input in
[Ramsey45Target.lean](../formal/Ramsey55/Ramsey45Target.lean). Lean proves
that injective relabeling preserves `IsRamsey45Coloring`, that every simple
25-vertex graph has degree in `0..24`, and that excluding the 25 fixed-star
degree branches implies `ForcesRed4OrBlue5 25`. It also defines the exact
65,780-clause direct formula (negative six-edge clauses for every four-set,
then positive ten-edge clauses for every five-set), appends the 24 fixed-star
units, constructs the graph assignment, and proves every one of the 25 exact
65,804-clause formulas complete for its branch. Consequently

    forcesRed4OrBlue5_of_exactFixedStarUnsat

has only the 25 formula-UNSAT facts as hypotheses. Its axiom audit contains
only `propext`, `Classical.choice`, and `Quot.sound`, with no `sorryAx` or
native decision. `VerifyRamsey45ExactBranches.lean` converted all typed
literals back to signed DIMACS and compared every line of all 25 generated
files on ARM in 9.54 seconds with 535,764 KiB peak RSS. The log SHA-256 is
`5ba01356fc090a96e9401224527711e41842e9648b6ade40c61cd36fc820fba5`.
The separate Python reconstruction also passed. This removes branch coverage
and encoding semantics from the external `R(4,5)=25` trust boundary; the 25
UNSAT certificates themselves remain open.

The classical smaller-Ramsey reduction is now checked as well. From
`ForcesRed3OrBlue5 14`, a vertex neighbourhood has size at most 13; from
`ForcesRed4OrBlue4 18`, its nonneighbourhood bound gives degree at least 7.
The handshake lemma on 25 vertices then supplies an even-degree vertex, so
only degrees 8, 10, and 12 remain after fixed-star relabeling. The theorem

    forcesRed4OrBlue5_of_threeExactFixedStarUnsat

therefore derives `ForcesRed4OrBlue5 25` from the two smaller Ramsey inputs
and UNSAT of those three exact typed formulas. This is the same three-degree
shape used by the published HOL4 gluing proof, now connected directly to the
repository DIMACS definitions.

The two smaller inputs are now discharged from one much smaller certificate.
[RamseySmallBounds.lean](../formal/Ramsey55/RamseySmallBounds.lean) proves the
classical recurrences

    R(3,4) <= 9  ->  R(3,5) <= 14
    R(3,4) <= 9  ->  R(4,4) <= 18

by fixed-star relabeling, neighbourhood induction, and colour complementation.
[Ramsey34Target.lean](../formal/Ramsey55/Ramsey34Target.lean) defines the exact
36-variable / 210-clause formula, constructs a satisfying assignment from any
counterexample, and proves exact CNF UNSAT implies `ForcesRed3OrBlue4 9`.
`VerifyRamsey34Exact.lean` independently compared all 210 typed clauses to the
retained DIMACS stream. Kissat solved that stream in 0.13 seconds; ordinary
`drat-trim` verified the 210,962-byte proof in 0.149 seconds with no core RAT
lemmas. The CNF and proof SHA-256 values are respectively
`1c5d12b0f0b76943d2c0ac750c158ac94939009a3fa55924aa8be4418f2bd2c4`
and
`6410b4135b83c8040024d32688b453954447f71ef7fb704d5f235041394ae2c6`.
All artifacts and an independently rerunnable audit are retained under
`data/certificates/r34-n9/`. The final combined theorem is

    forcesRed4OrBlue5_of_r34ExactCnfAndThreeExactFixedStarUnsat

so only the degree-8, degree-10, and degree-12 UNSAT certificates remain on
this `R(4,5) <= 25` route. No new `R(4,5)=25` claim is made yet.

The degree-8 branch now has a complete conditional gluing certificate layer;
see [r45-gluing-certificates.md](r45-gluing-certificates.md).  Two independent
implementations reconstructed all 54 reduced CNFs from the published 27-by-2
generalized-cover product.  CaDiCaL emitted 510,872,280 proof bytes and
ordinary `drat-trim` accepted every formula twice; the proof manifest and
second audit hash to
`dd3bb57079f53d5e153c1a6146174364716ea2e7b57d66b05f2a99c4ca23858f`
and
`8e070a197e5c2676f2b2c2e0e3ffe6382a35481cde83c5c4d7db713a5c26847d`.
The local cover/witness audit also passed, but global enumeration of all
`R(3,5;8)` and `R(4,4;16)` isomorphism classes remains an explicit formal
boundary.  Therefore this checkpoint does not yet discharge the direct d08
UNSAT hypothesis.

The complete incremental ARM build now covers 95 jobs and hashes to
`e095dde784f4d6062277f93b24d7208cd50ab8aa4a7d25d3d8340e3d363571d2`.
The full dependency-free suite passes all 232 tests; its log SHA-256 is
`f6c671bf20495f95e68ad8d79bdee210167ee730f519d5c91a3b26359b30b895`.

[Symmetry.lean](../formal/Ramsey55/Symmetry.lean) adds the generic bridge for
an optional symmetry-reduced route. It proves that a nonempty finite orbit
closed under a listed family of transformations has a least representative;
if the base predicate holds throughout the orbit, that representative obeys
every corresponding lex-leader inequality. Thus a checked lex CNF can be
used without pretending its symmetry clauses follow by DRAT from the
unsymmetrized CNF. A second theorem packages the contradiction: refuting all
leaders refutes the original predicate whenever every base solution has such
a finite closed satisfying orbit. Both theorems are kernel-checked and contain
no `sorry` or `native_decide`. Concrete permutation invariance, orbit closure,
and the DIMACS lex-encoding bridge are still explicit missing obligations.

## Independently checked inputs

The dependency-free Python implementation performs a separate computation:

- downloaded 328 graph6 records, locked by SHA-256;
- generated their complements, obtaining 656 distinct labelled graphs;
- verified that every graph has no \(K_5\) and no 5-point independent set;
- reproduced the published representative edge histogram
  \(423\ldots430\) with counts \(1,7,29,66,89,77,43,16\);
- reproduced degree support \(19,20,21,22\);
- verified that the 43-vertex near miss has exactly two monochromatic
  \(K_5\)'s:
  \(\{0,2,28,29,38\}\) and \(\{0,11,28,29,38\}\).
- checked an explicit isomorphism from the graph left after deleting common
  near-miss vertex 0 to public representative 255; the deleted vertex's
  transported attachment has exactly those two violations. This shows the
  formal lower bound of two is sharp within the public catalog.

The Python calculation is a cross-check. The formal lower-bound theorem relies
on the embedded Lean data and Lean proof, not on successful execution of the
Python program.

## Exact SAT encoding

[sat.py](../src/ramsey55/sat.py) fixes a one-to-one variable map for unordered
vertex pairs and emits two ten-literal clauses for every five-point set:

- one clause forbids all ten edges;
- one clause forbids all ten nonedges.

For \(n=43\), this gives 903 variables and 1,925,196 Ramsey clauses. Unit
clauses can fix the star of vertex 0 to degree 18 or 20, producing the two
standard symmetry-reduced benchmarks, each with 1,925,238 clauses.

Tests establish that:

- the variable map is a bijection on unordered pairs;
- the complete and empty \(K_5\) each violate the expected clause;
- a reference 42-point graph satisfies every generated clause;
- the 43-point near miss violates exactly the two clauses corresponding to its
  two monochromatic \(K_5\)'s.

The implication “the two degree-fixed cases cover every 43-point
counterexample” is not yet formalized here. Its proof needs the formal
\(R(4,5)=25\) result, the handshake parity lemma, complementation, and
relabeling.

## Negative computational benchmarks

CaDiCaL 2.1.2 was run for 60 wall-clock seconds on each raw degree-fixed
instance:

| case | result | conflicts | approximate peak RSS |
|---|---|---:|---:|
| degree 18 | <code>UNKNOWN</code> | 1,120,536 | 2.6 GB |
| degree 20 | <code>UNKNOWN</code> | 423,278 | 2.6 GB |

This is a benchmark, not evidence of unsatisfiability. Satsuma 1.4 detected two
Johnson structures and reduced the degree-18 instance from 1,925,238 to
1,527,060 clauses, but 60-second Kissat runs still returned `UNKNOWN` on the
raw and preprocessed instances. The preprocessing changes solver constants but
does not make raw CNF a practical proof route.

## The two-violation plateau

[local_search.cpp](../tools/local_search.cpp) maintains exact
monochromatic-\(K_5\) flip deltas. Starting from the public two-violation
colouring, it exhaustively enumerated the connected component formed by
single-edge flips that preserve objective value 2:

- the component has exactly 86 labelled states;
- the minimum one-flip objective change anywhere in the component is 0;
- therefore no single-edge flip from that component reaches objective 1 or 0;
- the known second near miss is reached by the zero-delta flip \((0,28)\).

A tabu run of 10 million flips over 10 restarts visited 430 objective-2 states
across the search and found no zero- or one-violation colouring. This is useful
landscape information, not a lower- or upper-bound proof.

The initial 86-state component is exactly \(C_{86}\). Its 43 transition-label
edges form a Hamilton cycle on the original 43 vertices. Four additional
complete \(C_{86}\) components were found; nauty canonicalization reduces all
430 states to the same two unlabelled types. The detailed, carefully scoped
observations are in
[the near-miss landscape note](near-miss-landscape.md).

## Negative identity experiment

The 1997 nonseparable counting identity was evaluated exactly on the official
edge-extremal \(R(4,5)\) data and on the complete 352,366-graph
\(R(4,5,24)\) catalog. A separate exact rational relaxation used every
Ramsey-compatible induced type through order six and the correct mean-edge
constraints. All resulting degree-18 through degree-24 contribution intervals
still crossed zero by a wide margin. See
[the identity experiment](nonseparable-identity-experiment.md).

This rules out a specific weak route: the old identity plus edge ranges and
only small-local distribution constraints. It does not rule out stronger
overlap consistency, exact whole-neighborhood optimization, or a new identity.

## Missing obligations for the exact theorem

There are now two precise completion routes.

The catalog route would require:

1. prove that every Ramsey-free 42-vertex colouring is, up to relabeling and
   colour swap, one of the 656 public graphs;
2. formalize the relabeling bridge and audit the orbit-to-record mapping;
3. apply the already checked nonextension certificates and reduction theorem.

The direct 43-vertex route would instead require:

1. formalize or import a checked proof of \(R(4,5)=25\);
2. reduce a hypothetical 43-point counterexample to the degree-18 or
   degree-20 split cases using complementation, parity, and relabeling;
3. replace raw SAT by a complete structural cover of both split spaces;
4. emit and independently check every computational leaf and the global cover.

Catalog completeness is currently the smallest statement separating the
formal development from the exact value, but it is still a major open
classification problem. More raw solver time does not discharge either route.
