import Ramsey55.LratBridge
import Ramsey55.Ramsey34Target

namespace Ramsey55

open Std.Tactic.BVDecide

theorem ramsey34EdgeLiteral_index_positive (left right : Nat)
    (ordered : left < right) (inside : right < 9) (polarity : Bool) :
    0 < (ramsey34EdgeLiteral left right polarity).index.val := by
  have upper := orderedEdgeDimacsVariable_le_36 left right ordered inside
  have lower : 0 < orderedEdgeDimacsVariable (left, right) := by
    unfold orderedEdgeDimacsVariable
    omega
  unfold ramsey34EdgeLiteral dimacsLiteral
  simp only [Fin.ofNat]
  rw [Nat.mod_eq_of_lt (by omega)]
  exact lower

/-- Every literal in the concrete `R(3,4,9)` formula uses an actual one-based
DIMACS identifier; index zero is only the unused assignment sentinel. -/
theorem ramsey34ExactFormula_usesPositiveIdentifiers :
    CnfFormulaUsesPositiveIdentifiers ramsey34ExactFormula := by
  intro clause membership literal literalMembership
  rcases ramsey34ExactFormula_shape clause membership with
    ⟨a, b, c, ab, bc, cInside, rfl⟩ |
      ⟨a, b, c, d, ab, bc, cd, dInside, rfl⟩
  · simp only [ramsey34ThreeSetClause, List.mem_cons, List.not_mem_nil,
      or_false] at literalMembership
    rcases literalMembership with rfl | rfl | rfl
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive a b ab (by omega) false
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive a c (by omega) cInside false
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive b c bc cInside false
  · simp only [ramsey34FourSetClause, List.mem_cons, List.not_mem_nil,
      or_false] at literalMembership
    rcases literalMembership with rfl | rfl | rfl | rfl | rfl | rfl
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive a b ab (by omega) true
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive a c (by omega) (by omega) true
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive a d (by omega) dInside true
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive b c bc (by omega) true
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive b d (by omega) dInside true
    · simpa [ramsey34EdgeLiteral] using
        ramsey34EdgeLiteral_index_positive c d cd dInside true

/-- A successful run of Lean's verified LRAT checker on the exact typed
`R(3,4,9)` formula discharges the small Ramsey input used by the order-45
reduction. -/
theorem forcesRed3OrBlue4_9_of_exactLratCheck
    (proof : Array LRAT.IntAction)
    (checked : LRAT.check proof ramsey34ExactFormula.toStd) :
    ForcesRed3OrBlue4 9 :=
  forcesRed3OrBlue4_9_of_exactCnfUnsat
    (cnfFormulaIsUnsat_of_lratCheck ramsey34ExactFormula proof
      ramsey34ExactFormula_usesPositiveIdentifiers checked)

#print axioms ramsey34ExactFormula_usesPositiveIdentifiers
#print axioms forcesRed3OrBlue4_9_of_exactLratCheck

end Ramsey55
