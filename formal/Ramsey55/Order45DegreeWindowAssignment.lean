import Ramsey55.Order45MotherPrefix

namespace Ramsey55

/-- Remove one Boolean position while retaining the original order. -/
def skipBoolPosition (input : Nat → Bool) (skip row : Nat) : Bool :=
  if row < skip then input row else input (row + 1)

theorem trueCountPrefix_congr (first second : Nat → Bool) :
    ∀ length : Nat, (∀ index, index < length → first index = second index) →
      trueCountPrefix first length = trueCountPrefix second length := by
  intro length
  induction length with
  | zero => simp [trueCountPrefix]
  | succ length inductionHypothesis =>
      intro equal
      simp only [trueCountPrefix]
      rw [inductionHypothesis (fun index inside => equal index (by omega)),
        equal length (by omega)]

theorem trueCountPrefix_skip_false (input : Nat → Bool) :
    ∀ length skip : Nat, skip < length + 1 → input skip = false →
      trueCountPrefix (skipBoolPosition input skip) length =
        trueCountPrefix input (length + 1) := by
  intro length
  induction length with
  | zero =>
      intro skip skipBound skippedFalse
      have skipZero : skip = 0 := by omega
      subst skip
      simp [trueCountPrefix, skippedFalse]
  | succ length inductionHypothesis =>
      intro skip skipBound skippedFalse
      by_cases skipLast : skip = length + 1
      · subst skip
        have prefixEqual :
            trueCountPrefix (skipBoolPosition input (length + 1))
                (length + 1) =
              trueCountPrefix input (length + 1) := by
          apply trueCountPrefix_congr
          intro index inside
          simp [skipBoolPosition, show index < length + 1 by omega]
        exact prefixEqual.trans (by
          simp [trueCountPrefix, skippedFalse])
      · have earlier : skip < length + 1 := by omega
        have lastValue :
            skipBoolPosition input skip length = input (length + 1) := by
          simp [skipBoolPosition, show ¬length < skip by omega]
        simp only [trueCountPrefix]
        rw [inductionHypothesis skip earlier skippedFalse, lastValue]
        rfl

/-- Natural-label view of one row, totalized outside order 45. -/
def order45NaturalRow (color : Coloring 45) (vertex : Fin 45) (index : Nat) :
    Bool :=
  if inside : index < 45 then color vertex ⟨index, inside⟩ else false

theorem trueCountPrefix_order45NaturalRow_eq_degree
    (color : Coloring 45) (vertex : Fin 45) :
    trueCountPrefix (order45NaturalRow color vertex) 45 =
      coloringDegree color vertex := by
  rw [trueCountPrefix_eq_sum_ofFn, coloringDegree,
    coloringDegreeUpTo_eq_listPrefix]
  congr 1

/-- Row `0..43` enumerates labels `0..44` with `vertex` removed. -/
def order45VertexOther (vertex row : Nat) : Nat :=
  if row < vertex then row else row + 1

theorem order45VertexOther_inside (vertex row : Nat)
    (_vertexInside : vertex < 45) (rowInside : row < 44) :
    order45VertexOther vertex row < 45 := by
  unfold order45VertexOther
  split <;> omega

theorem order45VertexOther_ne (vertex row : Nat) :
    order45VertexOther vertex row ≠ vertex := by
  unfold order45VertexOther
  split <;> omega

def order45UnorderedEdgeDimacsVariable (left right : Nat) : Nat :=
  if left < right then orderedEdgeDimacsVariable (left, right)
  else orderedEdgeDimacsVariable (right, left)

/-- The exact incident-edge order used by
`degree_bound_clauses`: increasing `other`, omitting `vertex`. -/
def order45VertexDegreeInput (maximum vertex row : Nat) :
    CnfLiteral (maximum + 1) :=
  dimacsLiteral maximum
    (order45UnorderedEdgeDimacsVariable vertex
      (order45VertexOther vertex row)) true

theorem order45VertexDegreeInput_truthValue
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (vertex row : Nat) (_vertexPositive : 0 < vertex)
    (vertexInside : vertex < 45) (rowInside : row < 44) :
    (order45VertexDegreeInput maximum vertex row).truthValue assignment =
      order45NaturalRow color ⟨vertex, vertexInside⟩
        (order45VertexOther vertex row) := by
  by_cases before : row < vertex
  · have represented := represents row vertex before vertexInside
    rw [show order45VertexDegreeInput maximum vertex row =
        dimacsLiteral maximum (orderedEdgeDimacsVariable (row, vertex)) true by
      simp [order45VertexDegreeInput, order45UnorderedEdgeDimacsVariable,
        order45VertexOther, before, show ¬vertex < row by omega]]
    rw [represented]
    simp [order45NaturalRow, order45NatColor, order45VertexOther, before,
      vertexInside, simple.2]
  · have ordered : vertex < row + 1 := by omega
    have represented := represents vertex (row + 1) ordered (by omega)
    rw [show order45VertexDegreeInput maximum vertex row =
        dimacsLiteral maximum
          (orderedEdgeDimacsVariable (vertex, row + 1)) true by
      simp [order45VertexDegreeInput, order45UnorderedEdgeDimacsVariable,
        order45VertexOther, before, ordered]]
    rw [represented]
    simp [order45NaturalRow, order45NatColor, order45VertexOther, before,
      vertexInside]

