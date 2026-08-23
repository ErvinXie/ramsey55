import Ramsey55.Order45DegreeWindowAssignment
import Ramsey55.CnfLex

namespace Ramsey55

/-- Cross-row input `(row + 1, degree + column + 1)` used by the order-45
lex generator. Rows are fixed-star neighbours and columns are nonneighbours. -/
def order45CrossRowInput (maximum degree row column : Nat) :
    CnfLiteral (maximum + 1) :=
  dimacsLiteral maximum
    (orderedEdgeDimacsVariable (row + 1, degree + column + 1)) true

def order45LexStateIdentifier (degree comparison column : Nat) : Nat :=
  36190 + comparison * (43 - degree) + column + 1

def order45LexState (maximum degree comparison column : Nat) :
    CnfLiteral (maximum + 1) :=
  dimacsLiteral maximum
    (order45LexStateIdentifier degree comparison column) true

def order45LexComparisonFormula
    (maximum degree comparison : Nat) : CnfFormula (maximum + 1) :=
  lexLeqFormula
    (order45CrossRowInput maximum degree comparison)
    (order45CrossRowInput maximum degree (comparison + 1))
    (order45LexState maximum degree comparison) (44 - degree)

/-- Exact comparison order for the first `count` adjacent neighbour rows. -/
def order45LexFormula (maximum degree : Nat) : Nat →
    CnfFormula (maximum + 1)
  | 0 => []
  | count + 1 =>
      order45LexFormula maximum degree count ++
        order45LexComparisonFormula maximum degree count

def order45LexComparisonStateEntries {maximum : Nat}
    (source : CnfAssignment (maximum + 1))
    (degree comparison : Nat) : List (Nat × Bool) :=
  (List.range (43 - degree)).map fun column =>
    (order45LexStateIdentifier degree comparison column,
      literalPrefixEqualValue source
        (order45CrossRowInput maximum degree comparison)
        (order45CrossRowInput maximum degree (comparison + 1))
        (column + 1))

theorem order45LexComparisonStateEntryKeys_nodup {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) (degree comparison : Nat) :
    ((order45LexComparisonStateEntries source degree comparison).map
      Prod.fst).Nodup := by
  simpa [order45LexComparisonStateEntries, Function.comp_def] using
    (nodup_map_of_injective
      (fun column => order45LexStateIdentifier degree comparison column)
      (by
        intro first second equal
        change 36190 + comparison * (43 - degree) + first + 1 =
          36190 + comparison * (43 - degree) + second + 1 at equal
        omega)
      (List.range (43 - degree))
      (range_nodup_structural (43 - degree)))

theorem mem_order45LexComparisonStateEntryKey_bounds {maximum : Nat}
    (source : CnfAssignment (maximum + 1))
    (degree comparison identifier : Nat)
    (membership : identifier ∈
      (order45LexComparisonStateEntries source degree comparison).map
        Prod.fst) :
    36190 + comparison * (43 - degree) < identifier ∧
      identifier ≤ 36190 + comparison * (43 - degree) + (43 - degree) := by
  simp only [order45LexComparisonStateEntries, List.map_map,
    Function.comp_def, List.mem_map, List.mem_range] at membership
  rcases membership with ⟨column, columnBound, rfl⟩
  unfold order45LexStateIdentifier
  omega

def order45LexStateEntries {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) (degree : Nat) : Nat →
    List (Nat × Bool)
  | 0 => []
  | count + 1 =>
      order45LexStateEntries source degree count ++
        order45LexComparisonStateEntries source degree count

set_option maxRecDepth 100000 in
theorem mem_order45LexStateEntryKey_bounds {maximum : Nat}
    (source : CnfAssignment (maximum + 1))
    (degree count identifier : Nat)
    (membership : identifier ∈
      (order45LexStateEntries source degree count).map Prod.fst) :
    36190 < identifier ∧
      identifier ≤ 36190 + count * (43 - degree) := by
  induction count with
  | zero => simp [order45LexStateEntries] at membership
  | succ count inductionHypothesis =>
      simp only [order45LexStateEntries, List.map_append,
        List.mem_append] at membership
      rcases membership with previousMembership | currentMembership
      · have bounds := inductionHypothesis previousMembership
        constructor
        · exact bounds.1
        · exact Nat.le_trans bounds.2 (by
            rw [Nat.add_mul]
            omega)
      · have bounds := mem_order45LexComparisonStateEntryKey_bounds source
          degree count identifier currentMembership
        constructor
        · omega
        · rw [Nat.add_mul]
          omega

set_option maxRecDepth 100000 in
theorem order45LexStateEntryKeys_nodup {maximum : Nat}
    (source : CnfAssignment (maximum + 1)) (degree count : Nat) :
    ((order45LexStateEntries source degree count).map Prod.fst).Nodup := by
  induction count with
  | zero => simp [order45LexStateEntries]
  | succ count inductionHypothesis =>
      simp only [order45LexStateEntries, List.map_append]
      apply nodup_append_of_nodup_of_disjoint
      · exact inductionHypothesis
      · exact order45LexComparisonStateEntryKeys_nodup source degree count
      · intro identifier previousMembership currentMembership
        have previousBounds := mem_order45LexStateEntryKey_bounds source degree
          count identifier previousMembership
        have currentBounds := mem_order45LexComparisonStateEntryKey_bounds
          source degree count identifier currentMembership
        omega

set_option maxRecDepth 100000 in
theorem order45LexStateEntry_mem {maximum : Nat}
    (source : CnfAssignment (maximum + 1))
    (degree count comparison column : Nat)
    (comparisonBound : comparison < count) (columnBound : column < 43 - degree) :
    (order45LexStateIdentifier degree comparison column,
      literalPrefixEqualValue source
        (order45CrossRowInput maximum degree comparison)
        (order45CrossRowInput maximum degree (comparison + 1))
        (column + 1)) ∈ order45LexStateEntries source degree count := by
  induction count with
  | zero => omega
  | succ count inductionHypothesis =>
      simp only [order45LexStateEntries, List.mem_append]
      by_cases last : comparison = count
      · right
        subst comparison
        simp only [order45LexComparisonStateEntries, List.mem_map,
          List.mem_range]
        exact ⟨column, columnBound, rfl⟩
      · left
        exact inductionHypothesis (by omega)

