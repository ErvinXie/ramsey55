import Ramsey55.Order45Primary

namespace Ramsey55

/-- Valid truncated sequential-counter cells in row-major order. -/
def counterCellCoordinates : Nat → Nat → List (Nat × Nat)
  | 0, _ => []
  | rows + 1, width =>
      counterCellCoordinates rows width ++
        (List.range (min (rows + 1) width)).map fun column => (rows, column)

theorem mem_counterCellCoordinates_bounds (rows width : Nat)
    (cell : Nat × Nat) (membership : cell ∈ counterCellCoordinates rows width) :
    cell.1 < rows ∧ cell.2 < min (cell.1 + 1) width := by
  induction rows with
  | zero => simp [counterCellCoordinates] at membership
  | succ rows inductionHypothesis =>
      simp only [counterCellCoordinates, List.mem_append, List.mem_map,
        List.mem_range] at membership
      rcases membership with previousMembership | rowMembership
      · have bounds := inductionHypothesis previousMembership
        exact ⟨by omega, bounds.2⟩
      · rcases rowMembership with ⟨column, columnBound, rfl⟩
        exact ⟨by omega, columnBound⟩

theorem mem_counterCellCoordinates (rows width row column : Nat)
    (rowBound : row < rows)
    (columnBound : column < min (row + 1) width) :
    (row, column) ∈ counterCellCoordinates rows width := by
  induction rows with
  | zero => omega
  | succ rows inductionHypothesis =>
      simp only [counterCellCoordinates, List.mem_append, List.mem_map,
        List.mem_range]
      by_cases lastRow : row = rows
      · right
        subst row
        exact ⟨column, columnBound, rfl⟩
      · left
        exact inductionHypothesis (by omega)

theorem counterCellCoordinates_nodup (rows width : Nat) :
    (counterCellCoordinates rows width).Nodup := by
  induction rows with
  | zero => simp [counterCellCoordinates]
  | succ rows inductionHypothesis =>
      simp only [counterCellCoordinates]
      apply nodup_append_of_nodup_of_disjoint
      · exact inductionHypothesis
      · apply nodup_map_of_injective (fun column => (rows, column))
        · intro first second equal
          have columnEqual := congrArg Prod.snd equal
          simpa using columnEqual
        · exact range_nodup_structural (min (rows + 1) width)
      · intro cell previousMembership rowMembership
        have previousBounds := mem_counterCellCoordinates_bounds rows width
          cell previousMembership
        simp only [List.mem_map, List.mem_range] at rowMembership
        rcases rowMembership with ⟨column, columnBound, cellEqual⟩
        have rowEqual := congrArg Prod.fst cellEqual
        simp at rowEqual
        omega

theorem counterCellsBefore_mono {width first second : Nat}
    (bounded : first ≤ second) :
    counterCellsBefore width first ≤ counterCellsBefore width second := by
  induction second generalizing first with
  | zero =>
      have : first = 0 := by omega
      subst first
      exact Nat.le_refl (counterCellsBefore width 0)
  | succ second inductionHypothesis =>
      by_cases equal : first = second + 1
      · subst first
        exact Nat.le_refl (counterCellsBefore width (second + 1))
      · have firstBounded : first ≤ second := by omega
        exact Nat.le_trans (inductionHypothesis firstBounded) (by
          simp only [counterCellsBefore]
          omega)

