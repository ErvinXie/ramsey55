import Ramsey55.CubeCover

namespace Ramsey55

/-- The two clauses used for the first sequential-counter cell. -/
def counterInitialClauses {variables : Nat}
    (item current : CnfLiteral variables) : CnfFormula variables :=
  [[current.negate, item], [item.negate, current]]

/-- The three clauses used in the first column after the first input. -/
def counterFirstColumnClauses {variables : Nat}
    (old item current : CnfLiteral variables) : CnfFormula variables :=
  [[old.negate, current], [item.negate, current],
    [current.negate, old, item]]

/-- The three clauses used on the triangular diagonal. -/
def counterDiagonalClauses {variables : Nat}
    (diagonal item current : CnfLiteral variables) : CnfFormula variables :=
  [[current.negate, diagonal], [current.negate, item],
    [diagonal.negate, item.negate, current]]

/-- The four clauses used for an interior sequential-counter cell. -/
def counterInteriorClauses {variables : Nat}
    (old diagonal item current : CnfLiteral variables) : CnfFormula variables :=
  [[old.negate, current], [diagonal.negate, item.negate, current],
    [current.negate, old, diagonal], [current.negate, old, item]]

theorem counterInitialClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (item current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment (counterInitialClauses item current) ↔
      (current.Holds assignment ↔ item.Holds assignment) := by
  by_cases itemValue : item.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [counterInitialClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

theorem counterFirstColumnClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (old item current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment
        (counterFirstColumnClauses old item current) ↔
      (current.Holds assignment ↔
        old.Holds assignment ∨ item.Holds assignment) := by
  by_cases oldValue : old.Holds assignment <;>
    by_cases itemValue : item.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [counterFirstColumnClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

theorem counterDiagonalClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (diagonal item current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment
        (counterDiagonalClauses diagonal item current) ↔
      (current.Holds assignment ↔
        diagonal.Holds assignment ∧ item.Holds assignment) := by
  by_cases diagonalValue : diagonal.Holds assignment <;>
    by_cases itemValue : item.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [counterDiagonalClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

theorem counterInteriorClauses_iff {variables : Nat}
    (assignment : CnfAssignment variables)
    (old diagonal item current : CnfLiteral variables) :
    SatisfiesCnfFormula assignment
        (counterInteriorClauses old diagonal item current) ↔
      (current.Holds assignment ↔ old.Holds assignment ∨
        (diagonal.Holds assignment ∧ item.Holds assignment)) := by
  by_cases oldValue : old.Holds assignment <;>
    by_cases diagonalValue : diagonal.Holds assignment <;>
    by_cases itemValue : item.Holds assignment <;>
    by_cases currentValue : current.Holds assignment <;>
    simp_all [counterInteriorClauses, SatisfiesCnfFormula,
      SatisfiesCnfClause, CnfLiteral.negate_holds_iff_not_holds]

/-- Number of true values among inputs `0, ..., length - 1`. -/
def trueCountPrefix (input : Nat → Bool) : Nat → Nat
  | 0 => 0
  | length + 1 => trueCountPrefix input length +
      if input length = true then 1 else 0

theorem trueCountPrefix_le (input : Nat → Bool) (length : Nat) :
    trueCountPrefix input length ≤ length := by
  induction length with
  | zero => simp [trueCountPrefix]
  | succ length inductionHypothesis =>
      simp only [trueCountPrefix]
      split <;> omega

/-- Boolean truth value of a signed CNF literal under an assignment. -/
def CnfLiteral.truthValue {variables : Nat}
    (assignment : CnfAssignment variables) (literal : CnfLiteral variables) : Bool :=
  assignment literal.index == literal.positive

theorem CnfLiteral.truthValue_eq_true_iff_holds {variables : Nat}
    (assignment : CnfAssignment variables) (literal : CnfLiteral variables) :
    literal.truthValue assignment = true ↔ literal.Holds assignment := by
  simp [CnfLiteral.truthValue, CnfLiteral.Holds]

/-- Bounded observable-output contract shared by the concrete order-45
counters. -/
def ExactAtLeastCounterOutputs {variables : Nat}
    (assignment : CnfAssignment variables)
    (outputs : Nat → CnfLiteral variables) (width count : Nat) : Prop :=
  ∀ k, k < width → ((outputs k).Holds assignment ↔ k + 1 ≤ count)

def sequentialCounterInputCount {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables) (rows : Nat) : Nat :=
  trueCountPrefix (fun k => (input k).truthValue assignment) rows

/-- The four local counter recurrences uniquely give every observable cell
its intended at-least semantics. Rows and columns are zero-based: row `i`
represents the first `i + 1` inputs, and column `j` means at least `j + 1`
true inputs. `width` permits a truncated counter without requiring cells past
the largest observable threshold. -/
theorem counterRecurrence_exact
    (input : Nat → Bool) (state : Nat → Nat → Prop) (rows width : Nat)
    (initial : state 0 0 ↔ input 0 = true)
    (firstColumn : ∀ i, 0 < i → i < rows →
      (state i 0 ↔ state (i - 1) 0 ∨ input i = true))
    (diagonal : ∀ i, 0 < i → i < rows → i < width →
      (state i i ↔ state (i - 1) (i - 1) ∧ input i = true))
    (interior : ∀ i j, 0 < i → i < rows → 0 < j → j < i → j < width →
      (state i j ↔ state (i - 1) j ∨
        (state (i - 1) (j - 1) ∧ input i = true)))
    (i j : Nat) (rowExists : i < rows)
    (insideRow : j ≤ i) (insideWidth : j < width) :
    state i j ↔ j + 1 ≤ trueCountPrefix input (i + 1) := by
  induction i generalizing j with
  | zero =>
      have jZero : j = 0 := by omega
      subst j
      rw [initial]
      cases inputZero : input 0 <;> simp [trueCountPrefix, inputZero]
  | succ i inductionHypothesis =>
      have countStep :
          trueCountPrefix input (i + 1 + 1) =
            trueCountPrefix input (i + 1) +
              if input (i + 1) = true then 1 else 0 := by
        rw [trueCountPrefix]
      by_cases first : j = 0
      · subst j
        rw [firstColumn (i + 1) (by omega) rowExists]
        simp only [Nat.add_sub_cancel]
        rw [inductionHypothesis 0 (by omega) (by omega) insideWidth]
        rw [countStep]
        cases newValue : input (i + 1) <;> simp <;> omega
      · by_cases last : j = i + 1
        · subst j
          rw [diagonal (i + 1) (by omega) rowExists insideWidth]
          simp only [Nat.add_sub_cancel]
          rw [inductionHypothesis i (by omega) (by omega) (by omega)]
          rw [countStep]
          have countBound := trueCountPrefix_le input (i + 1)
          cases newValue : input (i + 1) <;> simp <;> omega
        · have beforeLast : j < i + 1 := by omega
          rw [interior (i + 1) j (by omega) rowExists (by omega)
            beforeLast insideWidth]
          simp only [Nat.add_sub_cancel]
          rw [inductionHypothesis j (by omega) (by omega) insideWidth]
          rw [inductionHypothesis (j - 1) (by omega) (by omega) (by omega)]
          rw [countStep]
          cases newValue : input (i + 1) <;> simp <;> omega

/-- Semantic packaging of all local clause groups in a finite truncated
sequential counter. -/
def SatisfiesSequentialCounterCells {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat) : Prop :=
  SatisfiesCnfFormula assignment (counterInitialClauses (input 0) (state 0 0)) ∧
  (∀ i, 0 < i → i < rows → SatisfiesCnfFormula assignment
    (counterFirstColumnClauses (state (i - 1) 0) (input i) (state i 0))) ∧
  (∀ i, 0 < i → i < rows → i < width → SatisfiesCnfFormula assignment
    (counterDiagonalClauses (state (i - 1) (i - 1)) (input i) (state i i))) ∧
  (∀ i j, 0 < i → i < rows → 0 < j → j < i → j < width →
    SatisfiesCnfFormula assignment (counterInteriorClauses
      (state (i - 1) j) (state (i - 1) (j - 1)) (input i) (state i j)))

/-- The exact row-major clause stream emitted by
`at_least_counter_encoding`. Invalid cells are excluded by
`sequentialCounterCellFormula`; this selector is only observed for
`column ≤ row` and `column < width`. -/
def sequentialCounterCellClauses {variables : Nat}
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (row column : Nat) :
    CnfFormula variables :=
  if row = 0 then
    counterInitialClauses (input 0) (state 0 0)
  else if column = 0 then
    counterFirstColumnClauses (state (row - 1) 0) (input row) (state row 0)
  else if column = row then
    counterDiagonalClauses
      (state (row - 1) (row - 1)) (input row) (state row row)
  else
    counterInteriorClauses (state (row - 1) column)
      (state (row - 1) (column - 1)) (input row) (state row column)

/-- A complete truncated counter subformula in the same row-major cell and
clause order as the Python generator. -/
def sequentialCounterCellFormula {variables : Nat}
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat) :
    CnfFormula variables :=
  (List.range rows).flatMap fun row =>
    (List.range (min (row + 1) width)).flatMap fun column =>
      sequentialCounterCellClauses input state row column

/-- Satisfaction of the emitted row-major clause stream supplies every local
cell hypothesis used by the semantic counter theorem. -/
theorem satisfiesSequentialCounterCellFormula_cells {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (rowsPositive : 0 < rows) (widthPositive : 0 < width)
    (satisfied : SatisfiesCnfFormula assignment
      (sequentialCounterCellFormula input state rows width)) :
    SatisfiesSequentialCounterCells assignment input state rows width := by
  have blockSatisfied (row column : Nat) (rowBound : row < rows)
      (columnBound : column < min (row + 1) width) :
      SatisfiesCnfFormula assignment
        (sequentialCounterCellClauses input state row column) := by
    intro clause clauseMembership
    apply satisfied clause
    simp only [sequentialCounterCellFormula, List.mem_flatMap,
      List.mem_range]
    exact ⟨row, rowBound, column, columnBound, clauseMembership⟩
  refine ⟨?_, ?_, ?_, ?_⟩
  · have columnBound : 0 < min (0 + 1) width :=
      (Nat.lt_min).2 ⟨by omega, widthPositive⟩
    simpa [sequentialCounterCellClauses] using
      blockSatisfied 0 0 rowsPositive columnBound
  · intro row rowPositive rowBound
    have columnBound : 0 < min (row + 1) width :=
      (Nat.lt_min).2 ⟨by omega, widthPositive⟩
    simpa [sequentialCounterCellClauses, Nat.ne_of_gt rowPositive] using
      blockSatisfied row 0 rowBound columnBound
  · intro row rowPositive rowBound rowInsideWidth
    have columnBound : row < min (row + 1) width :=
      (Nat.lt_min).2 ⟨by omega, rowInsideWidth⟩
    simpa [sequentialCounterCellClauses, Nat.ne_of_gt rowPositive] using
      blockSatisfied row row rowBound columnBound
  · intro row column rowPositive rowBound columnPositive columnBeforeRow
      columnInsideWidth
    have columnBound : column < min (row + 1) width :=
      (Nat.lt_min).2 ⟨by omega, columnInsideWidth⟩
    have rowNotZero : row ≠ 0 := Nat.ne_of_gt rowPositive
    have columnNotZero : column ≠ 0 := Nat.ne_of_gt columnPositive
    have columnNotRow : column ≠ row := by omega
    simpa [sequentialCounterCellClauses, rowNotZero, columnNotZero,
      columnNotRow] using blockSatisfied row column rowBound columnBound

/-- A mother CNF that contains the complete row-major counter stream supplies
the same local-cell semantics. This is the subformula boundary used by the
generated order-45 DIMACS formulas. -/
theorem satisfiesSequentialCounterSubformula_cells {variables : Nat}
    (assignment : CnfAssignment variables)
    (formula : CnfFormula variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (rowsPositive : 0 < rows) (widthPositive : 0 < width)
    (satisfied : SatisfiesCnfFormula assignment formula)
    (included : ∀ clause ∈ sequentialCounterCellFormula input state rows width,
      clause ∈ formula) :
    SatisfiesSequentialCounterCells assignment input state rows width := by
  apply satisfiesSequentialCounterCellFormula_cells assignment input state
    rows width rowsPositive widthPositive
  exact SatisfiesCnfFormula.of_subset assignment formula
    (sequentialCounterCellFormula input state rows width) satisfied included

theorem satisfiesSequentialCounterCells_exact {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (cells : SatisfiesSequentialCounterCells assignment input state rows width)
    (i j : Nat) (rowExists : i < rows)
    (insideRow : j ≤ i) (insideWidth : j < width) :
    (state i j).Holds assignment ↔
      j + 1 ≤ trueCountPrefix (fun k => (input k).truthValue assignment) (i + 1) := by
  rcases cells with ⟨initialCell, firstCells, diagonalCells, interiorCells⟩
  apply counterRecurrence_exact
    (fun k => (input k).truthValue assignment)
    (fun row column => (state row column).Holds assignment)
    rows width
  · rw [CnfLiteral.truthValue_eq_true_iff_holds]
    exact (counterInitialClauses_iff assignment (input 0) (state 0 0)).mp
      initialCell
  · intro row rowPositive rowExists
    rw [CnfLiteral.truthValue_eq_true_iff_holds]
    exact (counterFirstColumnClauses_iff assignment
      (state (row - 1) 0) (input row) (state row 0)).mp
      (firstCells row rowPositive rowExists)
  · intro row rowPositive rowExists rowInsideWidth
    rw [CnfLiteral.truthValue_eq_true_iff_holds]
    exact (counterDiagonalClauses_iff assignment
      (state (row - 1) (row - 1)) (input row) (state row row)).mp
      (diagonalCells row rowPositive rowExists rowInsideWidth)
  · intro row column rowPositive rowExists columnPositive columnBeforeRow
      columnInsideWidth
    rw [CnfLiteral.truthValue_eq_true_iff_holds]
    exact (counterInteriorClauses_iff assignment
      (state (row - 1) column) (state (row - 1) (column - 1))
      (input row) (state row column)).mp
      (interiorCells row column rowPositive rowExists columnPositive
        columnBeforeRow columnInsideWidth)
  · exact rowExists
  · exact insideRow
  · exact insideWidth

theorem satisfiesSequentialCounterCells_outputs_exact {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (rowsPositive : 0 < rows) (widthAtMostRows : width ≤ rows)
    (cells : SatisfiesSequentialCounterCells assignment input state rows width) :
    ExactAtLeastCounterOutputs assignment (state (rows - 1)) width
      (sequentialCounterInputCount assignment input rows) := by
  intro threshold thresholdInside
  have exact := satisfiesSequentialCounterCells_exact assignment input state
    rows width cells (rows - 1) threshold (by omega) (by omega) thresholdInside
  have rowIndex : rows - 1 + 1 = rows := by omega
  rw [rowIndex] at exact
  simpa [sequentialCounterInputCount] using exact

#print axioms counterInitialClauses_iff
#print axioms counterFirstColumnClauses_iff
#print axioms counterDiagonalClauses_iff
#print axioms counterInteriorClauses_iff
#print axioms trueCountPrefix_le
#print axioms counterRecurrence_exact
#print axioms satisfiesSequentialCounterCellFormula_cells
#print axioms satisfiesSequentialCounterSubformula_cells
#print axioms satisfiesSequentialCounterCells_exact
#print axioms satisfiesSequentialCounterCells_outputs_exact

end Ramsey55