theorem order45VertexDegreeInputCount
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (vertex : Nat) (vertexPositive : 0 < vertex)
    (vertexInside : vertex < 45) :
    sequentialCounterInputCount assignment
        (order45VertexDegreeInput maximum vertex) 44 =
      coloringDegree color ⟨vertex, vertexInside⟩ := by
  unfold sequentialCounterInputCount
  rw [trueCountPrefix_congr
    (fun row => (order45VertexDegreeInput maximum vertex row).truthValue
      assignment)
    (skipBoolPosition
      (order45NaturalRow color ⟨vertex, vertexInside⟩) vertex) 44]
  · rw [trueCountPrefix_skip_false
      (order45NaturalRow color ⟨vertex, vertexInside⟩) 44 vertex
      (by omega)]
    · exact trueCountPrefix_order45NaturalRow_eq_degree color
        ⟨vertex, vertexInside⟩
    · unfold order45NaturalRow
      simp only [dif_pos vertexInside]
      exact simple.1 ⟨vertex, vertexInside⟩
  · intro row rowInside
    rw [order45VertexDegreeInput_truthValue maximum assignment color simple
      represents vertex row vertexPositive vertexInside rowInside]
    by_cases before : row < vertex <;>
      simp [skipBoolPosition, order45VertexOther, before]

theorem counterCellsBefore_25_44 : counterCellsBefore 25 44 = 800 := by
  decide

/-- The 44 degree counters occupy one contiguous 800-variable block per
vertex.  `count` includes vertices `1, ..., count`, matching the generator. -/
def order45DegreeStateEntries {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) : Nat → List (Nat × Bool)
  | 0 => []
  | count + 1 =>
      order45DegreeStateEntries source count ++
        counterStateEntries source
          (order45VertexDegreeInput maximum (count + 1))
          (990 + count * 800) 44 25

set_option maxRecDepth 100000 in
theorem mem_order45DegreeStateEntryKey_bounds {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) (count identifier : Nat)
    (membership : identifier ∈
      (order45DegreeStateEntries source count).map Prod.fst) :
    990 < identifier ∧ identifier ≤ 990 + count * 800 := by
  induction count with
  | zero => simp [order45DegreeStateEntries] at membership
  | succ count inductionHypothesis =>
      simp only [order45DegreeStateEntries, List.map_append,
        List.mem_append] at membership
      rcases membership with previousMembership | currentMembership
      · have bounds := inductionHypothesis previousMembership
        omega
      · have bounds := mem_counterStateEntryKey_bounds source
          (order45VertexDegreeInput maximum (count + 1))
          (990 + count * 800) 44 25 identifier currentMembership
        rw [counterCellsBefore_25_44] at bounds
        omega

set_option maxRecDepth 100000 in
theorem order45DegreeStateEntryKeys_nodup {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) (count : Nat) :
    ((order45DegreeStateEntries source count).map Prod.fst).Nodup := by
  induction count with
  | zero => simp [order45DegreeStateEntries]
  | succ count inductionHypothesis =>
      simp only [order45DegreeStateEntries, List.map_append]
      apply nodup_append_of_nodup_of_disjoint
      · exact inductionHypothesis
      · exact counterStateEntryKeys_nodup source
          (order45VertexDegreeInput maximum (count + 1))
          (990 + count * 800) 44 25
      · intro identifier previousMembership currentMembership
        have previousBounds := mem_order45DegreeStateEntryKey_bounds source
          count identifier previousMembership
        have currentBounds := mem_counterStateEntryKey_bounds source
          (order45VertexDegreeInput maximum (count + 1))
          (990 + count * 800) 44 25 identifier currentMembership
        omega

set_option maxRecDepth 100000 in
theorem order45DegreeStateEntry_mem {maximum : Nat}
    (source : CnfAssignment (maximum + 1))
    (count index row column : Nat) (indexBound : index < count)
    (rowBound : row < 44) (columnBound : column < min (row + 1) 25) :
    (counterStateDimacsVariable (990 + index * 800) 25 row column,
      intendedCounterStateValue source
        (order45VertexDegreeInput maximum (index + 1)) row column) ∈
      order45DegreeStateEntries source count := by
  induction count with
  | zero => omega
  | succ count inductionHypothesis =>
      simp only [order45DegreeStateEntries, List.mem_append]
      by_cases last : index = count
      · right
        subst index
        exact counterStateEntry_mem source
          (order45VertexDegreeInput maximum (count + 1))
          (990 + count * 800) 44 25 row column rowBound columnBound
      · left
        exact inductionHypothesis (by omega)

/-- Override the primary graph assignment with all 44 intended degree-counter
state tables.  Their exact identifier interval is `991..36190`. -/
def order45DegreeWindowAssignment (maximum : Nat)
    (source : CnfAssignment (maximum + 1)) : CnfAssignment (maximum + 1) :=
  assignmentWithEntries source (order45DegreeStateEntries source 44)

theorem order45DegreeWindowAssignment_eq_source_below_990
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (index : Fin (maximum + 1)) (below : index.val ≤ 990) :
    order45DegreeWindowAssignment maximum source index = source index := by
  apply assignmentWithEntries_eq_fallback_of_not_mem
  intro membership
  have bounds := mem_order45DegreeStateEntryKey_bounds source 44 index.val
    membership
  omega