theorem counterStateDimacsVariable_injective_of_valid
    (base width : Nat) (first second : Nat × Nat)
    (firstValid : first.2 < min (first.1 + 1) width)
    (secondValid : second.2 < min (second.1 + 1) width)
    (equal : counterStateDimacsVariable base width first.1 first.2 =
      counterStateDimacsVariable base width second.1 second.2) :
    first = second := by
  change base + counterCellsBefore width first.1 + first.2 + 1 =
    base + counterCellsBefore width second.1 + second.2 + 1 at equal
  by_cases rowEqual : first.1 = second.1
  · rw [rowEqual] at equal
    have columnEqual : first.2 = second.2 := by omega
    apply Prod.ext <;> assumption
  · by_cases forward : first.1 < second.1
    · have firstUpper :
          base + counterCellsBefore width first.1 + first.2 + 1 ≤
            base + counterCellsBefore width (first.1 + 1) := by
          simp only [counterCellsBefore]
          omega
      have middle := counterCellsBefore_mono
        (width := width) (show first.1 + 1 ≤ second.1 by omega)
      have secondLower :
          base + counterCellsBefore width second.1 <
            base + counterCellsBefore width second.1 + second.2 + 1 := by omega
      omega
    · have reverse : second.1 < first.1 := by omega
      have secondUpper :
          base + counterCellsBefore width second.1 + second.2 + 1 ≤
            base + counterCellsBefore width (second.1 + 1) := by
          simp only [counterCellsBefore]
          omega
      have middle := counterCellsBefore_mono
        (width := width) (show second.1 + 1 ≤ first.1 by omega)
      have firstLower :
          base + counterCellsBefore width first.1 <
            base + counterCellsBefore width first.1 + first.2 + 1 := by omega
      omega

theorem counterCellIdentifiers_nodup (base rows width : Nat) :
    ((counterCellCoordinates rows width).map fun cell =>
      counterStateDimacsVariable base width cell.1 cell.2).Nodup := by
  apply nodup_map_of_nodup_of_injective_on_mem
  · exact counterCellCoordinates_nodup rows width
  · intro first firstMembership second secondMembership equal
    exact counterStateDimacsVariable_injective_of_valid base width first second
      (mem_counterCellCoordinates_bounds rows width first firstMembership).2
      (mem_counterCellCoordinates_bounds rows width second secondMembership).2
      equal

/-- Intended Boolean value of one counter state cell, evaluated from a fixed
source assignment for the input literals. -/
def intendedCounterStateValue {variables : Nat}
    (source : CnfAssignment variables)
    (input : Nat → CnfLiteral variables) (row column : Nat) : Bool :=
  decide (column + 1 ≤ trueCountPrefix
    (fun k => (input k).truthValue source) (row + 1))

def counterStateEntries {variables : Nat}
    (source : CnfAssignment variables)
    (input : Nat → CnfLiteral variables)
    (base rows width : Nat) : List (Nat × Bool) :=
  (counterCellCoordinates rows width).map fun cell =>
    (counterStateDimacsVariable base width cell.1 cell.2,
      intendedCounterStateValue source input cell.1 cell.2)

theorem counterStateEntryKeys_nodup {variables : Nat}
    (source : CnfAssignment variables)
    (input : Nat → CnfLiteral variables) (base rows width : Nat) :
    ((counterStateEntries source input base rows width).map Prod.fst).Nodup := by
  simpa [counterStateEntries, Function.comp_def] using
    counterCellIdentifiers_nodup base rows width

theorem counterStateEntry_mem {variables : Nat}
    (source : CnfAssignment variables)
    (input : Nat → CnfLiteral variables) (base rows width row column : Nat)
    (rowBound : row < rows)
    (columnBound : column < min (row + 1) width) :
    (counterStateDimacsVariable base width row column,
      intendedCounterStateValue source input row column) ∈
        counterStateEntries source input base rows width := by
  simp only [counterStateEntries, List.mem_map]
  exact ⟨(row, column),
    mem_counterCellCoordinates rows width row column rowBound columnBound, rfl⟩

theorem counterStateIdentifier_gt_base (base width row column : Nat) :
    base < counterStateDimacsVariable base width row column := by
  unfold counterStateDimacsVariable
  omega

