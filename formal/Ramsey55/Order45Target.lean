import Ramsey55.Order45Window
import Ramsey55.CubeCover

namespace Ramsey55

/-- A CNF is a complete encoding of Ramsey-free colourings in one fixed-star
branch when every such colouring extends to a satisfying assignment.  This is
the exact graph-to-CNF obligation that a concrete DIMACS bridge must prove. -/
def FixedStarCnfComplete {variables : Nat} (degree : Nat)
    (formula : CnfFormula variables) : Prop :=
  ∀ color : Coloring 45,
    IsSimpleColoring color → IsRamseyFree55 color →
      HasFixedStar color degree →
        ∃ assignment, SatisfiesCnfFormula assignment formula

/-- Refuting a complete fixed-star encoding excludes Ramsey-free colourings
in that branch. -/
theorem noRamseyFreeFixedStar_of_cnfUnsat {variables degree : Nat}
    (formula : CnfFormula variables)
    (complete : FixedStarCnfComplete degree formula)
    (unsat : CnfFormulaIsUnsat formula) :
    ∀ color : Coloring 45,
      IsSimpleColoring color → HasFixedStar color degree →
        ¬ IsRamseyFree55 color := by
  intro color simple fixedStar ramseyFree
  exact unsat (complete color simple ramseyFree fixedStar)

/-- End-to-end order-45 reduction.  Apart from the order-25 `R(4,5)` input,
the remaining hypotheses are exactly graph-to-CNF completeness and checked
UNSAT for the degree-20 and degree-22 fixed-star formulas. -/
theorem forcesMonochromatic5_45_of_fixedStarCnf
    {variables20 variables22 : Nat}
    (r45 : ForcesRed4OrBlue5 25)
    (formula20 : CnfFormula variables20)
    (formula22 : CnfFormula variables22)
    (complete20 : FixedStarCnfComplete 20 formula20)
    (complete22 : FixedStarCnfComplete 22 formula22)
    (unsat20 : CnfFormulaIsUnsat formula20)
    (unsat22 : CnfFormulaIsUnsat formula22) :
    ForcesMonochromatic5 45 := by
  intro color simple ramseyFree
  rcases order45_fixedStar_normalize_of_r45 r45 color simple ramseyFree with
    ⟨normalized, normalizedSimple, normalizedFree, branch⟩
  rcases branch with branch20 | branch22
  · exact unsat20
      (complete20 normalized normalizedSimple normalizedFree branch20.1)
  · exact unsat22
      (complete22 normalized normalizedSimple normalizedFree branch22.1)

/-- Certificate-facing form of the end-to-end reduction.  Formula-relative
cube coverage plus a refutation of every covered leaf supplies each branch
UNSAT hypothesis required above. -/
theorem forcesMonochromatic5_45_of_fixedStarCubeRefutations
    {variables20 variables22 : Nat}
    (r45 : ForcesRed4OrBlue5 25)
    (formula20 : CnfFormula variables20)
    (formula22 : CnfFormula variables22)
    (cubes20 : List (CnfCube variables20))
    (cubes22 : List (CnfCube variables22))
    (complete20 : FixedStarCnfComplete 20 formula20)
    (complete22 : FixedStarCnfComplete 22 formula22)
    (cover20 : CnfCubeFamilyCoversFormula formula20 cubes20)
    (cover22 : CnfCubeFamilyCoversFormula formula22 cubes22)
    (leaves20 : ∀ cube ∈ cubes20, CnfCubeIsUnsat formula20 cube)
    (leaves22 : ∀ cube ∈ cubes22, CnfCubeIsUnsat formula22 cube) :
    ForcesMonochromatic5 45 := by
  exact forcesMonochromatic5_45_of_fixedStarCnf r45 formula20 formula22
    complete20 complete22
    (cnfFormulaIsUnsat_of_relativeCubeCover formula20 cubes20 cover20 leaves20)
    (cnfFormulaIsUnsat_of_relativeCubeCover formula22 cubes22 cover22 leaves22)

#print axioms noRamseyFreeFixedStar_of_cnfUnsat
#print axioms forcesMonochromatic5_45_of_fixedStarCnf
#print axioms forcesMonochromatic5_45_of_fixedStarCubeRefutations

end Ramsey55
