import Ramsey55.CubeCover
import Std.Tactic.BVDecide.LRAT

namespace Ramsey55

open Std.Sat

/-- Translate a project CNF literal to the representation consumed by Lean's
verified LRAT checker. -/
def CnfLiteral.toStd {variables : Nat} (literal : CnfLiteral variables) :
    Literal Nat :=
  (literal.index.val - 1, literal.positive)

def CnfClause.toStd {variables : Nat} (clause : CnfClause variables) :
    CNF.Clause Nat :=
  clause.map CnfLiteral.toStd

def CnfFormula.toStd {variables : Nat} (formula : CnfFormula variables) :
    CNF Nat :=
  { clauses := (formula.map CnfClause.toStd).toArray }

/-- Extend a finite project assignment to natural identifiers.  Only indices
originating in a typed literal are observed by `CnfFormula.toStd`. -/
def CnfAssignment.toStd {variables : Nat} [NeZero variables]
    (assignment : CnfAssignment variables) : Nat → Bool :=
  fun identifier => assignment (Fin.ofNat variables (identifier + 1))

/-- Project formulas reserve identifier zero as a dummy.  This predicate is
the explicit side condition needed when translating their one-based DIMACS
identifiers to Lean's zero-based `CNF Nat`; Lean's LRAT conversion adds one
back before checking a DIMACS proof. -/
def CnfFormulaUsesPositiveIdentifiers {variables : Nat}
    (formula : CnfFormula variables) : Prop :=
  ∀ clause ∈ formula, ∀ literal ∈ clause, 0 < literal.index.val

theorem cnfLiteral_toStd_eval_eq_true_iff {variables : Nat}
    [NeZero variables] (assignment : CnfAssignment variables)
    (literal : CnfLiteral variables) (positive : 0 < literal.index.val) :
    (assignment.toStd literal.toStd.1 == literal.toStd.2) = true ↔
      literal.Holds assignment := by
  have shifted : literal.index.val - 1 + 1 = literal.index.val := by omega
  simp [CnfAssignment.toStd, CnfLiteral.toStd, CnfLiteral.Holds, shifted]

theorem cnfClause_toStd_eval_eq_true_iff {variables : Nat}
    [NeZero variables] (assignment : CnfAssignment variables)
    (clause : CnfClause variables)
    (positive : ∀ literal ∈ clause, 0 < literal.index.val) :
    CNF.Clause.eval assignment.toStd clause.toStd = true ↔
      SatisfiesCnfClause assignment clause := by
  simp only [CNF.Clause.eval, List.any_eq_true, CnfClause.toStd,
    SatisfiesCnfClause]
  constructor
  · rintro ⟨translated, translatedMembership, evaluated⟩
    rw [List.mem_map] at translatedMembership
    rcases translatedMembership with ⟨literal, membership, rfl⟩
    exact ⟨literal, membership,
      (cnfLiteral_toStd_eval_eq_true_iff assignment literal
        (positive literal membership)).mp evaluated⟩
  · rintro ⟨literal, membership, holds⟩
    exact ⟨literal.toStd, List.mem_map.mpr ⟨literal, membership, rfl⟩,
      (cnfLiteral_toStd_eval_eq_true_iff assignment literal
        (positive literal membership)).mpr holds⟩

theorem cnfFormula_toStd_eval_eq_true_iff {variables : Nat}
    [NeZero variables] (assignment : CnfAssignment variables)
    (formula : CnfFormula variables)
    (positive : CnfFormulaUsesPositiveIdentifiers formula) :
    CNF.eval assignment.toStd formula.toStd = true ↔
      SatisfiesCnfFormula assignment formula := by
  simp only [CNF.eval, CnfFormula.toStd, List.all_toArray, List.all_eq_true,
    List.mem_map, SatisfiesCnfFormula]
  constructor
  · intro evaluated clause membership
    exact (cnfClause_toStd_eval_eq_true_iff assignment clause
      (positive clause membership)).mp
        (evaluated clause.toStd ⟨clause, membership, rfl⟩)
  · intro satisfied translated membership
    rcases membership with ⟨clause, membership, rfl⟩
    exact (cnfClause_toStd_eval_eq_true_iff assignment clause
      (positive clause membership)).mpr (satisfied clause membership)

/-- Soundness bridge from Lean's verified LRAT checker to the project's typed
CNF UNSAT predicate.  Certificate parsing/evaluation is deliberately kept
outside this theorem; callers must supply the checker's successful Boolean
result. -/
theorem cnfFormulaIsUnsat_of_lratCheck {variables : Nat} [NeZero variables]
    (formula : CnfFormula variables)
    (proof : Array Std.Tactic.BVDecide.LRAT.IntAction)
    (positive : CnfFormulaUsesPositiveIdentifiers formula)
    (checked : Std.Tactic.BVDecide.LRAT.check proof formula.toStd) :
    CnfFormulaIsUnsat formula := by
  have unsat := Std.Tactic.BVDecide.LRAT.check_sound proof formula.toStd checked
  intro satisfiable
  rcases satisfiable with ⟨assignment, satisfied⟩
  have evaluated : CNF.eval assignment.toStd formula.toStd = true :=
    (cnfFormula_toStd_eval_eq_true_iff assignment formula positive).mpr satisfied
  have rejected : CNF.eval assignment.toStd formula.toStd = false :=
    unsat assignment.toStd
  simp_all

#print axioms cnfClause_toStd_eval_eq_true_iff
#print axioms cnfFormula_toStd_eval_eq_true_iff
#print axioms cnfFormulaIsUnsat_of_lratCheck

end Ramsey55