theorem order45UnorderedEdgeDimacsVariable_le_990 (left right : Nat)
    (leftInside : left < 45) (rightInside : right < 45)
    (different : left ≠ right) :
    order45UnorderedEdgeDimacsVariable left right ≤ 990 := by
  unfold order45UnorderedEdgeDimacsVariable
  split
  · exact orderedEdgeDimacsVariable_le_990 left right (by assumption)
      rightInside
  · exact orderedEdgeDimacsVariable_le_990 right left (by omega) leftInside

theorem order45VertexDegreeInput_index_le_990
    (maximum vertex row : Nat) (maximumEnough : 990 ≤ maximum)
    (vertexInside : vertex < 45) (rowInside : row < 44) :
    (order45VertexDegreeInput maximum vertex row).index.val ≤ 990 := by
  have otherInside := order45VertexOther_inside vertex row vertexInside rowInside
  have identifierBound := order45UnorderedEdgeDimacsVariable_le_990 vertex
    (order45VertexOther vertex row) vertexInside otherInside
    (Ne.symm (order45VertexOther_ne vertex row))
  have identifierInside :
      order45UnorderedEdgeDimacsVariable vertex
        (order45VertexOther vertex row) < maximum + 1 := by
    omega
  unfold order45VertexDegreeInput dimacsLiteral
  simpa [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside] using
    identifierBound

def order45DegreeCounterState (maximum index row column : Nat) :
    CnfLiteral (maximum + 1) :=
  counterStateDimacsLiteral maximum (990 + index * 800) 25 row column

def order45DegreeCounterOutput (maximum index thresholdIndex : Nat) :
    CnfLiteral (maximum + 1) :=
  order45DegreeCounterState maximum index 43 thresholdIndex

set_option maxRecDepth 100000 in
theorem order45DegreeWindowAssignment_sourceExact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (endInside : 36190 ≤ maximum) (index : Nat) (indexBound : index < 44) :
    ∀ row column, row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum index row column).Holds
          (order45DegreeWindowAssignment maximum source) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            source) (row + 1)) := by
  unfold order45DegreeCounterState order45DegreeWindowAssignment
  apply assignmentWithEntries_counterState_sourceExact maximum
    (990 + index * 800) 44 25 source
    (order45VertexDegreeInput maximum (index + 1))
    (order45DegreeStateEntries source 44)
  · rw [counterCellsBefore_25_44]
    omega
  · exact order45DegreeStateEntryKeys_nodup source 44
  · intro row column rowBound columnBound
    exact order45DegreeStateEntry_mem source 44 index row column indexBound
      rowBound columnBound

set_option maxRecDepth 100000 in
theorem order45DegreeWindowAssignment_exact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (endInside : 36190 ≤ maximum) (index : Nat) (indexBound : index < 44) :
    ∀ row column, row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum index row column).Holds
          (order45DegreeWindowAssignment maximum source) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            (order45DegreeWindowAssignment maximum source)) (row + 1)) := by
  intro row column rowBound columnInRow columnInsideWidth
  have sourceExact := order45DegreeWindowAssignment_sourceExact maximum source
    endInside index indexBound row column rowBound columnInRow
    columnInsideWidth
  have countEqual :
      trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            (order45DegreeWindowAssignment maximum source)) (row + 1) =
        trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            source) (row + 1) := by
    apply trueCountPrefix_congr
    intro k kInside
    unfold CnfLiteral.truthValue
    rw [order45DegreeWindowAssignment_eq_source_below_990 maximum source
      (order45VertexDegreeInput maximum (index + 1) k).index]
    exact order45VertexDegreeInput_index_le_990 maximum (index + 1) k
      (by omega) (by omega) (by omega)
  rw [countEqual]
  exact sourceExact

theorem order45DegreeCounterCellFormula_satisfied
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (endInside : 36190 ≤ maximum) (index : Nat) (indexBound : index < 44) :
    SatisfiesCnfFormula (order45DegreeWindowAssignment maximum source)
      (sequentialCounterCellFormula
        (order45VertexDegreeInput maximum (index + 1))
        (order45DegreeCounterState maximum index) 44 25) := by
  apply satisfiesSequentialCounterCellFormula_of_exact
  · omega
  · omega
  · exact order45DegreeWindowAssignment_exact maximum source endInside index
      indexBound

theorem order45DegreeWindowAssignment_represents_primary
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum source color)
    (maximumEnough : 990 ≤ maximum) :
    RepresentsOrder45Primary maximum
      (order45DegreeWindowAssignment maximum source) color := by
  intro left right ordered inside
  have identifierBound := orderedEdgeDimacsVariable_le_990 left right ordered
    inside
  have identifierInside :
      orderedEdgeDimacsVariable (left, right) < maximum + 1 := by omega
  have preserved := order45DegreeWindowAssignment_eq_source_below_990 maximum
    source
    (dimacsLiteral maximum (orderedEdgeDimacsVariable (left, right)) true).index
    (by
      unfold dimacsLiteral
      simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside,
        identifierBound])
  unfold CnfLiteral.truthValue
  rw [preserved]
  exact represents left right ordered inside