theorem counterStateIdentifier_le_end (base rows width row column : Nat)
    (rowBound : row < rows)
    (columnBound : column < min (row + 1) width) :
    counterStateDimacsVariable base width row column ≤
      base + counterCellsBefore width rows := by
  have rowEnd :
      counterStateDimacsVariable base width row column ≤
        base + counterCellsBefore width (row + 1) := by
    unfold counterStateDimacsVariable
    simp only [counterCellsBefore]
    omega
  have later := counterCellsBefore_mono
    (width := width) (show row + 1 ≤ rows by omega)
  omega

theorem mem_counterStateEntryKey_bounds {variables : Nat}
    (source : CnfAssignment variables)
    (input : Nat → CnfLiteral variables) (base rows width identifier : Nat)
    (membership : identifier ∈
      (counterStateEntries source input base rows width).map Prod.fst) :
    base < identifier ∧
      identifier ≤ base + counterCellsBefore width rows := by
  simp only [counterStateEntries, List.map_map, Function.comp_def,
    List.mem_map] at membership
  rcases membership with ⟨cell, cellMembership, rfl⟩
  have bounds := mem_counterCellCoordinates_bounds rows width cell cellMembership
  exact ⟨counterStateIdentifier_gt_base base width cell.1 cell.2,
    counterStateIdentifier_le_end base rows width cell.1 cell.2
      bounds.1 bounds.2⟩

/-- Two disjoint sequential-counter state tables, both evaluated from the
same source assignment on their graph inputs. -/
def counterPairStateEntries {variables : Nat}
    (source : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hBase hRows hWidth jBase jRows jWidth : Nat) : List (Nat × Bool) :=
  counterStateEntries source hInput hBase hRows hWidth ++
    counterStateEntries source jInput jBase jRows jWidth

theorem counterPairStateEntryKeys_nodup {variables : Nat}
    (source : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase) :
    ((counterPairStateEntries source hInput jInput
      hBase hRows hWidth jBase jRows jWidth).map Prod.fst).Nodup := by
  simp only [counterPairStateEntries, List.map_append]
  apply nodup_append_of_nodup_of_disjoint
  · exact counterStateEntryKeys_nodup source hInput hBase hRows hWidth
  · exact counterStateEntryKeys_nodup source jInput jBase jRows jWidth
  · intro identifier hMembership jMembership
    have hBounds := mem_counterStateEntryKey_bounds source hInput
      hBase hRows hWidth identifier hMembership
    have jBounds := mem_counterStateEntryKey_bounds source jInput
      jBase jRows jWidth identifier jMembership
    omega

/-- Override a fallback assignment with a finite association list. -/
def assignmentWithEntries {variables : Nat}
    (fallback : CnfAssignment variables) (entries : List (Nat × Bool)) :
    CnfAssignment variables := fun index =>
  (List.lookup index.val entries).getD (fallback index)

theorem lookup_eq_none_of_not_mem_keys (identifier : Nat) :
    ∀ entries : List (Nat × Bool),
      identifier ∉ entries.map Prod.fst → List.lookup identifier entries = none := by
  intro entries
  induction entries with
  | nil => simp
  | cons head tail inductionHypothesis =>
      intro absent
      have headNe : identifier ≠ head.1 := by
        intro equal
        apply absent
        simp [equal]
      have tailAbsent : identifier ∉ tail.map Prod.fst := by
        intro membership
        apply absent
        simp [membership]
      have beqFalse : (identifier == head.1) = false :=
        beq_eq_false_iff_ne.mpr headNe
      simp [List.lookup, beqFalse, inductionHypothesis tailAbsent]

theorem assignmentWithEntries_eq_fallback_of_not_mem {variables : Nat}
    (fallback : CnfAssignment variables) (entries : List (Nat × Bool))
    (index : Fin variables) (absent : index.val ∉ entries.map Prod.fst) :
    assignmentWithEntries fallback entries index = fallback index := by
  unfold assignmentWithEntries
  rw [lookup_eq_none_of_not_mem_keys index.val entries absent]
  rfl

