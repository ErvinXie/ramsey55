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

/-- The two unit clauses emitted for an inclusive lower/upper counter range. -/
def counterRangeClauses {variables : Nat}
    (outputs : Nat → CnfLiteral variables) (lower upper : Nat) :
    CnfFormula variables :=
  [[outputs (lower - 1)], [(outputs upper).negate]]

theorem counterRangeClauses_bounds {variables : Nat}
    (assignment : CnfAssignment variables)
    (outputs : Nat → CnfLiteral variables) (width count lower upper : Nat)
    (lowerPositive : 0 < lower) (ordered : lower ≤ upper)
    (upperInside : upper < width)
    (exact : ExactAtLeastCounterOutputs assignment outputs width count)
    (satisfied : SatisfiesCnfFormula assignment
      (counterRangeClauses outputs lower upper)) :
    lower ≤ count ∧ count ≤ upper := by
  have lowerHolds : (outputs (lower - 1)).Holds assignment := by
    have := satisfied [outputs (lower - 1)] (by simp [counterRangeClauses])
    simpa [SatisfiesCnfClause] using this
  have upperDoesNotHold : ¬(outputs upper).Holds assignment := by
    have := satisfied [(outputs upper).negate] (by simp [counterRangeClauses])
    simpa [SatisfiesCnfClause,
      CnfLiteral.negate_holds_iff_not_holds] using this
  have lowerExact := exact (lower - 1) (by omega)
  have upperExact := exact upper upperInside
  rw [lowerExact] at lowerHolds
  rw [upperExact] at upperDoesNotHold
  omega

theorem satisfiesCounterRangeClauses_of_bounds {variables : Nat}
    (assignment : CnfAssignment variables)
    (outputs : Nat → CnfLiteral variables) (width count lower upper : Nat)
    (lowerPositive : 0 < lower) (ordered : lower ≤ upper)
    (upperInside : upper < width)
    (lowerBound : lower ≤ count) (upperBound : count ≤ upper)
    (exact : ExactAtLeastCounterOutputs assignment outputs width count) :
    SatisfiesCnfFormula assignment
      (counterRangeClauses outputs lower upper) := by
  intro clause membership
  simp [counterRangeClauses] at membership
  rcases membership with rfl | rfl
  · have outputInside : lower - 1 < width := by omega
    have holds : (outputs (lower - 1)).Holds assignment := by
      rw [exact (lower - 1) outputInside]
      omega
    exact ⟨outputs (lower - 1), by simp, holds⟩
  · have doesNotHold : ¬(outputs upper).Holds assignment := by
      rw [exact upper upperInside]
      omega
    exact ⟨(outputs upper).negate, by simp,
      (CnfLiteral.negate_holds_iff_not_holds assignment (outputs upper)).mpr
        doesNotHold⟩

/-- One clause of the generator's lower bound on the sum of two observable
at-least counters. `split` ranges from zero through `threshold - 1`; outputs
past a truncated width are omitted exactly as in the Python encoder. -/
def counterSumClause {variables : Nat}
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth threshold split : Nat) : CnfClause variables :=
  (if split + 1 ≤ hWidth then [hOutputs split] else []) ++
  (if threshold - split ≤ jWidth then
    [jOutputs (threshold - split - 1)] else [])

def counterSumFormula {variables : Nat}
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth threshold : Nat) : CnfFormula variables :=
  (List.range threshold).map fun split =>
    counterSumClause hOutputs jOutputs hWidth jWidth threshold split

/-- The exact tail emitted after two counter streams: four range units followed
by the lower-bound-on-sum clauses. -/
def counterPairConstraintFormula {variables : Nat}
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth hLower hUpper jLower jUpper threshold : Nat) :
    CnfFormula variables :=
  counterRangeClauses hOutputs hLower hUpper ++
  counterRangeClauses jOutputs jLower jUpper ++
  counterSumFormula hOutputs jOutputs hWidth jWidth threshold