set_option maxRecDepth 100000 in
theorem order45DegreeCounterOutputs_exact
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum source color)
    (endInside : 36190 ≤ maximum) (index : Nat) (indexBound : index < 44) :
    ExactAtLeastCounterOutputs
      (order45DegreeWindowAssignment maximum source)
      (order45DegreeCounterOutput maximum index) 25
      (coloringDegree color ⟨index + 1, by omega⟩) := by
  intro thresholdIndex thresholdInside
  have cellExact := order45DegreeWindowAssignment_exact maximum source
    endInside index indexBound 43 thresholdIndex (by omega) (by omega)
    thresholdInside
  have assignmentRepresents :=
    order45DegreeWindowAssignment_represents_primary maximum source color
      represents (by omega)
  have inputCount := order45VertexDegreeInputCount maximum
    (order45DegreeWindowAssignment maximum source) color simple
    assignmentRepresents (index + 1) (by omega) (by omega)
  unfold sequentialCounterInputCount at inputCount
  rw [inputCount] at cellExact
  simpa [order45DegreeCounterOutput] using cellExact

def order45DegreeCounterFormula (maximum index : Nat) :
    CnfFormula (maximum + 1) :=
  sequentialCounterCellFormula
      (order45VertexDegreeInput maximum (index + 1))
      (order45DegreeCounterState maximum index) 44 25 ++
    counterRangeClauses (order45DegreeCounterOutput maximum index) 20 24

set_option maxRecDepth 100000 in
theorem order45DegreeCounterFormula_satisfied
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum source color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (endInside : 36190 ≤ maximum) (index : Nat) (indexBound : index < 44) :
    SatisfiesCnfFormula (order45DegreeWindowAssignment maximum source)
      (order45DegreeCounterFormula maximum index) := by
  have cells := order45DegreeCounterCellFormula_satisfied maximum source
    endInside index indexBound
  have bounds := window ⟨index + 1, by omega⟩
  have range := satisfiesCounterRangeClauses_of_bounds
    (order45DegreeWindowAssignment maximum source)
    (order45DegreeCounterOutput maximum index) 25
    (coloringDegree color ⟨index + 1, by omega⟩) 20 24
    (by omega) (by omega) (by omega) bounds.1 bounds.2
    (order45DegreeCounterOutputs_exact maximum source color simple represents
      endInside index indexBound)
  intro clause membership
  simp only [order45DegreeCounterFormula, List.mem_append] at membership
  rcases membership with cellMembership | rangeMembership
  · exact cells clause cellMembership
  · exact range clause rangeMembership

/-- Exact concatenation order of all degree encodings emitted for vertices
`1..count`. -/
def order45DegreeWindowFormula (maximum : Nat) : Nat →
    CnfFormula (maximum + 1)
  | 0 => []
  | count + 1 =>
      order45DegreeWindowFormula maximum count ++
        order45DegreeCounterFormula maximum count

set_option maxRecDepth 100000 in
theorem order45DegreeWindowFormula_satisfied_upTo
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum source color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (endInside : 36190 ≤ maximum) :
    ∀ count : Nat, count ≤ 44 →
      SatisfiesCnfFormula (order45DegreeWindowAssignment maximum source)
        (order45DegreeWindowFormula maximum count) := by
  intro count countBound
  induction count with
  | zero => simp [order45DegreeWindowFormula, SatisfiesCnfFormula]
  | succ count inductionHypothesis =>
      have previous := inductionHypothesis (by omega)
      have current := order45DegreeCounterFormula_satisfied maximum source color
        simple represents window endInside count (by omega)
      intro clause membership
      simp only [order45DegreeWindowFormula, List.mem_append] at membership
      rcases membership with previousMembership | currentMembership
      · exact previous clause previousMembership
      · exact current clause currentMembership

theorem order45DegreeWindowFormula_satisfied
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum source color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (endInside : 36190 ≤ maximum) :
    SatisfiesCnfFormula (order45DegreeWindowAssignment maximum source)
      (order45DegreeWindowFormula maximum 44) := by
  exact order45DegreeWindowFormula_satisfied_upTo maximum source color simple
    represents window endInside 44 (Nat.le_refl 44)

/-- Concrete degree-window extension of the canonical graph assignment. -/
def order45GraphDegreeWindowAssignment (maximum : Nat)
    (color : Coloring 45) : CnfAssignment (maximum + 1) :=
  order45DegreeWindowAssignment maximum
    (order45GraphPrimaryAssignment maximum color)

theorem order45GraphDegreeWindowAssignment_represents
    (maximum : Nat) (enough : 36190 ≤ maximum) (color : Coloring 45) :
    RepresentsOrder45Primary maximum
      (order45GraphDegreeWindowAssignment maximum color) color := by
  apply order45DegreeWindowAssignment_represents_primary maximum
    (order45GraphPrimaryAssignment maximum color) color
  · exact order45GraphPrimaryAssignment_represents maximum (by omega) color
  · omega

theorem order45GraphDegreeWindowFormula_satisfied_of_r45
    (maximum : Nat) (enough : 36190 ≤ maximum)
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45GraphDegreeWindowAssignment maximum color)
      (order45DegreeWindowFormula maximum 44) := by
  apply order45DegreeWindowFormula_satisfied maximum
    (order45GraphPrimaryAssignment maximum color) color simple
  · exact order45GraphPrimaryAssignment_represents maximum (by omega) color
  · exact order45_degree_window_of_r45 r45 color simple ramseyFree
  · exact enough