/-- Overlay every intended equality-prefix variable for all adjacent row
comparisons. -/
def order45LexAssignment (maximum degree : Nat)
    (source : CnfAssignment (maximum + 1)) : CnfAssignment (maximum + 1) :=
  assignmentWithEntries source
    (order45LexStateEntries source degree (degree - 1))

theorem order45LexAssignment_eq_source_below_36190
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (index : Fin (maximum + 1)) (below : index.val ≤ 36190) :
    order45LexAssignment maximum degree source index = source index := by
  apply assignmentWithEntries_eq_fallback_of_not_mem
  intro membership
  have bounds := mem_order45LexStateEntryKey_bounds source degree (degree - 1)
    index.val membership
  omega

theorem order45CrossRowInput_index_le_990
    (maximum degree row column : Nat) (maximumEnough : 990 ≤ maximum)
    (degreeBound : degree ≤ 44) (rowBound : row < degree)
    (columnBound : column < 44 - degree) :
    (order45CrossRowInput maximum degree row column).index.val ≤ 990 := by
  have ordered : row + 1 < degree + column + 1 := by omega
  have inside : degree + column + 1 < 45 := by omega
  have identifierBound := orderedEdgeDimacsVariable_le_990
    (row + 1) (degree + column + 1) ordered inside
  have identifierInside :
      orderedEdgeDimacsVariable (row + 1, degree + column + 1) <
        maximum + 1 := by omega
  unfold order45CrossRowInput dimacsLiteral
  simpa [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside] using
    identifierBound

theorem order45LexAssignment_represents_primary
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum source color)
    (maximumEnough : 990 ≤ maximum) :
    RepresentsOrder45Primary maximum
      (order45LexAssignment maximum degree source) color := by
  intro left right ordered inside
  have identifierBound := orderedEdgeDimacsVariable_le_990 left right ordered
    inside
  have identifierInside :
      orderedEdgeDimacsVariable (left, right) < maximum + 1 := by omega
  have preserved := order45LexAssignment_eq_source_below_36190 maximum degree
    source
    (dimacsLiteral maximum (orderedEdgeDimacsVariable (left, right)) true).index
    (by
      unfold dimacsLiteral
      simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside]
      omega)
  unfold CnfLiteral.truthValue
  rw [preserved]
  exact represents left right ordered inside

set_option maxRecDepth 100000 in
theorem order45LexStateIdentifier_le_end
    (degree count comparison column : Nat)
    (comparisonBound : comparison < count)
    (columnBound : column < 43 - degree) :
    order45LexStateIdentifier degree comparison column ≤
      36190 + count * (43 - degree) := by
  have identifierStep :
      order45LexStateIdentifier degree comparison column ≤
        36190 + (comparison + 1) * (43 - degree) := by
    unfold order45LexStateIdentifier
    rw [Nat.add_mul]
    omega
  have multiplicationBound := Nat.mul_le_mul_right (43 - degree)
    (show comparison + 1 ≤ count by omega)
  have identifierBound :
      order45LexStateIdentifier degree comparison column ≤
        36190 + count * (43 - degree) := by omega
  exact identifierBound

set_option maxRecDepth 100000 in
theorem order45LexState_index_le_end
    (maximum degree count comparison column : Nat)
    (endInside : 36190 + count * (43 - degree) ≤ maximum)
    (comparisonBound : comparison < count)
    (columnBound : column < 43 - degree) :
    (order45LexState maximum degree comparison column).index.val ≤
      36190 + count * (43 - degree) := by
  have identifierBound := order45LexStateIdentifier_le_end degree count
    comparison column comparisonBound columnBound
  have identifierInside :
      order45LexStateIdentifier degree comparison column < maximum + 1 := by
    omega
  unfold order45LexState dimacsLiteral
  simpa [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside] using
    identifierBound

set_option maxRecDepth 100000 in
theorem order45LexAssignment_state_sourceExact
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (endInside : 36190 + (degree - 1) * (43 - degree) ≤ maximum)
    (comparison column : Nat) (comparisonBound : comparison < degree - 1)
    (columnBound : column + 1 < 44 - degree) :
    ((order45LexState maximum degree comparison column).Holds
        (order45LexAssignment maximum degree source) ↔
      LiteralPrefixEqual source
        (order45CrossRowInput maximum degree comparison)
        (order45CrossRowInput maximum degree (comparison + 1))
        (column + 1)) := by
  have columnStride : column < 43 - degree := by omega
  have identifierInside :
      order45LexStateIdentifier degree comparison column < maximum + 1 := by
    have bound := order45LexStateIdentifier_le_end degree (degree - 1)
      comparison column comparisonBound columnStride
    omega
  have assigned := assignmentWithEntries_eq_of_entry source
    (order45LexStateEntries source degree (degree - 1))
    (order45LexStateIdentifier degree comparison column)
    (literalPrefixEqualValue source
      (order45CrossRowInput maximum degree comparison)
      (order45CrossRowInput maximum degree (comparison + 1))
      (column + 1)) identifierInside
    (order45LexStateEntryKeys_nodup source degree (degree - 1))
    (order45LexStateEntry_mem source degree (degree - 1) comparison column
      comparisonBound columnStride)
  unfold order45LexState order45LexAssignment CnfLiteral.Holds dimacsLiteral
  have finEqual :
      Fin.ofNat (maximum + 1)
          (order45LexStateIdentifier degree comparison column) =
        ⟨order45LexStateIdentifier degree comparison column,
          identifierInside⟩ := by
    apply Fin.ext
    simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside]
  rw [finEqual, assigned]
  exact literalPrefixEqualValue_eq_true_iff source
    (order45CrossRowInput maximum degree comparison)
    (order45CrossRowInput maximum degree (comparison + 1)) (column + 1)