theorem counterSumFormula_lower_bound {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth threshold hCount jCount : Nat)
    (hExact : ExactAtLeastCounterOutputs
      assignment hOutputs hWidth hCount)
    (jExact : ExactAtLeastCounterOutputs
      assignment jOutputs jWidth jCount)
    (satisfied : SatisfiesCnfFormula assignment
      (counterSumFormula hOutputs jOutputs hWidth jWidth threshold)) :
    threshold ≤ hCount + jCount := by
  by_cases dense : threshold ≤ hCount + jCount
  · exact dense
  · exfalso
    have hCountBelow : hCount < threshold := by omega
    have clauseMember :
        counterSumClause hOutputs jOutputs hWidth jWidth threshold hCount ∈
          counterSumFormula hOutputs jOutputs hWidth jWidth threshold := by
      simp only [counterSumFormula, List.mem_map, List.mem_range]
      exact ⟨hCount, hCountBelow, rfl⟩
    have clauseSatisfied := satisfied _ clauseMember
    rcases clauseSatisfied with ⟨literal, literalMember, literalHolds⟩
    by_cases hFits : hCount + 1 ≤ hWidth
    · have hDoesNotHold : ¬(hOutputs hCount).Holds assignment := by
        rw [hExact hCount (by omega)]
        omega
      by_cases jFits : threshold - hCount ≤ jWidth
      · have jRequiredPositive : 0 < threshold - hCount := by omega
        have jDoesNotHold :
            ¬(jOutputs (threshold - hCount - 1)).Holds assignment := by
          rw [jExact (threshold - hCount - 1) (by omega)]
          omega
        simp [counterSumClause, hFits, jFits] at literalMember
        rcases literalMember with rfl | rfl
        · exact hDoesNotHold literalHolds
        · exact jDoesNotHold literalHolds
      · simp [counterSumClause, hFits, jFits] at literalMember
        subst literal
        exact hDoesNotHold literalHolds
    · by_cases jFits : threshold - hCount ≤ jWidth
      · have jRequiredPositive : 0 < threshold - hCount := by omega
        have jDoesNotHold :
            ¬(jOutputs (threshold - hCount - 1)).Holds assignment := by
          rw [jExact (threshold - hCount - 1) (by omega)]
          omega
        simp [counterSumClause, hFits, jFits] at literalMember
        subst literal
        exact jDoesNotHold literalHolds
      · simp [counterSumClause, hFits, jFits] at literalMember

theorem satisfiesCounterSumFormula_of_lower_bound {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth threshold hCount jCount : Nat)
    (hCountInside : hCount ≤ hWidth) (jCountInside : jCount ≤ jWidth)
    (dense : threshold ≤ hCount + jCount)
    (hExact : ExactAtLeastCounterOutputs
      assignment hOutputs hWidth hCount)
    (jExact : ExactAtLeastCounterOutputs
      assignment jOutputs jWidth jCount) :
    SatisfiesCnfFormula assignment
      (counterSumFormula hOutputs jOutputs hWidth jWidth threshold) := by
  intro clause membership
  simp only [counterSumFormula, List.mem_map, List.mem_range] at membership
  rcases membership with ⟨split, splitInside, rfl⟩
  by_cases hEnough : split + 1 ≤ hCount
  · have outputInside : split < hWidth := by omega
    have hFits : split + 1 ≤ hWidth := by omega
    have holds : (hOutputs split).Holds assignment :=
      (hExact split outputInside).mpr hEnough
    exact ⟨hOutputs split, by simp [counterSumClause, hFits], holds⟩
  · have neededPositive : 0 < threshold - split := by omega
    have jEnough : threshold - split ≤ jCount := by omega
    have jFits : threshold - split ≤ jWidth := by omega
    have outputInside : threshold - split - 1 < jWidth := by omega
    have holds :
        (jOutputs (threshold - split - 1)).Holds assignment := by
      rw [jExact (threshold - split - 1) outputInside]
      omega
    exact ⟨jOutputs (threshold - split - 1),
      by simp [counterSumClause, jFits], holds⟩

