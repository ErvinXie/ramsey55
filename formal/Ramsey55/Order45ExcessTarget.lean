import Ramsey55.Order45LocalCatalog
import Ramsey55.Order45Dimacs

namespace Ramsey55

/-- Exact graph-to-CNF obligation for one dense excess mother.  It includes
the fixed-apex branch, the concrete H/J edge counts, and the branch density
threshold.  Any additional degree-window, lex-leader, counter, or auxiliary
clauses in the concrete formula must be justified by the supplied satisfying
assignment. -/
def DenseExcessCnfComplete {variables : Nat} (degree threshold : Nat)
    (formula : CnfFormula variables) : Prop :=
  ∀ color : Coloring 45,
    IsSimpleColoring color → IsRamseyFree55 color →
      ∀ edgesH edgesJ : Nat,
        HasFixedStar color degree →
        HasOrder45LocalEdgeCounts color 0 edgesH edgesJ →
        threshold ≤ edgesH + edgesJ →
          ∃ assignment, SatisfiesCnfFormula assignment formula

/-- Smaller graph-to-CNF interface after the published local-catalog edge
ranges have been separated out.  An encoder only has to construct a model for
the branch inside the four exact H/J bounds. -/
def CatalogBoundedDenseExcessCnfComplete {variables : Nat}
    (degree threshold lowerH upperH lowerJ upperJ : Nat)
    (formula : CnfFormula variables) : Prop :=
  ∀ color : Coloring 45,
    IsSimpleColoring color → IsRamseyFree55 color →
      ∀ edgesH edgesJ : Nat,
        HasFixedStar color degree →
        HasOrder45LocalEdgeCounts color 0 edgesH edgesJ →
        threshold ≤ edgesH + edgesJ →
        lowerH ≤ edgesH → edgesH ≤ upperH →
        lowerJ ≤ edgesJ → edgesJ ≤ upperJ →
          ∃ assignment, SatisfiesCnfFormula assignment formula

/-- The checked local-padding bridge and two published edge-range instances
upgrade range-bounded encoding completeness to the full dense-excess
completeness contract. -/
theorem denseExcessCnfComplete_of_catalogRanges
    {variables : Nat}
    (degree threshold lowerH upperH lowerJ upperJ : Nat)
    (bounded : degree ≤ 44) (formula : CnfFormula variables)
    (rangeH : Ramsey45EdgeRange degree lowerH upperH)
    (rangeJ : Ramsey45EdgeRange (44 - degree) lowerJ upperJ)
    (complete : CatalogBoundedDenseExcessCnfComplete degree threshold
      lowerH upperH lowerJ upperJ formula) :
    DenseExcessCnfComplete degree threshold formula := by
  intro color simple ramseyFree edgesH edgesJ fixed counts dense
  rcases order45LocalEdgeCounts_bounds_of_catalog color simple ramseyFree
      degree bounded fixed lowerH upperH lowerJ upperJ rangeH rangeJ
      edgesH edgesJ counts with ⟨hLower, hUpper, jLower, jUpper⟩
  exact complete color simple ramseyFree edgesH edgesJ fixed counts dense
    hLower hUpper jLower jUpper

/-- The five exact published edge ranges used by the three order-45 excess
branches.  This proposition is intentionally an external catalog theorem
boundary until those finite classifications are imported or audited. -/
def Order45ExcessCatalogRanges : Prop :=
  Ramsey45EdgeRange 20 68 100 ∧
  Ramsey45EdgeRange 21 77 107 ∧
  Ramsey45EdgeRange 22 88 114 ∧
  Ramsey45EdgeRange 23 101 122 ∧
  Ramsey45EdgeRange 24 116 132