set_option maxRecDepth 100000 in
theorem order45LexAssignment_state_exact
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (degreePositive : 0 < degree) (degreeBound : degree ≤ 43)
    (endInside : 36190 + (degree - 1) * (43 - degree) ≤ maximum)
    (comparison column : Nat) (comparisonBound : comparison < degree - 1)
    (columnBound : column + 1 < 44 - degree) :
    ((order45LexState maximum degree comparison column).Holds
        (order45LexAssignment maximum degree source) ↔
      LiteralPrefixEqual (order45LexAssignment maximum degree source)
        (order45CrossRowInput maximum degree comparison)
        (order45CrossRowInput maximum degree (comparison + 1))
        (column + 1)) := by
  have sourceExact := order45LexAssignment_state_sourceExact maximum degree
    source endInside comparison column comparisonBound columnBound
  have prefixEqual := LiteralPrefixEqual.congr
    (order45LexAssignment maximum degree source) source
    (order45CrossRowInput maximum degree comparison)
    (order45CrossRowInput maximum degree (comparison + 1)) (column + 1)
    (by
      intro index indexBound
      unfold CnfLiteral.Holds
      rw [order45LexAssignment_eq_source_below_36190 maximum degree source
        (order45CrossRowInput maximum degree comparison index).index]
      exact Nat.le_trans
        (order45CrossRowInput_index_le_990 maximum degree comparison index
          (by omega) (by omega) (by omega) (by omega)) (by omega))
    (by
      intro index indexBound
      unfold CnfLiteral.Holds
      rw [order45LexAssignment_eq_source_below_36190 maximum degree source
        (order45CrossRowInput maximum degree (comparison + 1) index).index]
      exact Nat.le_trans
        (order45CrossRowInput_index_le_990 maximum degree (comparison + 1)
          index (by omega) (by omega) (by omega) (by omega)) (by omega))
  exact sourceExact.trans prefixEqual.symm

def Order45CrossRowsLexSorted (maximum degree : Nat)
    (assignment : CnfAssignment (maximum + 1)) : Prop :=
  ∀ comparison, comparison < degree - 1 →
    LiteralRowsLexLe assignment
      (order45CrossRowInput maximum degree comparison)
      (order45CrossRowInput maximum degree (comparison + 1)) (44 - degree)

set_option maxRecDepth 100000 in
theorem order45LexComparisonFormula_satisfied
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (degreePositive : 0 < degree) (degreeBound : degree ≤ 43)
    (endInside : 36190 + (degree - 1) * (43 - degree) ≤ maximum)
    (comparison : Nat) (comparisonBound : comparison < degree - 1)
    (ordered : LiteralRowsLexLe
      (order45LexAssignment maximum degree source)
      (order45CrossRowInput maximum degree comparison)
      (order45CrossRowInput maximum degree (comparison + 1))
      (44 - degree)) :
    SatisfiesCnfFormula (order45LexAssignment maximum degree source)
      (order45LexComparisonFormula maximum degree comparison) := by
  apply lexLeqFormula_satisfied
  · exact ordered
  · intro column columnBound
    exact order45LexAssignment_state_exact maximum degree source degreePositive
      degreeBound endInside comparison column comparisonBound columnBound

set_option maxRecDepth 100000 in
theorem order45LexFormula_satisfied
    (maximum degree : Nat) (source : CnfAssignment (maximum + 1))
    (degreePositive : 0 < degree) (degreeBound : degree ≤ 43)
    (endInside : 36190 + (degree - 1) * (43 - degree) ≤ maximum)
    (sorted : Order45CrossRowsLexSorted maximum degree
      (order45LexAssignment maximum degree source)) :
    SatisfiesCnfFormula (order45LexAssignment maximum degree source)
      (order45LexFormula maximum degree (degree - 1)) := by
  have upTo : ∀ count : Nat, count ≤ degree - 1 →
      SatisfiesCnfFormula (order45LexAssignment maximum degree source)
        (order45LexFormula maximum degree count) := by
    intro count countBound
    induction count with
    | zero => simp [order45LexFormula, SatisfiesCnfFormula]
    | succ count inductionHypothesis =>
        have previous := inductionHypothesis (by omega)
        have current := order45LexComparisonFormula_satisfied maximum degree
          source degreePositive degreeBound endInside count (by omega)
          (sorted count (by omega))
        intro clause membership
        simp only [order45LexFormula, List.mem_append] at membership
        rcases membership with previousMembership | currentMembership
        · exact previous clause previousMembership
        · exact current clause currentMembership
  exact upTo (degree - 1) (Nat.le_refl (degree - 1))

theorem order45LexFinalIdentifiers :
    36190 + (20 - 1) * (43 - 20) = 36627 ∧
      36190 + (21 - 1) * (43 - 21) = 36630 ∧
      36190 + (22 - 1) * (43 - 22) = 36631 := by
  decide

set_option maxRecDepth 100000 in
theorem order45LexFormulaLengths :
    (order45LexFormula 36627 20 (20 - 1)).length = 2622 ∧
      (order45LexFormula 36630 21 (21 - 1)).length = 2640 ∧
      (order45LexFormula 36631 22 (22 - 1)).length = 2646 := by
  decide

set_option maxRecDepth 100000 in
theorem order45LexAssignment_order45Degree_exact
    (maximum fixedDegree : Nat)
    (graphSource : CnfAssignment (maximum + 1))
    (lexEndInside : 36190 + (fixedDegree - 1) * (43 - fixedDegree) ≤ maximum) :
    ∀ vertexIndex, vertexIndex < 44 → ∀ row column,
      row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum vertexIndex row column).Holds
          (order45LexAssignment maximum fixedDegree
            (order45DegreeWindowAssignment maximum graphSource)) ↔
        column + 1 ≤ trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              (order45LexAssignment maximum fixedDegree
                (order45DegreeWindowAssignment maximum graphSource)))
          (row + 1)) := by
  intro vertexIndex vertexIndexBound row column rowBound columnInRow
    columnInsideWidth
  let degreeSource := order45DegreeWindowAssignment maximum graphSource
  let assignment := order45LexAssignment maximum fixedDegree degreeSource
  have maximumEnough : 36190 ≤ maximum := by omega
  have sourceExact := order45DegreeWindowAssignment_exact maximum graphSource
    maximumEnough vertexIndex vertexIndexBound row column rowBound columnInRow
    columnInsideWidth
  have stateBelow := order45DegreeCounterState_index_le_36190 maximum
    maximumEnough vertexIndex row column vertexIndexBound rowBound columnInRow
    columnInsideWidth
  have stateAssignmentEqual :=
    order45LexAssignment_eq_source_below_36190 maximum fixedDegree degreeSource
      (order45DegreeCounterState maximum vertexIndex row column).index
      stateBelow
  change assignment
      (order45DegreeCounterState maximum vertexIndex row column).index =
    degreeSource
      (order45DegreeCounterState maximum vertexIndex row column).index at stateAssignmentEqual
  have stateHoldsEqual :
      (order45DegreeCounterState maximum vertexIndex row column).Holds
          assignment ↔
        (order45DegreeCounterState maximum vertexIndex row column).Holds
          degreeSource := by
    unfold CnfLiteral.Holds
    rw [stateAssignmentEqual]
  have countEqual :
      trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              assignment) (row + 1) =
        trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              degreeSource) (row + 1) := by
    apply trueCountPrefix_congr
    intro k kInside
    have inputAssignmentEqual :=
      order45LexAssignment_eq_source_below_36190 maximum fixedDegree
        degreeSource
        (order45VertexDegreeInput maximum (vertexIndex + 1) k).index
        (Nat.le_trans
          (order45VertexDegreeInput_index_le_990 maximum (vertexIndex + 1) k
            (by omega) (by omega) (by omega)) (by omega))
    change assignment
        (order45VertexDegreeInput maximum (vertexIndex + 1) k).index =
      degreeSource
        (order45VertexDegreeInput maximum (vertexIndex + 1) k).index at inputAssignmentEqual
    unfold CnfLiteral.truthValue
    rw [inputAssignmentEqual]
  change
    (order45DegreeCounterState maximum vertexIndex row column).Holds
        assignment ↔ _
  rw [stateHoldsEqual, countEqual]
  exact sourceExact

