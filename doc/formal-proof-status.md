# R(5,5) formal proof status

Updated: 2026-08-15

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
importing or checking the generated cube data and leaf UNSAT results, and connecting the full
excess-witness reduction to an arbitrary Ramsey-free 45-vertex colouring.

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

[CnfCardinality.lean](../formal/Ramsey55/CnfCardinality.lean) discharges the
generic sequential-counter soundness obligation. It proves directly from CNF
semantics that the generator's initial, first-column, diagonal, and interior
clause groups encode respectively `current ↔ item`, `current ↔ old ∨ item`,
`current ↔ diagonal ∧ item`, and
`current ↔ old ∨ (diagonal ∧ item)`. A finite row/width induction then proves
that every state cell means “at least column+1 true inputs,” and packages the
last row as `ExactAtLeastCounterOutputs`.

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

The order-45 file instantiates this theorem at the actual H/J row counts and
counter widths: `(190,101)/(276,133)`, `(210,108)/(253,123)`, and
`(231,115)/(231,115)`. It now derives three formula-relative cube covers from
mother-CNF satisfaction and inclusion of the two row-major counter substreams
plus the generated constraint tail. No separate semantic range or density
hypothesis remains. What remains is data-level rather than counter mathematics:
prove the generated mother formula contains that concrete typed suffix.

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
independent Python verifier already checks those bytes and maps, but that fact
has not yet been imported as a Lean theorem. Graph/excess reduction and checked
UNSAT-certificate import remain separate obligations.

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