theorem assignmentWithEntries_eq_of_entry {variables : Nat}
    (fallback : CnfAssignment variables) (entries : List (Nat × Bool))
    (identifier : Nat) (value : Bool)
    (inside : identifier < variables)
    (nodup : (entries.map Prod.fst).Nodup)
    (membership : (identifier, value) ∈ entries) :
    assignmentWithEntries fallback entries ⟨identifier, inside⟩ = value := by
  have lookup := lookup_mapped_of_nodup Prod.fst Prod.snd entries
    (identifier, value) nodup membership
  have lookupDirect : List.lookup identifier entries = some value := by
    simpa using lookup
  simp [assignmentWithEntries, lookupDirect]

/-- A finite override containing the intended entry for every valid state
cell realizes those values at the direct-DIMACS literal indices. -/
theorem assignmentWithEntries_counterState_sourceExact
    (maximum base rows width : Nat)
    (source : CnfAssignment (maximum + 1))
    (input : Nat → CnfLiteral (maximum + 1))
    (entries : List (Nat × Bool))
    (endInside : base + counterCellsBefore width rows ≤ maximum)
    (nodup : (entries.map Prod.fst).Nodup)
    (contains : ∀ row column, row < rows →
      column < min (row + 1) width →
      (counterStateDimacsVariable base width row column,
        intendedCounterStateValue source input row column) ∈ entries) :
    ∀ row column, row < rows → column ≤ row → column < width →
      ((counterStateDimacsLiteral maximum base width row column).Holds
          (assignmentWithEntries source entries) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (input k).truthValue source) (row + 1)) := by
  intro row column rowBound columnInRow columnInsideWidth
  have columnBound : column < min (row + 1) width :=
    Nat.lt_min.mpr ⟨by omega, columnInsideWidth⟩
  have identifierInside :
      counterStateDimacsVariable base width row column < maximum + 1 := by
    have := counterStateIdentifier_le_end base rows width row column
      rowBound columnBound
    omega
  have value := assignmentWithEntries_eq_of_entry source entries
    (counterStateDimacsVariable base width row column)
    (intendedCounterStateValue source input row column)
    identifierInside nodup (contains row column rowBound columnBound)
  unfold CnfLiteral.Holds counterStateDimacsLiteral dimacsLiteral
  have finEqual :
      Fin.ofNat (maximum + 1)
          (counterStateDimacsVariable base width row column) =
        ⟨counterStateDimacsVariable base width row column,
          identifierInside⟩ := by
    apply Fin.ext
    simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside]
  rw [finEqual, value]
  simp [intendedCounterStateValue]

def assignmentWithCounterPairStates
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat) :
    CnfAssignment (maximum + 1) :=
  assignmentWithEntries source (counterPairStateEntries source hInput jInput
    hBase hRows hWidth jBase jRows jWidth)

theorem assignmentWithCounterPairStates_h_sourceExact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (jEndInside : jBase + counterCellsBefore jWidth jRows ≤ maximum) :
    ∀ row column, row < hRows → column ≤ row → column < hWidth →
      ((counterStateDimacsLiteral maximum hBase hWidth row column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (hInput k).truthValue source) (row + 1)) := by
  apply assignmentWithEntries_counterState_sourceExact maximum hBase hRows
    hWidth source hInput
    (counterPairStateEntries source hInput jInput
      hBase hRows hWidth jBase jRows jWidth)
  · omega
  · exact counterPairStateEntryKeys_nodup source hInput jInput
      hBase hRows hWidth jBase jRows jWidth separated
  · intro row column rowBound columnBound
    apply List.mem_append_left
    exact counterStateEntry_mem source hInput hBase hRows hWidth row column
      rowBound columnBound