/-- Refuting all three complete dense-excess mothers rules out every
Ramsey-free order-45 colouring.  The checked global identity supplies the
20/21/22 split; no parity shortcut is used here. -/
theorem forcesMonochromatic5_45_of_denseExcessCnfs
    {variables20 variables21 variables22 : Nat}
    (r45 : ForcesRed4OrBlue5 25)
    (formula20 : CnfFormula variables20)
    (formula21 : CnfFormula variables21)
    (formula22 : CnfFormula variables22)
    (complete20 : DenseExcessCnfComplete 20 226 formula20)
    (complete21 : DenseExcessCnfComplete 21 222 formula21)
    (complete22 : DenseExcessCnfComplete 22 220 formula22)
    (unsat20 : CnfFormulaIsUnsat formula20)
    (unsat21 : CnfFormulaIsUnsat formula21)
    (unsat22 : CnfFormulaIsUnsat formula22) :
    ForcesMonochromatic5 45 := by
  intro color simple ramseyFree
  rcases order45_exists_dense_excess_branch_of_r45 r45 color simple ramseyFree
      with
    ⟨normalized, edgesH, edgesJ, normalizedSimple, normalizedFree, counts,
      branch20 | branch21 | branch22⟩
  · exact unsat20 (complete20 normalized normalizedSimple normalizedFree
      edgesH edgesJ branch20.1 counts branch20.2.2)
  · exact unsat21 (complete21 normalized normalizedSimple normalizedFree
      edgesH edgesJ branch21.1 counts branch21.2.2)
  · exact unsat22 (complete22 normalized normalizedSimple normalizedFree
      edgesH edgesJ branch22.1 counts branch22.2.2)

/-- Certificate-facing excess route.  A formula-relative cube cover and a
checked refutation of every covered leaf produce each of the three mother
UNSAT facts consumed above. -/
theorem forcesMonochromatic5_45_of_denseExcessCubeRefutations
    {variables20 variables21 variables22 : Nat}
    (r45 : ForcesRed4OrBlue5 25)
    (formula20 : CnfFormula variables20)
    (formula21 : CnfFormula variables21)
    (formula22 : CnfFormula variables22)
    (cubes20 : List (CnfCube variables20))
    (cubes21 : List (CnfCube variables21))
    (cubes22 : List (CnfCube variables22))
    (complete20 : DenseExcessCnfComplete 20 226 formula20)
    (complete21 : DenseExcessCnfComplete 21 222 formula21)
    (complete22 : DenseExcessCnfComplete 22 220 formula22)
    (cover20 : CnfCubeFamilyCoversFormula formula20 cubes20)
    (cover21 : CnfCubeFamilyCoversFormula formula21 cubes21)
    (cover22 : CnfCubeFamilyCoversFormula formula22 cubes22)
    (leaves20 : ∀ cube ∈ cubes20, CnfCubeIsUnsat formula20 cube)
    (leaves21 : ∀ cube ∈ cubes21, CnfCubeIsUnsat formula21 cube)
    (leaves22 : ∀ cube ∈ cubes22, CnfCubeIsUnsat formula22 cube) :
    ForcesMonochromatic5 45 := by
  exact forcesMonochromatic5_45_of_denseExcessCnfs r45
    formula20 formula21 formula22 complete20 complete21 complete22
    (cnfFormulaIsUnsat_of_relativeCubeCover formula20 cubes20 cover20 leaves20)
    (cnfFormulaIsUnsat_of_relativeCubeCover formula21 cubes21 cover21 leaves21)
    (cnfFormulaIsUnsat_of_relativeCubeCover formula22 cubes22 cover22 leaves22)