def order45GraphDegreeLexAssignment (maximum fixedDegree : Nat)
    (color : Coloring 45) : CnfAssignment (maximum + 1) :=
  order45LexAssignment maximum fixedDegree
    (order45GraphDegreeWindowAssignment maximum color)

theorem order45GraphDegreeLexAssignment_represents
    (maximum fixedDegree : Nat) (enough : 36190 ≤ maximum)
    (color : Coloring 45) :
    RepresentsOrder45Primary maximum
      (order45GraphDegreeLexAssignment maximum fixedDegree color) color := by
  apply order45LexAssignment_represents_primary maximum fixedDegree
    (order45GraphDegreeWindowAssignment maximum color) color
  · exact order45GraphDegreeWindowAssignment_represents maximum enough color
  · omega

set_option maxRecDepth 100000 in
theorem order45GraphDegreeLexDegreeFormula_satisfied
    (maximum fixedDegree : Nat)
    (lexEndInside : 36190 + (fixedDegree - 1) * (43 - fixedDegree) ≤ maximum)
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula
      (order45GraphDegreeLexAssignment maximum fixedDegree color)
      (order45DegreeWindowFormula maximum 44) := by
  have maximumEnough : 36190 ≤ maximum := by omega
  apply order45DegreeWindowFormula_satisfied_of_exact maximum
    (order45GraphDegreeLexAssignment maximum fixedDegree color) color simple
  · exact order45GraphDegreeLexAssignment_represents maximum fixedDegree
      maximumEnough color
  · exact order45_degree_window_of_r45 r45 color simple ramseyFree
  · simpa [order45GraphDegreeLexAssignment,
      order45GraphDegreeWindowAssignment] using
      (order45LexAssignment_order45Degree_exact maximum fixedDegree
        (order45GraphPrimaryAssignment maximum color) lexEndInside)

set_option maxRecDepth 100000 in
theorem order45GraphDegreeLexFormula_satisfied
    (maximum fixedDegree : Nat)
    (degreePositive : 0 < fixedDegree) (degreeBound : fixedDegree ≤ 43)
    (lexEndInside : 36190 + (fixedDegree - 1) * (43 - fixedDegree) ≤ maximum)
    (color : Coloring 45)
    (sorted : Order45CrossRowsLexSorted maximum fixedDegree
      (order45GraphDegreeLexAssignment maximum fixedDegree color)) :
    SatisfiesCnfFormula
      (order45GraphDegreeLexAssignment maximum fixedDegree color)
      (order45LexFormula maximum fixedDegree (fixedDegree - 1)) := by
  exact order45LexFormula_satisfied maximum fixedDegree
    (order45GraphDegreeWindowAssignment maximum color) degreePositive
    degreeBound lexEndInside sorted

set_option maxRecDepth 100000 in
theorem order45LexFormula_satisfied_of_exact
    (maximum fixedDegree : Nat) (assignment : CnfAssignment (maximum + 1))
    (sorted : Order45CrossRowsLexSorted maximum fixedDegree assignment)
    (exact : ∀ comparison, comparison < fixedDegree - 1 → ∀ column,
      column + 1 < 44 - fixedDegree →
      ((order45LexState maximum fixedDegree comparison column).Holds
          assignment ↔
        LiteralPrefixEqual assignment
          (order45CrossRowInput maximum fixedDegree comparison)
          (order45CrossRowInput maximum fixedDegree (comparison + 1))
          (column + 1))) :
    SatisfiesCnfFormula assignment
      (order45LexFormula maximum fixedDegree (fixedDegree - 1)) := by
  have upTo : ∀ count : Nat, count ≤ fixedDegree - 1 →
      SatisfiesCnfFormula assignment
        (order45LexFormula maximum fixedDegree count) := by
    intro count countBound
    induction count with
    | zero => simp [order45LexFormula, SatisfiesCnfFormula]
    | succ count inductionHypothesis =>
        have previous := inductionHypothesis (by omega)
        have current : SatisfiesCnfFormula assignment
            (order45LexComparisonFormula maximum fixedDegree count) := by
          apply lexLeqFormula_satisfied
          · exact sorted count (by omega)
          · exact exact count (by omega)
        intro clause membership
        simp only [order45LexFormula, List.mem_append] at membership
        rcases membership with previousMembership | currentMembership
        · exact previous clause previousMembership
        · exact current clause currentMembership
  exact upTo (fixedDegree - 1) (Nat.le_refl (fixedDegree - 1))

