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

end Ramsey55