set_option maxRecDepth 100000 in
theorem order45DegreeCounterFormula_satisfied_of_exact
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (index : Nat) (indexBound : index < 44)
    (exact : ∀ row column, row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum index row column).Holds assignment ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            assignment) (row + 1))) :
    SatisfiesCnfFormula assignment
      (order45DegreeCounterFormula maximum index) := by
  have cells := satisfiesSequentialCounterCellFormula_of_exact assignment
    (order45VertexDegreeInput maximum (index + 1))
    (order45DegreeCounterState maximum index) 44 25 (by omega) (by omega)
    exact
  have outputsExact : ExactAtLeastCounterOutputs assignment
      (order45DegreeCounterOutput maximum index) 25
      (coloringDegree color ⟨index + 1, by omega⟩) := by
    intro thresholdIndex thresholdInside
    have cellExact := exact 43 thresholdIndex (by omega) (by omega)
      thresholdInside
    have inputCount := order45VertexDegreeInputCount maximum assignment color
      simple represents (index + 1) (by omega) (by omega)
    unfold sequentialCounterInputCount at inputCount
    rw [inputCount] at cellExact
    simpa [order45DegreeCounterOutput] using cellExact
  have bounds := window ⟨index + 1, by omega⟩
  have range := satisfiesCounterRangeClauses_of_bounds assignment
    (order45DegreeCounterOutput maximum index) 25
    (coloringDegree color ⟨index + 1, by omega⟩) 20 24
    (by omega) (by omega) (by omega) bounds.1 bounds.2 outputsExact
  intro clause membership
  simp only [order45DegreeCounterFormula, List.mem_append] at membership
  rcases membership with cellMembership | rangeMembership
  · exact cells clause cellMembership
  · exact range clause rangeMembership

set_option maxRecDepth 100000 in
theorem order45DegreeWindowFormula_satisfied_of_exact
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (exact : ∀ index, index < 44 → ∀ row column,
      row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum index row column).Holds assignment ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            assignment) (row + 1))) :
    SatisfiesCnfFormula assignment
      (order45DegreeWindowFormula maximum 44) := by
  have upTo : ∀ count : Nat, count ≤ 44 →
      SatisfiesCnfFormula assignment
        (order45DegreeWindowFormula maximum count) := by
    intro count countBound
    induction count with
    | zero => simp [order45DegreeWindowFormula, SatisfiesCnfFormula]
    | succ count inductionHypothesis =>
        have previous := inductionHypothesis (by omega)
        have current := order45DegreeCounterFormula_satisfied_of_exact
          maximum assignment color simple represents window count (by omega)
          (exact count (by omega))
        intro clause membership
        simp only [order45DegreeWindowFormula, List.mem_append] at membership
        rcases membership with previousMembership | currentMembership
        · exact previous clause previousMembership
        · exact current clause currentMembership
  exact upTo 44 (Nat.le_refl 44)

set_option maxRecDepth 100000 in
theorem order45DegreeCounterState_index_le_36190
    (maximum : Nat) (maximumEnough : 36190 ≤ maximum)
    (index row column : Nat) (indexBound : index < 44)
    (rowBound : row < 44) (columnInRow : column ≤ row)
    (columnInsideWidth : column < 25) :
    (order45DegreeCounterState maximum index row column).index.val ≤ 36190 := by
  have columnBound : column < min (row + 1) 25 :=
    Nat.lt_min.mpr ⟨by omega, columnInsideWidth⟩
  have identifierBound := counterStateIdentifier_le_end
    (990 + index * 800) 44 25 row column rowBound columnBound
  rw [counterCellsBefore_25_44] at identifierBound
  have identifierInside :
      counterStateDimacsVariable (990 + index * 800) 25 row column <
        maximum + 1 := by omega
  unfold order45DegreeCounterState counterStateDimacsLiteral dimacsLiteral
  simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside]
  omega