set_option maxRecDepth 100000 in
theorem assignmentWithCounterPairStates_order45Degree_exact_of_source
    (maximum : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (maximumEnough : 36190 ≤ maximum) (degreeBeforePair : 36190 ≤ hBase)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (sourceExact : ∀ vertexIndex, vertexIndex < 44 → ∀ row column,
      row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum vertexIndex row column).Holds
          source ↔
        column + 1 ≤ trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              source) (row + 1))) :
    ∀ vertexIndex, vertexIndex < 44 → ∀ row column,
      row < 44 → column ≤ row → column < 25 →
      ((order45DegreeCounterState maximum vertexIndex row column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        column + 1 ≤ trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              (assignmentWithCounterPairStates maximum source hInput jInput
                hBase hRows hWidth jBase jRows jWidth)) (row + 1)) := by
  intro vertexIndex vertexIndexBound row column rowBound columnInRow
    columnInsideWidth
  let assignment := assignmentWithCounterPairStates maximum source hInput
    jInput hBase hRows hWidth jBase jRows jWidth
  have stateBelow :
      (order45DegreeCounterState maximum vertexIndex row column).index.val ≤
        hBase := Nat.le_trans
    (order45DegreeCounterState_index_le_36190 maximum maximumEnough vertexIndex
      row column vertexIndexBound rowBound columnInRow columnInsideWidth)
    degreeBeforePair
  have stateAssignmentEqual :=
    assignmentWithCounterPairStates_eq_source_below_hBase maximum source
      hInput jInput hBase hRows hWidth jBase jRows jWidth separated
      (order45DegreeCounterState maximum vertexIndex row column).index
      stateBelow
  change assignment
      (order45DegreeCounterState maximum vertexIndex row column).index =
    source (order45DegreeCounterState maximum vertexIndex row column).index at stateAssignmentEqual
  have stateHoldsEqual :
      (order45DegreeCounterState maximum vertexIndex row column).Holds
          assignment ↔
        (order45DegreeCounterState maximum vertexIndex row column).Holds
          source := by
    unfold CnfLiteral.Holds
    rw [stateAssignmentEqual]
  have countEqual :
      trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              assignment) (row + 1) =
        trueCountPrefix
          (fun k =>
            (order45VertexDegreeInput maximum (vertexIndex + 1) k).truthValue
              source) (row + 1) := by
    apply trueCountPrefix_congr
    intro k kInside
    exact assignmentWithCounterPairStates_truthValue_eq_source maximum source
      hInput jInput hBase hRows hWidth jBase jRows jWidth separated
      (order45VertexDegreeInput maximum (vertexIndex + 1) k)
      (Nat.le_trans
        (order45VertexDegreeInput_index_le_990 maximum (vertexIndex + 1) k
          (by omega) (by omega) (by omega)) (by omega))
  change
    (order45DegreeCounterState maximum vertexIndex row column).Holds
        assignment ↔ _
  rw [stateHoldsEqual, countEqual]
  exact sourceExact vertexIndex vertexIndexBound row column rowBound
    columnInRow columnInsideWidth

set_option maxRecDepth 100000 in
theorem assignmentWithCounterPairStates_order45Lex_exact_of_source
    (maximum fixedDegree : Nat) (source : CnfAssignment (maximum + 1))
    (hInput jInput : Nat → CnfLiteral (maximum + 1))
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (degreePositive : 0 < fixedDegree) (degreeBound : fixedDegree ≤ 43)
    (lexEndInside : 36190 + (fixedDegree - 1) * (43 - fixedDegree) ≤ maximum)
    (lexBeforePair : 36190 + (fixedDegree - 1) * (43 - fixedDegree) ≤ hBase)
    (separated : hBase + counterCellsBefore hWidth hRows ≤ jBase)
    (sourceExact : ∀ comparison, comparison < fixedDegree - 1 → ∀ column,
      column + 1 < 44 - fixedDegree →
      ((order45LexState maximum fixedDegree comparison column).Holds source ↔
        LiteralPrefixEqual source
          (order45CrossRowInput maximum fixedDegree comparison)
          (order45CrossRowInput maximum fixedDegree (comparison + 1))
          (column + 1))) :
    ∀ comparison, comparison < fixedDegree - 1 → ∀ column,
      column + 1 < 44 - fixedDegree →
      ((order45LexState maximum fixedDegree comparison column).Holds
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth) ↔
        LiteralPrefixEqual
          (assignmentWithCounterPairStates maximum source hInput jInput
            hBase hRows hWidth jBase jRows jWidth)
          (order45CrossRowInput maximum fixedDegree comparison)
          (order45CrossRowInput maximum fixedDegree (comparison + 1))
          (column + 1)) := by
  intro comparison comparisonBound column columnBound
  let assignment := assignmentWithCounterPairStates maximum source hInput
    jInput hBase hRows hWidth jBase jRows jWidth
  have columnStride : column < 43 - fixedDegree := by omega
  have stateBelow :
      (order45LexState maximum fixedDegree comparison column).index.val ≤
        hBase := Nat.le_trans
    (order45LexState_index_le_end maximum fixedDegree (fixedDegree - 1)
      comparison column lexEndInside comparisonBound columnStride)
    lexBeforePair
  have stateAssignmentEqual :=
    assignmentWithCounterPairStates_eq_source_below_hBase maximum source
      hInput jInput hBase hRows hWidth jBase jRows jWidth separated
      (order45LexState maximum fixedDegree comparison column).index stateBelow
  change assignment
      (order45LexState maximum fixedDegree comparison column).index =
    source (order45LexState maximum fixedDegree comparison column).index at stateAssignmentEqual
  have stateHoldsEqual :
      (order45LexState maximum fixedDegree comparison column).Holds assignment ↔
        (order45LexState maximum fixedDegree comparison column).Holds source := by
    unfold CnfLiteral.Holds
    rw [stateAssignmentEqual]
  have prefixEqual := LiteralPrefixEqual.congr assignment source
    (order45CrossRowInput maximum fixedDegree comparison)
    (order45CrossRowInput maximum fixedDegree (comparison + 1)) (column + 1)
    (by
      intro index indexBound
      have inputAssignmentEqual :=
        assignmentWithCounterPairStates_eq_source_below_hBase maximum source
          hInput jInput hBase hRows hWidth jBase jRows jWidth separated
          (order45CrossRowInput maximum fixedDegree comparison index).index
          (Nat.le_trans
            (order45CrossRowInput_index_le_990 maximum fixedDegree comparison index
              (by omega) (by omega) (by omega) (by omega)) (by omega))
      change assignment
          (order45CrossRowInput maximum fixedDegree comparison index).index =
        source
          (order45CrossRowInput maximum fixedDegree comparison index).index at inputAssignmentEqual
      unfold CnfLiteral.Holds
      rw [inputAssignmentEqual])
    (by
      intro index indexBound
      have inputAssignmentEqual :=
        assignmentWithCounterPairStates_eq_source_below_hBase maximum source
          hInput jInput hBase hRows hWidth jBase jRows jWidth separated
          (order45CrossRowInput maximum fixedDegree (comparison + 1) index).index
          (Nat.le_trans
            (order45CrossRowInput_index_le_990 maximum fixedDegree (comparison + 1)
              index (by omega) (by omega) (by omega) (by omega)) (by omega))
      change assignment
          (order45CrossRowInput maximum fixedDegree (comparison + 1) index).index =
        source
          (order45CrossRowInput maximum fixedDegree (comparison + 1) index).index at inputAssignmentEqual
      unfold CnfLiteral.Holds
      rw [inputAssignmentEqual])
  exact stateHoldsEqual.trans ((sourceExact comparison comparisonBound column
    columnBound).trans prefixEqual.symm)