theorem counterPairConstraintFormula_bounds {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth hCount jCount hLower hUpper jLower jUpper threshold : Nat)
    (hLowerPositive : 0 < hLower) (hOrdered : hLower ≤ hUpper)
    (hUpperInside : hUpper < hWidth)
    (jLowerPositive : 0 < jLower) (jOrdered : jLower ≤ jUpper)
    (jUpperInside : jUpper < jWidth)
    (hExact : ExactAtLeastCounterOutputs
      assignment hOutputs hWidth hCount)
    (jExact : ExactAtLeastCounterOutputs
      assignment jOutputs jWidth jCount)
    (satisfied : SatisfiesCnfFormula assignment
      (counterPairConstraintFormula hOutputs jOutputs hWidth jWidth
        hLower hUpper jLower jUpper threshold)) :
    hLower ≤ hCount ∧ hCount ≤ hUpper ∧
      jLower ≤ jCount ∧ jCount ≤ jUpper ∧
      threshold ≤ hCount + jCount := by
  have hRangeSatisfied : SatisfiesCnfFormula assignment
      (counterRangeClauses hOutputs hLower hUpper) := by
    apply SatisfiesCnfFormula.of_subset assignment
      (counterPairConstraintFormula hOutputs jOutputs hWidth jWidth
        hLower hUpper jLower jUpper threshold)
      (counterRangeClauses hOutputs hLower hUpper) satisfied
    intro clause membership
    simp [counterPairConstraintFormula, membership]
  have jRangeSatisfied : SatisfiesCnfFormula assignment
      (counterRangeClauses jOutputs jLower jUpper) := by
    apply SatisfiesCnfFormula.of_subset assignment
      (counterPairConstraintFormula hOutputs jOutputs hWidth jWidth
        hLower hUpper jLower jUpper threshold)
      (counterRangeClauses jOutputs jLower jUpper) satisfied
    intro clause membership
    simp [counterPairConstraintFormula, membership]
  have sumSatisfied : SatisfiesCnfFormula assignment
      (counterSumFormula hOutputs jOutputs hWidth jWidth threshold) := by
    apply SatisfiesCnfFormula.of_subset assignment
      (counterPairConstraintFormula hOutputs jOutputs hWidth jWidth
        hLower hUpper jLower jUpper threshold)
      (counterSumFormula hOutputs jOutputs hWidth jWidth threshold) satisfied
    intro clause membership
    simp [counterPairConstraintFormula, membership]
  rcases counterRangeClauses_bounds assignment hOutputs hWidth hCount
    hLower hUpper hLowerPositive hOrdered hUpperInside hExact
    hRangeSatisfied with ⟨hLowerBound, hUpperBound⟩
  rcases counterRangeClauses_bounds assignment jOutputs jWidth jCount
    jLower jUpper jLowerPositive jOrdered jUpperInside jExact
    jRangeSatisfied with ⟨jLowerBound, jUpperBound⟩
  exact ⟨hLowerBound, hUpperBound, jLowerBound, jUpperBound,
    counterSumFormula_lower_bound assignment hOutputs jOutputs
      hWidth jWidth threshold hCount jCount hExact jExact sumSatisfied⟩