set_option maxRecDepth 100000 in
theorem assignmentWithCounterPairStates_order45Degree_exact
    (maximum : Nat) (graphSource : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (maximumEnough : 36190 ≤ maximum) (degreeBeforePair : 36190 ≤ hBase)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase) :
    ∀ index, index < 44 → ∀ row column,
      row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum index row column).Holds
          (assignmentWithCounterPairStates maximum
            (order45DegreeWindowAssignment maximum graphSource) hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            (assignmentWithCounterPairStates maximum
              (order45DegreeWindowAssignment maximum graphSource) hInput jInput
              hBase hRows hWidth jBase jRows jWidth)) (row + 1)) := by
  intro index indexBound row column rowBound columnInRow columnInsideWidth
  let degreeSource := order45DegreeWindowAssignment maximum graphSource
  let assignment := assignmentWithCounterPairStates maximum degreeSource
    hInput jInput hBase hRows hWidth jBase jRows jWidth
  have sourceExact := order45DegreeWindowAssignment_exact maximum graphSource
    maximumEnough index indexBound row column rowBound columnInRow
    columnInsideWidth
  have stateBelow :
      (order45DegreeCounterState maximum index row column).index.val ≤ hBase :=
    Nat.le_trans
      (order45DegreeCounterState_index_le_36190 maximum maximumEnough index row
        column indexBound rowBound columnInRow columnInsideWidth)
      degreeBeforePair
  have stateAssignmentEqual :=
    assignmentWithCounterPairStates_eq_source_below_hBase maximum degreeSource
      hInput jInput hBase hRows hWidth jBase jRows jWidth separated
      (order45DegreeCounterState maximum index row column).index stateBelow
  change assignment (order45DegreeCounterState maximum index row column).index =
    degreeSource (order45DegreeCounterState maximum index row column).index at stateAssignmentEqual
  have stateHoldsEqual :
      (order45DegreeCounterState maximum index row column).Holds assignment ↔
        (order45DegreeCounterState maximum index row column).Holds
          degreeSource := by
    unfold CnfLiteral.Holds
    rw [stateAssignmentEqual]
  have countEqual :
      trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            assignment) (row + 1) =
        trueCountPrefix
          (fun k => (order45VertexDegreeInput maximum (index + 1) k).truthValue
            degreeSource) (row + 1) := by
    apply trueCountPrefix_congr
    intro k kInside
    exact assignmentWithCounterPairStates_truthValue_eq_source maximum
      degreeSource hInput jInput hBase hRows hWidth jBase jRows jWidth
      separated (order45VertexDegreeInput maximum (index + 1) k)
      (Nat.le_trans
        (order45VertexDegreeInput_index_le_990 maximum (index + 1) k
          (by omega) (by omega) (by omega)) (by omega))
  change
    (order45DegreeCounterState maximum index row column).Holds assignment ↔ _
  rw [stateHoldsEqual, countEqual]
  exact sourceExact

set_option maxRecDepth 100000 in
theorem assignmentWithCounterPairStates_order45DegreeFormula_satisfied
    (maximum : Nat) (graphSource : CnfAssignment (maximum + 1))
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (graphRepresents : RepresentsOrder45Primary maximum graphSource color)
    (window : ∀ vertex : Fin 45,
      20 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 24)
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (maximumEnough : 36190 ≤ maximum) (degreeBeforePair : 36190 ≤ hBase)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase) :
    SatisfiesCnfFormula
      (assignmentWithCounterPairStates maximum
        (order45DegreeWindowAssignment maximum graphSource) hInput jInput
        hBase hRows hWidth jBase jRows jWidth)
      (order45DegreeWindowFormula maximum 44) := by
  let degreeSource := order45DegreeWindowAssignment maximum graphSource
  let assignment := assignmentWithCounterPairStates maximum degreeSource
    hInput jInput hBase hRows hWidth jBase jRows jWidth
  have degreeRepresents : RepresentsOrder45Primary maximum degreeSource color :=
    order45DegreeWindowAssignment_represents_primary maximum graphSource color
      graphRepresents (by omega)
  have finalRepresents : RepresentsOrder45Primary maximum assignment color :=
    assignmentWithCounterPairStates_represents_primary maximum degreeSource color
      degreeRepresents hInput jInput hBase hRows hWidth jBase jRows jWidth
      (by omega) (by omega) separated
  apply order45DegreeWindowFormula_satisfied_of_exact maximum assignment color
    simple finalRepresents window
  exact assignmentWithCounterPairStates_order45Degree_exact maximum graphSource
    hInput jInput hBase hRows hWidth jBase jRows jWidth maximumEnough
    degreeBeforePair separated

/-- Degree-20 branch assignment containing both the 44 global degree counters
and the H/J local counters.  The lex interval remains untouched. -/
def order45Degree20MotherAssignment (color : Coloring 45) :
    CnfAssignment (78697 + 1) :=
  assignmentWithCounterPairStates 78697
    (order45GraphDegreeWindowAssignment 78697 color)
    order45Degree20HInput order45Degree20JInput
    36627 190 101 50767 276 133

set_option maxRecDepth 100000 in
theorem order45Degree20MotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 78697
      (order45Degree20MotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 78697
    (order45GraphDegreeWindowAssignment 78697 color) color
    (order45GraphDegreeWindowAssignment_represents 78697 (by omega) color)
    order45Degree20HInput order45Degree20JInput
    36627 190 101 50767 276 133
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree20MotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree20MotherAssignment color)
      (order45DegreeWindowFormula 78697 44) := by
  simpa [order45Degree20MotherAssignment,
    order45GraphDegreeWindowAssignment] using
    (assignmentWithCounterPairStates_order45DegreeFormula_satisfied 78697
      (order45GraphPrimaryAssignment 78697 color) color simple
      (order45GraphPrimaryAssignment_represents 78697 (by omega) color)
      (order45_degree_window_of_r45 r45 color simple ramseyFree)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133
      (by omega) (by omega) (by decide))