/-- Degree-20 mother assignment with the generated degree, cross-row lex, and
H/J counter-state intervals all populated. -/
def order45Degree20FullMotherAssignment (color : Coloring 45) :
    CnfAssignment (78697 + 1) :=
  assignmentWithCounterPairStates 78697
    (order45GraphDegreeLexAssignment 78697 20 color)
    order45Degree20HInput order45Degree20JInput
    36627 190 101 50767 276 133

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 78697
      (order45Degree20FullMotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 78697
    (order45GraphDegreeLexAssignment 78697 20 color) color
    (order45GraphDegreeLexAssignment_represents 78697 20 (by omega) color)
    order45Degree20HInput order45Degree20JInput
    36627 190 101 50767 276 133
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree20FullMotherAssignment color)
      (order45DegreeWindowFormula 78697 44) := by
  apply order45DegreeWindowFormula_satisfied_of_exact 78697
    (order45Degree20FullMotherAssignment color) color simple
    (order45Degree20FullMotherAssignment_represents color)
    (order45_degree_window_of_r45 r45 color simple ramseyFree)
  simpa [order45Degree20FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Degree_exact_of_source 78697
      (order45GraphDegreeLexAssignment 78697 20 color)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133
      (by omega) (by omega) (by decide)
      (by
        simpa [order45GraphDegreeLexAssignment,
          order45GraphDegreeWindowAssignment] using
          (order45LexAssignment_order45Degree_exact 78697 20
            (order45GraphPrimaryAssignment 78697 color) (by omega))))

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherLex_satisfied
    (color : Coloring 45)
    (sorted : Order45CrossRowsLexSorted 78697 20
      (order45Degree20FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree20FullMotherAssignment color)
      (order45LexFormula 78697 20 (20 - 1)) := by
  apply order45LexFormula_satisfied_of_exact 78697 20
    (order45Degree20FullMotherAssignment color) sorted
  simpa [order45Degree20FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Lex_exact_of_source 78697 20
      (order45GraphDegreeLexAssignment 78697 20 color)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133
      (by omega) (by omega) (by omega) (by omega) (by decide)
      (by
        intro comparison comparisonBound column columnBound
        simpa [order45GraphDegreeLexAssignment] using
          (order45LexAssignment_state_exact 78697 20
            (order45GraphDegreeWindowAssignment 78697 color)
            (by omega) (by omega) (by omega) comparison column
            comparisonBound columnBound)))

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 20) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree20FullMotherAssignment color)
      order45Degree20CounterTail := by
  have sourceRepresents := order45GraphDegreeLexAssignment_represents
    78697 20 (by omega) color
  have sourceCounts := order45Degree20PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeLexAssignment 78697 20 color)
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
  simpa [order45Degree20FullMotherAssignment,
    order45Degree20CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 78697
      (order45GraphDegreeLexAssignment 78697 20 color)
      order45Degree20HInput order45Degree20JInput
      36627 190 101 50767 276 133 edgesH edgesJ
      68 100 116 132 226
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

/-- Degree-21 mother assignment with the generated degree, cross-row lex, and
H/J counter-state intervals all populated. -/
def order45Degree21FullMotherAssignment (color : Coloring 45) :
    CnfAssignment (77148 + 1) :=
  assignmentWithCounterPairStates 77148
    (order45GraphDegreeLexAssignment 77148 21 color)
    order45Degree21HInput order45Degree21JInput
    36630 210 108 53532 253 123

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 77148
      (order45Degree21FullMotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 77148
    (order45GraphDegreeLexAssignment 77148 21 color) color
    (order45GraphDegreeLexAssignment_represents 77148 21 (by omega) color)
    order45Degree21HInput order45Degree21JInput
    36630 210 108 53532 253 123
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree21FullMotherAssignment color)
      (order45DegreeWindowFormula 77148 44) := by
  apply order45DegreeWindowFormula_satisfied_of_exact 77148
    (order45Degree21FullMotherAssignment color) color simple
    (order45Degree21FullMotherAssignment_represents color)
    (order45_degree_window_of_r45 r45 color simple ramseyFree)
  simpa [order45Degree21FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Degree_exact_of_source 77148
      (order45GraphDegreeLexAssignment 77148 21 color)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123
      (by omega) (by omega) (by decide)
      (by
        simpa [order45GraphDegreeLexAssignment,
          order45GraphDegreeWindowAssignment] using
          (order45LexAssignment_order45Degree_exact 77148 21
            (order45GraphPrimaryAssignment 77148 color) (by omega))))

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherLex_satisfied
    (color : Coloring 45)
    (sorted : Order45CrossRowsLexSorted 77148 21
      (order45Degree21FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree21FullMotherAssignment color)
      (order45LexFormula 77148 21 (21 - 1)) := by
  apply order45LexFormula_satisfied_of_exact 77148 21
    (order45Degree21FullMotherAssignment color) sorted
  simpa [order45Degree21FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Lex_exact_of_source 77148 21
      (order45GraphDegreeLexAssignment 77148 21 color)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123
      (by omega) (by omega) (by omega) (by omega) (by decide)
      (by
        intro comparison comparisonBound column columnBound
        simpa [order45GraphDegreeLexAssignment] using
          (order45LexAssignment_state_exact 77148 21
            (order45GraphDegreeWindowAssignment 77148 color)
            (by omega) (by omega) (by omega) comparison column
            comparisonBound columnBound)))

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 21) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree21FullMotherAssignment color)
      order45Degree21CounterTail := by
  have sourceRepresents := order45GraphDegreeLexAssignment_represents
    77148 21 (by omega) color
  have sourceCounts := order45Degree21PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeLexAssignment 77148 21 color)
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
  simpa [order45Degree21FullMotherAssignment,
    order45Degree21CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 77148
      (order45GraphDegreeLexAssignment 77148 21 color)
      order45Degree21HInput order45Degree21JInput
      36630 210 108 53532 253 123 edgesH edgesJ
      77 107 101 122 222
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

/-- Degree-22 mother assignment with the generated degree, cross-row lex, and
H/J counter-state intervals all populated. -/
def order45Degree22FullMotherAssignment (color : Coloring 45) :
    CnfAssignment (76651 + 1) :=
  assignmentWithCounterPairStates 76651
    (order45GraphDegreeLexAssignment 76651 22 color)
    order45Degree22HInput order45Degree22JInput
    36631 231 115 56641 231 115

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherAssignment_represents (color : Coloring 45) :
    RepresentsOrder45Primary 76651
      (order45Degree22FullMotherAssignment color) color := by
  apply assignmentWithCounterPairStates_represents_primary 76651
    (order45GraphDegreeLexAssignment 76651 22 color) color
    (order45GraphDegreeLexAssignment_represents 76651 22 (by omega) color)
    order45Degree22HInput order45Degree22JInput
    36631 231 115 56641 231 115
  · omega
  · omega
  · decide

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherDegreeWindow_satisfied
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula (order45Degree22FullMotherAssignment color)
      (order45DegreeWindowFormula 76651 44) := by
  apply order45DegreeWindowFormula_satisfied_of_exact 76651
    (order45Degree22FullMotherAssignment color) color simple
    (order45Degree22FullMotherAssignment_represents color)
    (order45_degree_window_of_r45 r45 color simple ramseyFree)
  simpa [order45Degree22FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Degree_exact_of_source 76651
      (order45GraphDegreeLexAssignment 76651 22 color)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115
      (by omega) (by omega) (by decide)
      (by
        simpa [order45GraphDegreeLexAssignment,
          order45GraphDegreeWindowAssignment] using
          (order45LexAssignment_order45Degree_exact 76651 22
            (order45GraphPrimaryAssignment 76651 color) (by omega))))

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherLex_satisfied
    (color : Coloring 45)
    (sorted : Order45CrossRowsLexSorted 76651 22
      (order45Degree22FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree22FullMotherAssignment color)
      (order45LexFormula 76651 22 (22 - 1)) := by
  apply order45LexFormula_satisfied_of_exact 76651 22
    (order45Degree22FullMotherAssignment color) sorted
  simpa [order45Degree22FullMotherAssignment] using
    (assignmentWithCounterPairStates_order45Lex_exact_of_source 76651 22
      (order45GraphDegreeLexAssignment 76651 22 color)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115
      (by omega) (by omega) (by omega) (by omega) (by decide)
      (by
        intro comparison comparisonBound column columnBound
        simpa [order45GraphDegreeLexAssignment] using
          (order45LexAssignment_state_exact 76651 22
            (order45GraphDegreeWindowAssignment 76651 color)
            (by omega) (by omega) (by omega) comparison column
            comparisonBound columnBound)))

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherCounterTail_satisfied
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 22) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ) :
    SatisfiesCnfFormula (order45Degree22FullMotherAssignment color)
      order45Degree22CounterTail := by
  have sourceRepresents := order45GraphDegreeLexAssignment_represents
    76651 22 (by omega) color
  have sourceCounts := order45Degree22PrimaryInputCounts color simple fixed
    edgesH edgesJ counts (order45GraphDegreeLexAssignment 76651 22 color)
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
  simpa [order45Degree22FullMotherAssignment,
    order45Degree22CounterTail] using
    (assignmentWithCounterPairStates_satisfies_encoding 76651
      (order45GraphDegreeLexAssignment 76651 22 color)
      order45Degree22HInput order45Degree22JInput
      36631 231 115 56641 231 115 edgesH edgesJ
      88 114 88 114 220
      (by decide) (by decide) hInputBelow jInputBelow
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      sourceCounts.1 sourceCounts.2
      (by omega) (by omega) (by omega) (by omega) (by omega) (by omega)
      hLower hUpper jLower jUpper dense)