theorem assignmentWithCounterPairStates_j_sourceExact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (jEndInside : jBase + counterCellsBefore jWidth jRows ≤ maximum) :
    ∀ row column, row < jRows → column ≤ row → column < jWidth →
      ((counterStateDimacsLiteral maximum jBase jWidth row column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (jInput k).truthValue source) (row + 1)) := by
  apply assignmentWithEntries_counterState_sourceExact maximum jBase jRows
    jWidth source jInput
    (counterPairStateEntries source hInput jInput
      hBase hRows hWidth jBase jRows jWidth)
  · exact jEndInside
  · exact counterPairStateEntryKeys_nodup source hInput jInput
      hBase hRows hWidth jBase jRows jWidth separated
  · intro row column rowBound columnBound
    apply List.mem_append_right
    exact counterStateEntry_mem source jInput jBase jRows jWidth row column
      rowBound columnBound

theorem assignmentWithCounterPairStates_eq_source_below_hBase
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (index : Fin (maximum + 1)) (below : index.val ≤ hBase) :
    assignmentWithCounterPairStates maximum source hInput jInput
        hBase hRows hWidth jBase jRows jWidth index = source index := by
  apply assignmentWithEntries_eq_fallback_of_not_mem
  intro membership
  simp only [counterPairStateEntries, List.map_append,
    List.mem_append] at membership
  rcases membership with hMembership | jMembership
  · have bounds := mem_counterStateEntryKey_bounds source hInput
      hBase hRows hWidth index.val hMembership
    omega
  · have bounds := mem_counterStateEntryKey_bounds source jInput
      jBase jRows jWidth index.val jMembership
    omega

theorem assignmentWithCounterPairStates_truthValue_eq_source
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (literal : CnfLiteral (maximum + 1))
    (below : literal.index.val ≤ hBase) :
    literal.truthValue (assignmentWithCounterPairStates maximum source
      hInput jInput hBase hRows hWidth jBase jRows jWidth) =
        literal.truthValue source := by
  unfold CnfLiteral.truthValue
  rw [assignmentWithCounterPairStates_eq_source_below_hBase maximum source
    hInput jInput hBase hRows hWidth jBase jRows jWidth separated
    literal.index below]

theorem assignmentWithCounterPairStates_h_exact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (jEndInside : jBase + counterCellsBefore jWidth jRows ≤ maximum)
    (hInputBelow : ∀ k, (hInput k).index.val ≤ hBase) :
    ∀ row column, row < hRows → column ≤ row → column < hWidth →
      ((counterStateDimacsLiteral maximum hBase hWidth row column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (hInput k).truthValue
            (assignmentWithCounterPairStates maximum source hInput jInput
              hBase hRows hWidth jBase jRows jWidth)) (row + 1)) := by
  intro row column rowBound columnInRow columnInsideWidth
  have sourceExact := assignmentWithCounterPairStates_h_sourceExact maximum
    source hInput jInput hBase hRows hWidth jBase jRows jWidth separated
    jEndInside row column rowBound columnInRow columnInsideWidth
  have preserved (k : Nat) := assignmentWithCounterPairStates_truthValue_eq_source
    maximum source hInput jInput hBase hRows hWidth jBase jRows jWidth
    separated (hInput k) (hInputBelow k)
  simpa [preserved] using sourceExact

theorem assignmentWithCounterPairStates_j_exact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (jEndInside : jBase + counterCellsBefore jWidth jRows ≤ maximum)
    (jInputBelow : ∀ k, (jInput k).index.val ≤ hBase) :
    ∀ row column, row < jRows → column ≤ row → column < jWidth →
      ((counterStateDimacsLiteral maximum jBase jWidth row column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (jInput k).truthValue
            (assignmentWithCounterPairStates maximum source hInput jInput
              hBase hRows hWidth jBase jRows jWidth)) (row + 1)) := by
  intro row column rowBound columnInRow columnInsideWidth
  have sourceExact := assignmentWithCounterPairStates_j_sourceExact maximum
    source hInput jInput hBase hRows hWidth jBase jRows jWidth separated
    jEndInside row column rowBound columnInRow columnInsideWidth
  have preserved (k : Nat) := assignmentWithCounterPairStates_truthValue_eq_source
    maximum source hInput jInput hBase hRows hWidth jBase jRows jWidth
    separated (jInput k) (jInputBelow k)
  simpa [preserved] using sourceExact