set_option maxRecDepth 100000 in
theorem order45Degree20MotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 20) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree20MotherAssignment color)
      order45Degree20CounterTail := by
  have sourceRepresents := order45GraphDegreeWindowAssignment_represents
    78697 (by omega) color
  have sourceCounts := order45Degree20PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeWindowAssignment 78697 color)
    sourceRepresents
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
  simpa [order45Degree20MotherAssignment, order45Degree20CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 78697
      (order45GraphDegreeWindowAssignment 78697 color)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133 edgesH edgesJ
      68 100 116 132 226
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

def order45Degree21MotherAssignment (color : Coloring 45) :
    CnfAssignment (77148 + 1) :=
  assignmentWithCounterPairStates 77148
    (order45GraphDegreeWindowAssignment 77148 color)
    order45Degree21HInput order45Degree21JInput
    36630 210 108 53532 253 123

set_option maxRecDepth 100000 in
theorem order45Degree21MotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 77148
      (order45Degree21MotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 77148
    (order45GraphDegreeWindowAssignment 77148 color) color
    (order45GraphDegreeWindowAssignment_represents 77148 (by omega) color)
    order45Degree21HInput order45Degree21JInput
    36630 210 108 53532 253 123
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree21MotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree21MotherAssignment color)
      (order45DegreeWindowFormula 77148 44) := by
  simpa [order45Degree21MotherAssignment,
    order45GraphDegreeWindowAssignment] using
    (assignmentWithCounterPairStates_order45DegreeFormula_satisfied 77148
      (order45GraphPrimaryAssignment 77148 color) color simple
      (order45GraphPrimaryAssignment_represents 77148 (by omega) color)
      (order45_degree_window_of_r45 r45 color simple ramseyFree)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123
      (by omega) (by omega) (by decide))

set_option maxRecDepth 100000 in
theorem order45Degree21MotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 21) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree21MotherAssignment color)
      order45Degree21CounterTail := by
  have sourceRepresents := order45GraphDegreeWindowAssignment_represents
    77148 (by omega) color
  have sourceCounts := order45Degree21PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeWindowAssignment 77148 color)
    sourceRepresents
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
  simpa [order45Degree21MotherAssignment, order45Degree21CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 77148
      (order45GraphDegreeWindowAssignment 77148 color)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123 edgesH edgesJ
      77 107 101 122 222
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

def order45Degree22MotherAssignment (color : Coloring 45) :
    CnfAssignment (76651 + 1) :=
  assignmentWithCounterPairStates 76651
    (order45GraphDegreeWindowAssignment 76651 color)
    order45Degree22HInput order45Degree22JInput
    36631 231 115 56641 231 115

set_option maxRecDepth 100000 in
theorem order45Degree22MotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 76651
      (order45Degree22MotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 76651
    (order45GraphDegreeWindowAssignment 76651 color) color
    (order45GraphDegreeWindowAssignment_represents 76651 (by omega) color)
    order45Degree22HInput order45Degree22JInput
    36631 231 115 56641 231 115
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree22MotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree22MotherAssignment color)
      (order45DegreeWindowFormula 76651 44) := by
  simpa [order45Degree22MotherAssignment,
    order45GraphDegreeWindowAssignment] using
    (assignmentWithCounterPairStates_order45DegreeFormula_satisfied 76651
      (order45GraphPrimaryAssignment 76651 color) color simple
      (order45GraphPrimaryAssignment_represents 76651 (by omega) color)
      (order45_degree_window_of_r45 r45 color simple ramseyFree)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115
      (by omega) (by omega) (by decide))

set_option maxRecDepth 100000 in
theorem order45Degree22MotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 22) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree22MotherAssignment color)
      order45Degree22CounterTail := by
  have sourceRepresents := order45GraphDegreeWindowAssignment_represents
    76651 (by omega) color
  have sourceCounts := order45Degree22PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeWindowAssignment 76651 color)
    sourceRepresents
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
  simpa [order45Degree22MotherAssignment, order45Degree22CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 76651
      (order45GraphDegreeWindowAssignment 76651 color)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115 edgesH edgesJ
      88 114 88 114 220
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

/-- The exact mother-clause order after deleting only the cross-row lex block:
Ramsey clauses, fixed-star units, 44 degree windows, then the H/J tail. -/
def order45NonLexMotherFormula {variables : Nat}
    (ramsey fixed degreeWindows counterTail : CnfFormula variables) :
    CnfFormula variables :=
  ramsey ++ (fixed ++ (degreeWindows ++ counterTail))

theorem order45NonLexMotherFormula_satisfied {variables : Nat}
    (assignment : CnfAssignment variables)
    (ramsey fixed degreeWindows counterTail : CnfFormula variables)
    (ramseySatisfied : SatisfiesCnfFormula assignment ramsey)
    (fixedSatisfied : SatisfiesCnfFormula assignment fixed)
    (degreeSatisfied : SatisfiesCnfFormula assignment degreeWindows)
    (tailSatisfied : SatisfiesCnfFormula assignment counterTail) :
    SatisfiesCnfFormula assignment
      (order45NonLexMotherFormula ramsey fixed degreeWindows counterTail) := by
  intro clause membership
  simp only [order45NonLexMotherFormula, List.mem_append] at membership
  rcases membership with ramseyMembership |
    fixedMembership | degreeMembership | tailMembership
  · exact ramseySatisfied clause ramseyMembership
  · exact fixedSatisfied clause fixedMembership
  · exact degreeSatisfied clause degreeMembership
  · exact tailSatisfied clause tailMembership

def order45Degree20NonLexMotherFormula
    (ramsey fixed : CnfFormula (78697 + 1)) : CnfFormula (78697 + 1) :=
  order45NonLexMotherFormula ramsey fixed
    (order45DegreeWindowFormula 78697 44) order45Degree20CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree20NonLexMotherFormula_satisfied
    (ramsey fixedFormula : CnfFormula (78697 + 1))
    (ramseyShape : IsOrder45RamseyFormula 78697 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 78697 20 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (fixed : HasFixedStar color 20)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree20MotherAssignment color)
      (order45Degree20NonLexMotherFormula ramsey fixedFormula) := by
  unfold order45Degree20NonLexMotherFormula
  apply order45NonLexMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 78697 ramsey ramseyShape
      (order45Degree20MotherAssignment color) color
      (order45Degree20MotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 78697 20 fixedFormula fixedShape
      (order45Degree20MotherAssignment color) color
      (order45Degree20MotherAssignment_represents color) fixed
  · exact order45Degree20MotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree20MotherCounterTail_satisfied color simple fixed edgesH
      edgesJ counts hLower hUpper jLower jUpper dense

def order45Degree21NonLexMotherFormula
    (ramsey fixed : CnfFormula (77148 + 1)) : CnfFormula (77148 + 1) :=
  order45NonLexMotherFormula ramsey fixed
    (order45DegreeWindowFormula 77148 44) order45Degree21CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree21NonLexMotherFormula_satisfied
    (ramsey fixedFormula : CnfFormula (77148 + 1))
    (ramseyShape : IsOrder45RamseyFormula 77148 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 77148 21 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (fixed : HasFixedStar color 21)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree21MotherAssignment color)
      (order45Degree21NonLexMotherFormula ramsey fixedFormula) := by
  unfold order45Degree21NonLexMotherFormula
  apply order45NonLexMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 77148 ramsey ramseyShape
      (order45Degree21MotherAssignment color) color
      (order45Degree21MotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 77148 21 fixedFormula fixedShape
      (order45Degree21MotherAssignment color) color
      (order45Degree21MotherAssignment_represents color) fixed
  · exact order45Degree21MotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree21MotherCounterTail_satisfied color simple fixed edgesH
      edgesJ counts hLower hUpper jLower jUpper dense

def order45Degree22NonLexMotherFormula
    (ramsey fixed : CnfFormula (76651 + 1)) : CnfFormula (76651 + 1) :=
  order45NonLexMotherFormula ramsey fixed
    (order45DegreeWindowFormula 76651 44) order45Degree22CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree22NonLexMotherFormula_satisfied
    (ramsey fixedFormula : CnfFormula (76651 + 1))
    (ramseyShape : IsOrder45RamseyFormula 76651 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 76651 22 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (fixed : HasFixedStar color 22)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree22MotherAssignment color)
      (order45Degree22NonLexMotherFormula ramsey fixedFormula) := by
  unfold order45Degree22NonLexMotherFormula
  apply order45NonLexMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 76651 ramsey ramseyShape
      (order45Degree22MotherAssignment color) color
      (order45Degree22MotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 76651 22 fixedFormula fixedShape
      (order45Degree22MotherAssignment color) color
      (order45Degree22MotherAssignment_represents color) fixed
  · exact order45Degree22MotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree22MotherCounterTail_satisfied color simple fixed edgesH
      edgesJ counts hLower hUpper jLower jUpper dense

#print axioms trueCountPrefix_skip_false
#print axioms trueCountPrefix_order45NaturalRow_eq_degree
#print axioms order45VertexDegreeInput_truthValue
#print axioms order45VertexDegreeInputCount
#print axioms order45DegreeStateEntryKeys_nodup
#print axioms order45DegreeWindowAssignment_eq_source_below_990
#print axioms order45DegreeWindowAssignment_exact
#print axioms order45DegreeCounterCellFormula_satisfied
#print axioms order45DegreeWindowAssignment_represents_primary
#print axioms order45DegreeCounterOutputs_exact
#print axioms order45DegreeCounterFormula_satisfied
#print axioms order45DegreeWindowFormula_satisfied
#print axioms order45GraphDegreeWindowAssignment_represents
#print axioms order45GraphDegreeWindowFormula_satisfied_of_r45
#print axioms order45DegreeWindowFormula_satisfied_of_exact
#print axioms assignmentWithCounterPairStates_order45Degree_exact
#print axioms assignmentWithCounterPairStates_order45DegreeFormula_satisfied
#print axioms order45Degree20MotherAssignment_represents
#print axioms order45Degree20MotherDegreeWindow_satisfied
#print axioms order45Degree20MotherCounterTail_satisfied
#print axioms order45Degree21MotherAssignment_represents
#print axioms order45Degree21MotherDegreeWindow_satisfied
#print axioms order45Degree21MotherCounterTail_satisfied
#print axioms order45Degree22MotherAssignment_represents
#print axioms order45Degree22MotherDegreeWindow_satisfied
#print axioms order45Degree22MotherCounterTail_satisfied
#print axioms order45Degree20NonLexMotherFormula_satisfied
#print axioms order45Degree21NonLexMotherFormula_satisfied
#print axioms order45Degree22NonLexMotherFormula_satisfied

end Ramsey55