/-- Exact block order emitted by `generate_order45_edge_strata.py`: Ramsey,
fixed star, degree windows, cross-row lex leaders, then the H/J counter tail. -/
def order45FullMotherFormula {variables : Nat}
    (ramsey fixed degreeWindows lex counterTail : CnfFormula variables) :
    CnfFormula variables :=
  ramsey ++ (fixed ++ (degreeWindows ++ (lex ++ counterTail)))

theorem order45FullMotherFormula_satisfied {variables : Nat}
    (assignment : CnfAssignment variables)
    (ramsey fixed degreeWindows lex counterTail : CnfFormula variables)
    (ramseySatisfied : SatisfiesCnfFormula assignment ramsey)
    (fixedSatisfied : SatisfiesCnfFormula assignment fixed)
    (degreeSatisfied : SatisfiesCnfFormula assignment degreeWindows)
    (lexSatisfied : SatisfiesCnfFormula assignment lex)
    (tailSatisfied : SatisfiesCnfFormula assignment counterTail) :
    SatisfiesCnfFormula assignment
      (order45FullMotherFormula ramsey fixed degreeWindows lex counterTail) := by
  intro clause membership
  simp only [order45FullMotherFormula, List.mem_append] at membership
  rcases membership with ramseyMembership | fixedMembership |
    degreeMembership | lexMembership | tailMembership
  · exact ramseySatisfied clause ramseyMembership
  · exact fixedSatisfied clause fixedMembership
  · exact degreeSatisfied clause degreeMembership
  · exact lexSatisfied clause lexMembership
  · exact tailSatisfied clause tailMembership

