import Ramsey55.CnfCardinality

namespace Ramsey55

/-- The four clauses defining the first explicit equality-prefix variable. -/
def lexFirstPrefixClauses {variables : Nat}
    (left right current : CnfLiteral variables) : CnfFormula variables :=
  [[current.negate, left.negate, right],
    [current.negate, left, right.negate],
    [left.negate, right.negate, current],
    [left, right, current]]

/-- The five clauses defining a later equality-prefix variable from its
predecessor and the current pair of input bits. -/
def lexNextPrefixClauses {variables : Nat}
    (previous left right current : CnfLiteral variables) :
    CnfFormula variables :=
  [[current.negate, previous],
    [current.negate, left.negate, right],
    [current.negate, left, right.negate],
    [previous.negate, left.negate, right.negate, current],
    [previous.negate, left, right, current]]

theorem lexFirstPrefixClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment
        (lexFirstPrefixClauses left right current) ↔
      (current.Holds assignment ↔
        (left.Holds assignment ↔ right.Holds assignment)) := by
  by_cases leftValue : left.Holds assignment <;>
    by_cases rightValue : right.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [lexFirstPrefixClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

theorem lexNextPrefixClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (previous left right current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment
        (lexNextPrefixClauses previous left right current) ↔
      (current.Holds assignment ↔ previous.Holds assignment ∧
        (left.Holds assignment ↔ right.Holds assignment)) := by
  by_cases previousValue : previous.Holds assignment <;>
    by_cases leftValue : left.Holds assignment <;>
    by_cases rightValue : right.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [lexNextPrefixClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

/-- Equality of the first `length` input positions under one assignment. -/
def LiteralPrefixEqual {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) : Nat → Prop
  | 0 => True
  | length + 1 =>
      LiteralPrefixEqual assignment left right length ∧
        ((left length).Holds assignment ↔ (right length).Holds assignment)

def literalPrefixEqualValue {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) : Nat → Bool
  | 0 => true
  | length + 1 =>
      literalPrefixEqualValue assignment left right length &&
        ((left length).truthValue assignment ==
          (right length).truthValue assignment)

theorem literalTruthValue_beq_eq_true_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : CnfLiteral variables) :
    ((left.truthValue assignment == right.truthValue assignment) = true) ↔
      (left.Holds assignment ↔ right.Holds assignment) := by
  rw [← CnfLiteral.truthValue_eq_true_iff_holds,
    ← CnfLiteral.truthValue_eq_true_iff_holds]
  cases left.truthValue assignment <;>
    cases right.truthValue assignment <;> simp

theorem literalPrefixEqualValue_eq_true_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) :
    ∀ length : Nat,
      literalPrefixEqualValue assignment left right length = true ↔
        LiteralPrefixEqual assignment left right length := by
  intro length
  induction length with
  | zero => simp [literalPrefixEqualValue, LiteralPrefixEqual]
  | succ length inductionHypothesis =>
      simp only [literalPrefixEqualValue, LiteralPrefixEqual, Bool.and_eq_true]
      rw [inductionHypothesis,
        literalTruthValue_beq_eq_true_iff assignment (left length)
          (right length)]

/-- Lexicographic `left ≤ right` through `width`, with false before true. -/
def LiteralRowsLexLe {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) (width : Nat) : Prop :=
  ∀ column, column < width →
    LiteralPrefixEqual assignment left right column →
      (left column).Holds assignment → (right column).Holds assignment

theorem LiteralPrefixEqual.congr {variables : Nat}
    (first second : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) :
    ∀ length : Nat,
      (∀ index, index < length →
        ((left index).Holds first ↔ (left index).Holds second)) →
      (∀ index, index < length →
        ((right index).Holds first ↔ (right index).Holds second)) →
      (LiteralPrefixEqual first left right length ↔
        LiteralPrefixEqual second left right length) := by
  intro length
  induction length with
  | zero => simp [LiteralPrefixEqual]
  | succ length inductionHypothesis =>
      intro leftEqual rightEqual
      simp only [LiteralPrefixEqual]
      rw [inductionHypothesis
        (fun index inside => leftEqual index (by omega))
        (fun index inside => rightEqual index (by omega)),
        leftEqual length (by omega), rightEqual length (by omega)]

/-- The order clause emitted before the equality-prefix definition at a
column. Column zero has an implicit true prefix. -/
def lexOrderClause {variables : Nat}
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (column : Nat) :
    CnfClause variables :=
  if column = 0 then [(left 0).negate, right 0]
  else [(state (column - 1)).negate, (left column).negate, right column]

/-- Exact per-column clause order used by `lex_leq_encoding`. -/
def lexColumnClauses {variables : Nat}
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (width column : Nat) :
    CnfFormula variables :=
  [lexOrderClause left right state column] ++
    if column + 1 < width then
      if column = 0 then
        lexFirstPrefixClauses (left 0) (right 0) (state 0)
      else
        lexNextPrefixClauses (state (column - 1))
          (left column) (right column) (state column)
    else []

/-- Complete clause stream for one positive-width row comparison. -/
def lexLeqFormula {variables : Nat}
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (width : Nat) :
    CnfFormula variables :=
  (List.range width).flatMap fun column =>
    lexColumnClauses left right state width column

theorem lexOrderClause_satisfied {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (width column : Nat)
    (columnBound : column < width)
    (ordered : LiteralRowsLexLe assignment left right width)
    (stateExact : ∀ index, index + 1 < width →
      ((state index).Holds assignment ↔
        LiteralPrefixEqual assignment left right (index + 1))) :
    SatisfiesCnfClause assignment
      (lexOrderClause left right state column) := by
  by_cases columnZero : column = 0
  · subst column
    have implication := ordered 0 columnBound (by
      simp [LiteralPrefixEqual])
    by_cases leftValue : (left 0).Holds assignment <;>
      by_cases rightValue : (right 0).Holds assignment <;>
      simp_all [lexOrderClause, SatisfiesCnfClause,
        CnfLiteral.negate_holds_iff_not_holds]
  · have previousBound : column - 1 + 1 < width := by omega
    have previousExact := stateExact (column - 1) previousBound
    have previousLength : column - 1 + 1 = column := by omega
    rw [previousLength] at previousExact
    have implication := ordered column columnBound
    by_cases previousValue : (state (column - 1)).Holds assignment <;>
      by_cases leftValue : (left column).Holds assignment <;>
      by_cases rightValue : (right column).Holds assignment <;>
      simp_all [lexOrderClause, SatisfiesCnfClause,
        CnfLiteral.negate_holds_iff_not_holds]

theorem lexColumnClauses_satisfied {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (width column : Nat)
    (columnBound : column < width)
    (ordered : LiteralRowsLexLe assignment left right width)
    (stateExact : ∀ index, index + 1 < width →
      ((state index).Holds assignment ↔
        LiteralPrefixEqual assignment left right (index + 1))) :
    SatisfiesCnfFormula assignment
      (lexColumnClauses left right state width column) := by
  have orderSatisfied := lexOrderClause_satisfied assignment left right state
    width column columnBound ordered stateExact
  by_cases beforeLast : column + 1 < width
  · have currentExact := stateExact column beforeLast
    by_cases columnZero : column = 0
    · subst column
      have prefixSatisfied : SatisfiesCnfFormula assignment
          (lexFirstPrefixClauses (left 0) (right 0) (state 0)) := by
        apply (lexFirstPrefixClauses_iff assignment
          (left 0) (right 0) (state 0)).mpr
        rw [currentExact]
        simp [LiteralPrefixEqual]
      intro clause membership
      simp only [lexColumnClauses, beforeLast, if_true, List.mem_append,
        List.mem_singleton] at membership
      rcases membership with rfl | prefixMembership
      · exact orderSatisfied
      · exact prefixSatisfied clause prefixMembership
    · have previousExact := stateExact (column - 1) (by omega)
      have currentPrefix :
          LiteralPrefixEqual assignment left right (column + 1) ↔
            LiteralPrefixEqual assignment left right column ∧
              ((left column).Holds assignment ↔
                (right column).Holds assignment) := by
        rw [show column + 1 = Nat.succ column by omega]
        rfl
      have previousLength : column - 1 + 1 = column := by omega
      rw [previousLength] at previousExact
      have prefixSatisfied : SatisfiesCnfFormula assignment
          (lexNextPrefixClauses (state (column - 1))
            (left column) (right column) (state column)) := by
        apply (lexNextPrefixClauses_iff assignment (state (column - 1))
          (left column) (right column) (state column)).mpr
        rw [currentExact, previousExact, currentPrefix]
      intro clause membership
      simp only [lexColumnClauses, beforeLast, if_true, columnZero, if_false,
        List.mem_append, List.mem_singleton] at membership
      rcases membership with rfl | prefixMembership
      · exact orderSatisfied
      · exact prefixSatisfied clause prefixMembership
  · intro clause membership
    simp [lexColumnClauses, beforeLast] at membership
    subst clause
    exact orderSatisfied

theorem lexLeqFormula_satisfied {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables)
    (state : Nat → CnfLiteral variables) (width : Nat)
    (ordered : LiteralRowsLexLe assignment left right width)
    (stateExact : ∀ index, index + 1 < width →
      ((state index).Holds assignment ↔
        LiteralPrefixEqual assignment left right (index + 1))) :
    SatisfiesCnfFormula assignment
      (lexLeqFormula left right state width) := by
  intro clause membership
  simp only [lexLeqFormula, List.mem_flatMap, List.mem_range] at membership
  rcases membership with ⟨column, columnBound, clauseMembership⟩
  exact lexColumnClauses_satisfied assignment left right state width column
    columnBound ordered stateExact clause clauseMembership

#print axioms lexFirstPrefixClauses_iff
#print axioms lexNextPrefixClauses_iff
#print axioms lexLeqFormula_satisfied

end Ramsey55