theorem satisfiesCounterPairConstraintFormula_of_bounds {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth hCount jCount hLower hUpper jLower jUpper threshold : Nat)
    (hLowerPositive : 0 < hLower) (hOrdered : hLower ≤ hUpper)
    (hUpperInside : hUpper < hWidth)
    (jLowerPositive : 0 < jLower) (jOrdered : jLower ≤ jUpper)
    (jUpperInside : jUpper < jWidth)
    (hLowerBound : hLower ≤ hCount) (hUpperBound : hCount ≤ hUpper)
    (jLowerBound : jLower ≤ jCount) (jUpperBound : jCount ≤ jUpper)
    (dense : threshold ≤ hCount + jCount)
    (hExact : ExactAtLeastCounterOutputs
      assignment hOutputs hWidth hCount)
    (jExact : ExactAtLeastCounterOutputs
      assignment jOutputs jWidth jCount) :
    SatisfiesCnfFormula assignment
      (counterPairConstraintFormula hOutputs jOutputs hWidth jWidth
        hLower hUpper jLower jUpper threshold) := by
  have hRange := satisfiesCounterRangeClauses_of_bounds assignment hOutputs
    hWidth hCount hLower hUpper hLowerPositive hOrdered hUpperInside
    hLowerBound hUpperBound hExact
  have jRange := satisfiesCounterRangeClauses_of_bounds assignment jOutputs
    jWidth jCount jLower jUpper jLowerPositive jOrdered jUpperInside
    jLowerBound jUpperBound jExact
  have sum := satisfiesCounterSumFormula_of_lower_bound assignment
    hOutputs jOutputs hWidth jWidth threshold hCount jCount
    (by omega) (by omega) dense hExact jExact
  intro clause membership
  simp only [counterPairConstraintFormula, List.mem_append] at membership
  rcases membership with rangesMembership | sumMembership
  · rcases rangesMembership with hMembership | jMembership
    · exact hRange clause hMembership
    · exact jRange clause jMembership
  · exact sum clause sumMembership

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