/-- Concrete generated-cube form.  The only remaining certificate inputs are
the exact graph-to-mother completeness predicates, inclusion of each checked
counter tail in its mother formula, and refutations of the committed
28/36/45 DIMACS cube families. -/
theorem forcesMonochromatic5_45_of_order45DimacsCubeRefutations
    (r45 : ForcesRed4OrBlue5 25)
    (formula20 : CnfFormula (78697 + 1))
    (formula21 : CnfFormula (77148 + 1))
    (formula22 : CnfFormula (76651 + 1))
    (complete20 : DenseExcessCnfComplete 20 226 formula20)
    (complete21 : DenseExcessCnfComplete 21 222 formula21)
    (complete22 : DenseExcessCnfComplete 22 220 formula22)
    (tail20 : ∀ clause ∈ order45Degree20CounterTail, clause ∈ formula20)
    (tail21 : ∀ clause ∈ order45Degree21CounterTail, clause ∈ formula21)
    (tail22 : ∀ clause ∈ order45Degree22CounterTail, clause ∈ formula22)
    (leaves20 : ∀ cube ∈ order45Degree20CnfCubes,
      CnfCubeIsUnsat formula20 cube)
    (leaves21 : ∀ cube ∈ order45Degree21CnfCubes,
      CnfCubeIsUnsat formula21 cube)
    (leaves22 : ∀ cube ∈ order45Degree22CnfCubes,
      CnfCubeIsUnsat formula22 cube) :
    ForcesMonochromatic5 45 := by
  exact forcesMonochromatic5_45_of_denseExcessCubeRefutations r45
    formula20 formula21 formula22
    order45Degree20CnfCubes order45Degree21CnfCubes order45Degree22CnfCubes
    complete20 complete21 complete22
    (order45Degree20Mother_cover formula20 tail20)
    (order45Degree21Mother_cover formula21 tail21)
    (order45Degree22Mother_cover formula22 tail22)
    leaves20 leaves21 leaves22

/-- Fully factored concrete target.  Compared with
`forcesMonochromatic5_45_of_order45DimacsCubeRefutations`, the three opaque
mother-completeness premises are reduced to range-bounded encoder premises,
while the five published `R(4,5,n)` edge ranges are exposed once as a separate
classification boundary. -/
theorem forcesMonochromatic5_45_of_order45CatalogDimacsCubeRefutations
    (r45 : ForcesRed4OrBlue5 25)
    (ranges : Order45ExcessCatalogRanges)
    (formula20 : CnfFormula (78697 + 1))
    (formula21 : CnfFormula (77148 + 1))
    (formula22 : CnfFormula (76651 + 1))
    (complete20 : CatalogBoundedDenseExcessCnfComplete
      20 226 68 100 116 132 formula20)
    (complete21 : CatalogBoundedDenseExcessCnfComplete
      21 222 77 107 101 122 formula21)
    (complete22 : CatalogBoundedDenseExcessCnfComplete
      22 220 88 114 88 114 formula22)
    (tail20 : ∀ clause ∈ order45Degree20CounterTail, clause ∈ formula20)
    (tail21 : ∀ clause ∈ order45Degree21CounterTail, clause ∈ formula21)
    (tail22 : ∀ clause ∈ order45Degree22CounterTail, clause ∈ formula22)
    (leaves20 : ∀ cube ∈ order45Degree20CnfCubes,
      CnfCubeIsUnsat formula20 cube)
    (leaves21 : ∀ cube ∈ order45Degree21CnfCubes,
      CnfCubeIsUnsat formula21 cube)
    (leaves22 : ∀ cube ∈ order45Degree22CnfCubes,
      CnfCubeIsUnsat formula22 cube) :
    ForcesMonochromatic5 45 := by
  rcases ranges with ⟨range20, range21, range22, range23, range24⟩
  exact forcesMonochromatic5_45_of_order45DimacsCubeRefutations r45
    formula20 formula21 formula22
    (denseExcessCnfComplete_of_catalogRanges 20 226 68 100 116 132
      (by omega) formula20 range20 range24 complete20)
    (denseExcessCnfComplete_of_catalogRanges 21 222 77 107 101 122
      (by omega) formula21 range21 range23 complete21)
    (denseExcessCnfComplete_of_catalogRanges 22 220 88 114 88 114
      (by omega) formula22 range22 range22 complete22)
    tail20 tail21 tail22 leaves20 leaves21 leaves22

#print axioms forcesMonochromatic5_45_of_denseExcessCnfs
#print axioms forcesMonochromatic5_45_of_denseExcessCubeRefutations
#print axioms forcesMonochromatic5_45_of_order45DimacsCubeRefutations
#print axioms denseExcessCnfComplete_of_catalogRanges
#print axioms forcesMonochromatic5_45_of_order45CatalogDimacsCubeRefutations

end Ramsey55