theorem order45CounterInput_index_le_990
    (maximum start count : Nat) (positive : Bool)
    (within : start + count ≤ 45) (enough : 990 ≤ maximum) (row : Nat) :
    (counterInputDimacsLiteral maximum
      ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
      positive row).index.val ≤ 990 := by
  by_cases inside : row < (orderedPairsFrom start count).length
  · rw [counterInputDimacsLiteral_eq_getElem maximum
      ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
      positive row (by simpa using inside)]
    let pair := (orderedPairsFrom start count)[row]
    have pairMembership : pair ∈ orderedPairsFrom start count :=
      List.getElem_mem inside
    have bounds := mem_orderedPairsFrom_bounds start count pair pairMembership
    have identifierBound : orderedEdgeDimacsVariable pair ≤ 990 := by
      simpa only [Prod.eta] using
        (orderedEdgeDimacsVariable_le_990 pair.1 pair.2
          bounds.2.1 (by omega))
    have identifierInside : orderedEdgeDimacsVariable pair < maximum + 1 := by
      omega
    unfold dimacsLiteral
    simpa [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside, pair] using
      identifierBound
  · simp [counterInputDimacsLiteral, List.getD_eq_getElem?_getD, inside,
      dimacsLiteral]

theorem assignmentWithCounterPairStates_inputCount_eq_source
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput input : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth inputRows : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (inputBelow : ∀ k, (input k).index.val ≤ hBase) :
    sequentialCounterInputCount
        (assignmentWithCounterPairStates maximum source hInput jInput
          hBase hRows hWidth jBase jRows jWidth) input inputRows =
      sequentialCounterInputCount source input inputRows := by
  unfold sequentialCounterInputCount
  congr 1
  funext k
  exact assignmentWithCounterPairStates_truthValue_eq_source maximum source
    hInput jInput hBase hRows hWidth jBase jRows jWidth separated
    (input k) (inputBelow k)