/-- Conversely, assigning every valid counter cell its intended at-least
truth value satisfies every local clause group. This is the generic
counter-completeness direction needed when extending a graph-primary
assignment with auxiliary state variables. -/
theorem satisfiesSequentialCounterCells_of_exact {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (rowsPositive : 0 < rows) (widthPositive : 0 < width)
    (exact : ∀ i j, i < rows → j ≤ i → j < width →
      ((state i j).Holds assignment ↔
        j + 1 ≤ trueCountPrefix
          (fun k => (input k).truthValue assignment) (i + 1))) :
    SatisfiesSequentialCounterCells assignment input state rows width := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · apply (counterInitialClauses_iff assignment (input 0) (state 0 0)).mpr
    rw [exact 0 0 rowsPositive (by omega) widthPositive]
    rw [← CnfLiteral.truthValue_eq_true_iff_holds]
    cases inputZero : (input 0).truthValue assignment <;>
      simp [trueCountPrefix, inputZero]
  · intro row rowPositive rowBound
    apply (counterFirstColumnClauses_iff assignment
      (state (row - 1) 0) (input row) (state row 0)).mpr
    rw [exact row 0 rowBound (by omega) widthPositive]
    rw [exact (row - 1) 0 (by omega) (by omega) widthPositive]
    rw [← CnfLiteral.truthValue_eq_true_iff_holds]
    have previousLength : row - 1 + 1 = row := by omega
    rw [previousLength, trueCountPrefix]
    cases newValue : (input row).truthValue assignment <;>
      simp <;> omega
  · intro row rowPositive rowBound rowInsideWidth
    apply (counterDiagonalClauses_iff assignment
      (state (row - 1) (row - 1)) (input row) (state row row)).mpr
    rw [exact row row rowBound (by omega) rowInsideWidth]
    rw [exact (row - 1) (row - 1) (by omega) (by omega) (by omega)]
    rw [← CnfLiteral.truthValue_eq_true_iff_holds]
    have previousLength : row - 1 + 1 = row := by omega
    rw [previousLength, trueCountPrefix]
    have countBound := trueCountPrefix_le
      (fun k => (input k).truthValue assignment) row
    cases newValue : (input row).truthValue assignment <;>
      simp <;> omega
  · intro row column rowPositive rowBound columnPositive columnBeforeRow
      columnInsideWidth
    apply (counterInteriorClauses_iff assignment
      (state (row - 1) column) (state (row - 1) (column - 1))
      (input row) (state row column)).mpr
    rw [exact row column rowBound (by omega) columnInsideWidth]
    rw [exact (row - 1) column (by omega) (by omega) columnInsideWidth]
    rw [exact (row - 1) (column - 1) (by omega) (by omega) (by omega)]
    rw [← CnfLiteral.truthValue_eq_true_iff_holds]
    have previousLength : row - 1 + 1 = row := by omega
    rw [previousLength, trueCountPrefix]
    cases newValue : (input row).truthValue assignment <;>
      simp <;> omega

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

/-- The local cell bundle is also sufficient for the exact emitted row-major
counter formula. Together with `satisfiesSequentialCounterCells_of_exact`,
this supplies the previously missing completeness direction. -/
theorem satisfiesSequentialCounterCellFormula_of_cells {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (cells : SatisfiesSequentialCounterCells assignment input state
      rows width) :
    SatisfiesCnfFormula assignment
      (sequentialCounterCellFormula input state rows width) := by
  rcases cells with ⟨initialCell, firstCells, diagonalCells, interiorCells⟩
  intro clause membership
  simp only [sequentialCounterCellFormula, List.mem_flatMap,
    List.mem_range] at membership
  rcases membership with
    ⟨row, rowBound, column, columnBound, clauseMembership⟩
  have columnBeforeRowSucc : column < row + 1 :=
    (Nat.lt_min.mp columnBound).1
  have columnInsideWidth : column < width :=
    (Nat.lt_min.mp columnBound).2
  by_cases rowZero : row = 0
  · subst row
    have columnZero : column = 0 := by omega
    subst column
    exact initialCell clause (by
      simpa [sequentialCounterCellClauses] using clauseMembership)
  · have rowPositive : 0 < row := by omega
    by_cases columnZero : column = 0
    · subst column
      exact firstCells row rowPositive rowBound clause (by
        simpa [sequentialCounterCellClauses, rowZero] using clauseMembership)
    · have columnPositive : 0 < column := by omega
      by_cases columnLast : column = row
      · subst column
        exact diagonalCells row rowPositive rowBound columnInsideWidth clause
          (by simpa [sequentialCounterCellClauses, rowZero] using
            clauseMembership)
      · have columnBeforeRow : column < row := by omega
        exact interiorCells row column rowPositive rowBound columnPositive
          columnBeforeRow columnInsideWidth clause (by
            simpa [sequentialCounterCellClauses, rowZero, columnZero,
              columnLast] using clauseMembership)

theorem satisfiesSequentialCounterCellFormula_of_exact {variables : Nat}
    (assignment : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (state : Nat → Nat → CnfLiteral variables) (rows width : Nat)
    (rowsPositive : 0 < rows) (widthPositive : 0 < width)
    (exact : ∀ i j, i < rows → j ≤ i → j < width →
      ((state i j).Holds assignment ↔
        j + 1 ≤ trueCountPrefix
          (fun k => (input k).truthValue assignment) (i + 1))) :
    SatisfiesCnfFormula assignment
      (sequentialCounterCellFormula input state rows width) := by
  apply satisfiesSequentialCounterCellFormula_of_cells assignment input state
    rows width
  exact satisfiesSequentialCounterCells_of_exact assignment input state
    rows width rowsPositive widthPositive exact

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

/-- End-to-end completeness of the generated two-counter tail. Intended
truth values for both state grids, together with the numeric range and dense
sum facts, satisfy the two row-major counter streams and their entire
constraint suffix. -/
theorem satisfiesSequentialCounterPairEncoding_of_exact {variables : Nat}
    (assignment : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hRows hWidth jRows jWidth hCount jCount : Nat)
    (hLower hUpper jLower jUpper threshold : Nat)
    (hRowsPositive : 0 < hRows) (hWidthPositive : 0 < hWidth)
    (hWidthAtMostRows : hWidth ≤ hRows)
    (jRowsPositive : 0 < jRows) (jWidthPositive : 0 < jWidth)
    (jWidthAtMostRows : jWidth ≤ jRows)
    (hInputCount : sequentialCounterInputCount assignment hInput hRows = hCount)
    (jInputCount : sequentialCounterInputCount assignment jInput jRows = jCount)
    (hLowerPositive : 0 < hLower) (hOrdered : hLower ≤ hUpper)
    (hUpperInside : hUpper < hWidth)
    (jLowerPositive : 0 < jLower) (jOrdered : jLower ≤ jUpper)
    (jUpperInside : jUpper < jWidth)
    (hLowerBound : hLower ≤ hCount) (hUpperBound : hCount ≤ hUpper)
    (jLowerBound : jLower ≤ jCount) (jUpperBound : jCount ≤ jUpper)
    (dense : threshold ≤ hCount + jCount)
    (hExact : ∀ i j, i < hRows → j ≤ i → j < hWidth →
      ((hState i j).Holds assignment ↔
        j + 1 ≤ trueCountPrefix
          (fun k => (hInput k).truthValue assignment) (i + 1)))
    (jExact : ∀ i j, i < jRows → j ≤ i → j < jWidth →
      ((jState i j).Holds assignment ↔
        j + 1 ≤ trueCountPrefix
          (fun k => (jInput k).truthValue assignment) (i + 1))) :
    SatisfiesCnfFormula assignment
      (sequentialCounterCellFormula hInput hState hRows hWidth ++
        sequentialCounterCellFormula jInput jState jRows jWidth ++
        counterPairConstraintFormula (hState (hRows - 1))
          (jState (jRows - 1)) hWidth jWidth
          hLower hUpper jLower jUpper threshold) := by
  have hCells := satisfiesSequentialCounterCells_of_exact assignment hInput
    hState hRows hWidth hRowsPositive hWidthPositive hExact
  have jCells := satisfiesSequentialCounterCells_of_exact assignment jInput
    jState jRows jWidth jRowsPositive jWidthPositive jExact
  have hFormula := satisfiesSequentialCounterCellFormula_of_cells assignment
    hInput hState hRows hWidth hCells
  have jFormula := satisfiesSequentialCounterCellFormula_of_cells assignment
    jInput jState jRows jWidth jCells
  have hOutputs := satisfiesSequentialCounterCells_outputs_exact assignment
    hInput hState hRows hWidth hRowsPositive hWidthAtMostRows hCells
  have jOutputs := satisfiesSequentialCounterCells_outputs_exact assignment
    jInput jState jRows jWidth jRowsPositive jWidthAtMostRows jCells
  rw [hInputCount] at hOutputs
  rw [jInputCount] at jOutputs
  have constraints := satisfiesCounterPairConstraintFormula_of_bounds
    assignment (hState (hRows - 1)) (jState (jRows - 1))
    hWidth jWidth hCount jCount hLower hUpper jLower jUpper threshold
    hLowerPositive hOrdered hUpperInside jLowerPositive jOrdered jUpperInside
    hLowerBound hUpperBound jLowerBound jUpperBound dense hOutputs jOutputs
  intro clause membership
  simp only [List.mem_append] at membership
  rcases membership with counterMembership | constraintMembership
  · rcases counterMembership with hMembership | jMembership
    · exact hFormula clause hMembership
    · exact jFormula clause jMembership
  · exact constraints clause constraintMembership

#print axioms counterInitialClauses_iff
#print axioms counterFirstColumnClauses_iff
#print axioms counterDiagonalClauses_iff
#print axioms counterInteriorClauses_iff
#print axioms counterRangeClauses_bounds
#print axioms satisfiesCounterRangeClauses_of_bounds
#print axioms counterSumFormula_lower_bound
#print axioms satisfiesCounterSumFormula_of_lower_bound
#print axioms counterPairConstraintFormula_bounds
#print axioms satisfiesCounterPairConstraintFormula_of_bounds
#print axioms trueCountPrefix_le
#print axioms counterRecurrence_exact
#print axioms satisfiesSequentialCounterCells_of_exact
#print axioms satisfiesSequentialCounterCellFormula_of_cells
#print axioms satisfiesSequentialCounterCellFormula_of_exact
#print axioms satisfiesSequentialCounterCellFormula_cells
#print axioms satisfiesSequentialCounterSubformula_cells
#print axioms satisfiesSequentialCounterCells_exact
#print axioms satisfiesSequentialCounterCells_outputs_exact
#print axioms satisfiesSequentialCounterPairEncoding_of_exact

end Ramsey55