def order45Degree20FullMotherFormula
    (ramsey fixed : CnfFormula (78697 + 1)) : CnfFormula (78697 + 1) :=
  order45FullMotherFormula ramsey fixed
    (order45DegreeWindowFormula 78697 44)
    (order45LexFormula 78697 20 (20 - 1)) order45Degree20CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherFormula_satisfied
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
    (dense : 226 ≤ edgesH + edgesJ)
    (sorted : Order45CrossRowsLexSorted 78697 20
      (order45Degree20FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree20FullMotherAssignment color)
      (order45Degree20FullMotherFormula ramsey fixedFormula) := by
  unfold order45Degree20FullMotherFormula
  apply order45FullMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 78697 ramsey ramseyShape
      (order45Degree20FullMotherAssignment color) color
      (order45Degree20FullMotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 78697 20 fixedFormula fixedShape
      (order45Degree20FullMotherAssignment color) color
      (order45Degree20FullMotherAssignment_represents color) fixed
  · exact order45Degree20FullMotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree20FullMotherLex_satisfied color sorted
  · exact order45Degree20FullMotherCounterTail_satisfied color simple fixed
      edgesH edgesJ counts hLower hUpper jLower jUpper dense

def order45Degree21FullMotherFormula
    (ramsey fixed : CnfFormula (77148 + 1)) : CnfFormula (77148 + 1) :=
  order45FullMotherFormula ramsey fixed
    (order45DegreeWindowFormula 77148 44)
    (order45LexFormula 77148 21 (21 - 1)) order45Degree21CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherFormula_satisfied
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
    (dense : 222 ≤ edgesH + edgesJ)
    (sorted : Order45CrossRowsLexSorted 77148 21
      (order45Degree21FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree21FullMotherAssignment color)
      (order45Degree21FullMotherFormula ramsey fixedFormula) := by
  unfold order45Degree21FullMotherFormula
  apply order45FullMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 77148 ramsey ramseyShape
      (order45Degree21FullMotherAssignment color) color
      (order45Degree21FullMotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 77148 21 fixedFormula fixedShape
      (order45Degree21FullMotherAssignment color) color
      (order45Degree21FullMotherAssignment_represents color) fixed
  · exact order45Degree21FullMotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree21FullMotherLex_satisfied color sorted
  · exact order45Degree21FullMotherCounterTail_satisfied color simple fixed
      edgesH edgesJ counts hLower hUpper jLower jUpper dense

def order45Degree22FullMotherFormula
    (ramsey fixed : CnfFormula (76651 + 1)) : CnfFormula (76651 + 1) :=
  order45FullMotherFormula ramsey fixed
    (order45DegreeWindowFormula 76651 44)
    (order45LexFormula 76651 22 (22 - 1)) order45Degree22CounterTail

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherFormula_satisfied
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
    (dense : 220 ≤ edgesH + edgesJ)
    (sorted : Order45CrossRowsLexSorted 76651 22
      (order45Degree22FullMotherAssignment color)) :
    SatisfiesCnfFormula (order45Degree22FullMotherAssignment color)
      (order45Degree22FullMotherFormula ramsey fixedFormula) := by
  unfold order45Degree22FullMotherFormula
  apply order45FullMotherFormula_satisfied
  · exact order45RamseyFormula_satisfied 76651 ramsey ramseyShape
      (order45Degree22FullMotherAssignment color) color
      (order45Degree22FullMotherAssignment_represents color) ramseyFree
  · exact order45FixedStarFormula_satisfied 76651 22 fixedFormula fixedShape
      (order45Degree22FullMotherAssignment color) color
      (order45Degree22FullMotherAssignment_represents color) fixed
  · exact order45Degree22FullMotherDegreeWindow_satisfied r45 color simple
      ramseyFree
  · exact order45Degree22FullMotherLex_satisfied color sorted
  · exact order45Degree22FullMotherCounterTail_satisfied color simple fixed
      edgesH edgesJ counts hLower hUpper jLower jUpper dense

/-- Fully concrete typed mothers matching the five emitted DIMACS blocks.
Unlike the generic wrappers above, these definitions contain the exact
Ramsey and fixed-star prefix streams rather than accepting shape hypotheses. -/
def order45Degree20ExactFullMotherFormula : CnfFormula (78697 + 1) :=
  order45Degree20FullMotherFormula
    (order45ExactRamseyFormula 78697)
    (order45ExactFixedStarFormula 78697 20)

def order45Degree21ExactFullMotherFormula : CnfFormula (77148 + 1) :=
  order45Degree21FullMotherFormula
    (order45ExactRamseyFormula 77148)
    (order45ExactFixedStarFormula 77148 21)

def order45Degree22ExactFullMotherFormula : CnfFormula (76651 + 1) :=
  order45Degree22FullMotherFormula
    (order45ExactRamseyFormula 76651)
    (order45ExactFixedStarFormula 76651 22)

#print axioms order45LexStateEntryKeys_nodup
#print axioms order45LexAssignment_eq_source_below_36190
#print axioms order45LexAssignment_represents_primary
#print axioms order45LexAssignment_state_exact
#print axioms order45LexFormula_satisfied
#print axioms order45LexFinalIdentifiers
#print axioms order45LexFormulaLengths
#print axioms order45LexAssignment_order45Degree_exact
#print axioms order45GraphDegreeLexAssignment_represents
#print axioms order45GraphDegreeLexDegreeFormula_satisfied
#print axioms order45GraphDegreeLexFormula_satisfied
#print axioms order45LexFormula_satisfied_of_exact
#print axioms assignmentWithCounterPairStates_order45Degree_exact_of_source
#print axioms assignmentWithCounterPairStates_order45Lex_exact_of_source
#print axioms order45Degree20FullMotherAssignment_represents
#print axioms order45Degree20FullMotherDegreeWindow_satisfied
#print axioms order45Degree20FullMotherLex_satisfied
#print axioms order45Degree20FullMotherCounterTail_satisfied
#print axioms order45Degree21FullMotherAssignment_represents
#print axioms order45Degree21FullMotherDegreeWindow_satisfied
#print axioms order45Degree21FullMotherLex_satisfied
#print axioms order45Degree21FullMotherCounterTail_satisfied
#print axioms order45Degree22FullMotherAssignment_represents
#print axioms order45Degree22FullMotherDegreeWindow_satisfied
#print axioms order45Degree22FullMotherLex_satisfied
#print axioms order45Degree22FullMotherCounterTail_satisfied
#print axioms order45FullMotherFormula_satisfied
#print axioms order45Degree20FullMotherFormula_satisfied
#print axioms order45Degree21FullMotherFormula_satisfied
#print axioms order45Degree22FullMotherFormula_satisfied

end Ramsey55