theorem assignmentWithCounterPairStates_satisfies_encoding
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth hCount jCount : Nat)
    (hLower hUpper jLower jUpper threshold : Nat)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (jEndInside : jBase + counterCellsBefore jWidth jRows ≤ maximum)
    (hInputBelow : ∀ k, (hInput k).index.val ≤ hBase)
    (jInputBelow : ∀ k, (jInput k).index.val ≤ hBase)
    (hRowsPositive : 0 < hRows) (hWidthPositive : 0 < hWidth)
    (hWidthAtMostRows : hWidth ≤ hRows)
    (jRowsPositive : 0 < jRows) (jWidthPositive : 0 < jWidth)
    (jWidthAtMostRows : jWidth ≤ jRows)
    (hSourceCount : sequentialCounterInputCount source hInput hRows = hCount)
    (jSourceCount : sequentialCounterInputCount source jInput jRows = jCount)
    (hLowerPositive : 0 < hLower) (hOrdered : hLower ≤ hUpper)
    (hUpperInside : hUpper < hWidth)
    (jLowerPositive : 0 < jLower) (jOrdered : jLower ≤ jUpper)
    (jUpperInside : jUpper < jWidth)
    (hLowerBound : hLower ≤ hCount) (hUpperBound : hCount ≤ hUpper)
    (jLowerBound : jLower ≤ jCount) (jUpperBound : jCount ≤ jUpper)
    (dense : threshold ≤ hCount + jCount) :
    SatisfiesCnfFormula
      (assignmentWithCounterPairStates maximum source hInput jInput
        hBase hRows hWidth jBase jRows jWidth)
      (sequentialCounterCellFormula hInput
          (counterStateDimacsLiteral maximum hBase hWidth) hRows hWidth ++
        sequentialCounterCellFormula jInput
          (counterStateDimacsLiteral maximum jBase jWidth) jRows jWidth ++
        counterPairConstraintFormula
          (counterStateDimacsLiteral maximum hBase hWidth (hRows - 1))
          (counterStateDimacsLiteral maximum jBase jWidth (jRows - 1))
          hWidth jWidth hLower hUpper jLower jUpper threshold) := by
  let assignment := assignmentWithCounterPairStates maximum source
    hInput jInput hBase hRows hWidth jBase jRows jWidth
  apply satisfiesSequentialCounterPairEncoding_of_exact assignment
    hInput jInput
    (counterStateDimacsLiteral maximum hBase hWidth)
    (counterStateDimacsLiteral maximum jBase jWidth)
    hRows hWidth jRows jWidth hCount jCount
    hLower hUpper jLower jUpper threshold
    hRowsPositive hWidthPositive hWidthAtMostRows
    jRowsPositive jWidthPositive jWidthAtMostRows
  · exact (assignmentWithCounterPairStates_inputCount_eq_source maximum source
      hInput jInput hInput hBase hRows hWidth jBase jRows jWidth hRows
      separated hInputBelow).trans hSourceCount
  · exact (assignmentWithCounterPairStates_inputCount_eq_source maximum source
      hInput jInput jInput hBase hRows hWidth jBase jRows jWidth jRows
      separated jInputBelow).trans jSourceCount
  · exact hLowerPositive
  · exact hOrdered
  · exact hUpperInside
  · exact jLowerPositive
  · exact jOrdered
  · exact jUpperInside
  · exact hLowerBound
  · exact hUpperBound
  · exact jLowerBound
  · exact jUpperBound
  · exact dense
  · exact assignmentWithCounterPairStates_h_exact maximum source hInput jInput
      hBase hRows hWidth jBase jRows jWidth separated jEndInside hInputBelow
  · exact assignmentWithCounterPairStates_j_exact maximum source hInput jInput
      hBase hRows hWidth jBase jRows jWidth separated jEndInside jInputBelow

def order45Degree20CounterAssignment (color : Coloring 45) :
    CnfAssignment (78697 + 1) :=
  assignmentWithCounterPairStates 78697
    (order45GraphPrimaryAssignment 78697 color)
    order45Degree20HInput order45Degree20JInput
    36627 190 101 50767 276 133

set_option maxRecDepth 100000 in
theorem order45Degree20CounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 20) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree20CounterAssignment color)
      order45Degree20CounterTail := by
  have sourceCounts := order45Degree20GraphPrimaryInputCounts color simple
    fixed edgesH edgesJ counts
  have hInputBelow : ∀ k, (order45Degree20HInput k).index.val ≤ 36627 := by
    intro k
    have bound := order45CounterInput_index_le_990 78697 1 20 true
      (by omega) (by omega) k
    have concrete : (order45Degree20HInput k).index.val ≤ 990 := by
      simpa [order45Degree20HInput, order45HInputIdentifiers] using bound
    omega
  have jInputBelow : ∀ k, (order45Degree20JInput k).index.val ≤ 36627 := by
    intro k
    have bound := order45CounterInput_index_le_990 78697 21 24 false
      (by omega) (by omega) k
    have concrete : (order45Degree20JInput k).index.val ≤ 990 := by
      simpa [order45Degree20JInput, order45JInputIdentifiers] using bound
    omega
  simpa [order45Degree20CounterAssignment, order45Degree20CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 78697
      (order45GraphPrimaryAssignment 78697 color)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133 edgesH edgesJ
      68 100 116 132 226
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

def order45Degree21CounterAssignment (color : Coloring 45) :
    CnfAssignment (77148 + 1) :=
  assignmentWithCounterPairStates 77148
    (order45GraphPrimaryAssignment 77148 color)
    order45Degree21HInput order45Degree21JInput
    36630 210 108 53532 253 123

set_option maxRecDepth 100000 in
theorem order45Degree21CounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 21) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree21CounterAssignment color)
      order45Degree21CounterTail := by
  have sourceCounts := order45Degree21GraphPrimaryInputCounts color simple
    fixed edgesH edgesJ counts
  have hInputBelow : ∀ k, (order45Degree21HInput k).index.val ≤ 36630 := by
    intro k
    have bound := order45CounterInput_index_le_990 77148 1 21 true
      (by omega) (by omega) k
    have concrete : (order45Degree21HInput k).index.val ≤ 990 := by
      simpa [order45Degree21HInput, order45HInputIdentifiers] using bound
    omega
  have jInputBelow : ∀ k, (order45Degree21JInput k).index.val ≤ 36630 := by
    intro k
    have bound := order45CounterInput_index_le_990 77148 22 23 false
      (by omega) (by omega) k
    have concrete : (order45Degree21JInput k).index.val ≤ 990 := by
      simpa [order45Degree21JInput, order45JInputIdentifiers] using bound
    omega
  simpa [order45Degree21CounterAssignment, order45Degree21CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 77148
      (order45GraphPrimaryAssignment 77148 color)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123 edgesH edgesJ
      77 107 101 122 222
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

def order45Degree22CounterAssignment (color : Coloring 45) :
    CnfAssignment (76651 + 1) :=
  assignmentWithCounterPairStates 76651
    (order45GraphPrimaryAssignment 76651 color)
    order45Degree22HInput order45Degree22JInput
    36631 231 115 56641 231 115

set_option maxRecDepth 100000 in
theorem order45Degree22CounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 22) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree22CounterAssignment color)
      order45Degree22CounterTail := by
  have sourceCounts := order45Degree22GraphPrimaryInputCounts color simple
    fixed edgesH edgesJ counts
  have hInputBelow : ∀ k, (order45Degree22HInput k).index.val ≤ 36631 := by
    intro k
    have bound := order45CounterInput_index_le_990 76651 1 22 true
      (by omega) (by omega) k
    have concrete : (order45Degree22HInput k).index.val ≤ 990 := by
      simpa [order45Degree22HInput, order45HInputIdentifiers] using bound
    omega
  have jInputBelow : ∀ k, (order45Degree22JInput k).index.val ≤ 36631 := by
    intro k
    have bound := order45CounterInput_index_le_990 76651 23 22 false
      (by omega) (by omega) k
    have concrete : (order45Degree22JInput k).index.val ≤ 990 := by
      simpa [order45Degree22JInput, order45JInputIdentifiers] using bound
    omega
  simpa [order45Degree22CounterAssignment, order45Degree22CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 76651
      (order45GraphPrimaryAssignment 76651 color)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115 edgesH edgesJ
      88 114 88 114 220
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

#print axioms counterCellCoordinates_nodup
#print axioms counterCellIdentifiers_nodup
#print axioms counterStateEntryKeys_nodup
#print axioms counterPairStateEntryKeys_nodup
#print axioms assignmentWithEntries_eq_of_entry
#print axioms assignmentWithEntries_counterState_sourceExact
#print axioms assignmentWithCounterPairStates_h_sourceExact
#print axioms assignmentWithCounterPairStates_j_sourceExact
#print axioms assignmentWithCounterPairStates_eq_source_below_hBase
#print axioms assignmentWithCounterPairStates_h_exact
#print axioms assignmentWithCounterPairStates_j_exact
#print axioms order45CounterInput_index_le_990
#print axioms assignmentWithCounterPairStates_inputCount_eq_source
#print axioms assignmentWithCounterPairStates_satisfies_encoding
#print axioms order45Degree20CounterTail_satisfied
#print axioms order45Degree21CounterTail_satisfied
#print axioms order45Degree22CounterTail_satisfied

end Ramsey55
