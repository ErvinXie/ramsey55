import Ramsey55.Order45LexAssignment
import Ramsey55.Order45ExcessTarget
import Ramsey55.Relabeling
import Init.Data.List.Lex
import Init.Data.List.Nat.Pairwise

namespace Ramsey55

/-- The concrete cross row used as the sorting key for a neighbour label.
False and true are embedded as `0` and `1`; natural labels make the definition
independent of bound proofs. -/
def order45ColorCrossRowKey (color : Coloring 45)
    (degree row : Nat) : List Nat :=
  (List.range (44 - degree)).map fun column =>
    edgeWeight (order45NatColor color (row + 1) (degree + column + 1))

@[simp] theorem order45ColorCrossRowKey_length
    (color : Coloring 45) (degree row : Nat) :
    (order45ColorCrossRowKey color degree row).length = 44 - degree := by
  simp [order45ColorCrossRowKey]

theorem edgeWeight_injective : Function.Injective edgeWeight := by
  intro left right equal
  cases left <;> cases right <;> simp [edgeWeight] at equal ⊢

set_option maxRecDepth 100000 in
theorem order45ColorCrossRowKey_le_implication
    (color : Coloring 45) (degree left right : Nat)
    (ordered : order45ColorCrossRowKey color degree left ≤
      order45ColorCrossRowKey color degree right) :
    ∀ column, column < 44 - degree →
      (∀ index, index < column →
        order45NatColor color (left + 1) (degree + index + 1) =
          order45NatColor color (right + 1) (degree + index + 1)) →
      order45NatColor color (left + 1) (degree + column + 1) = true →
      order45NatColor color (right + 1) (degree + column + 1) = true := by
  intro column columnBound rowPrefix leftTrue
  rcases (List.le_iff_exists.mp ordered) with equal | firstDifference
  · have equalLists : order45ColorCrossRowKey color degree left =
        order45ColorCrossRowKey color degree right := by
      have lengths :
          (order45ColorCrossRowKey color degree left).length =
            (order45ColorCrossRowKey color degree right).length := by simp
      rw [lengths, List.take_length] at equal
      exact equal
    have leftInside : column <
        (order45ColorCrossRowKey color degree left).length := by
      simpa using columnBound
    have atColumn := getElem_congr
      (c := order45ColorCrossRowKey color degree left)
      (d := order45ColorCrossRowKey color degree right)
      equalLists (i := column) (j := column) rfl leftInside
    have valueEqual :
        edgeWeight (order45NatColor color (left + 1)
          (degree + column + 1)) =
        edgeWeight (order45NatColor color (right + 1)
          (degree + column + 1)) := by
      simpa [order45ColorCrossRowKey] using atColumn
    have bitEqual := edgeWeight_injective valueEqual
    rw [← bitEqual, leftTrue]
  · rcases firstDifference with
      ⟨index, leftInside, rightInside, firstPrefix, smaller⟩
    have indexBound : index < 44 - degree := by
      simpa [order45ColorCrossRowKey] using leftInside
    have firstPrefixValues : ∀ prior, prior < index →
        order45NatColor color (left + 1) (degree + prior + 1) =
          order45NatColor color (right + 1) (degree + prior + 1) := by
      intro prior priorBound
      have value := firstPrefix prior priorBound
      apply edgeWeight_injective
      simpa [order45ColorCrossRowKey] using value
    have smallerValues :
        edgeWeight (order45NatColor color (left + 1)
          (degree + index + 1)) <
          edgeWeight (order45NatColor color (right + 1)
            (degree + index + 1)) := by
      simpa [order45ColorCrossRowKey] using smaller
    rcases Nat.lt_trichotomy index column with before | same | after
    · have equalAtIndex := rowPrefix index before
      rw [equalAtIndex] at smallerValues
      omega
    · subst index
      cases leftValue : order45NatColor color (left + 1)
          (degree + column + 1) <;>
        cases rightValue : order45NatColor color (right + 1)
          (degree + column + 1) <;>
        simp_all [edgeWeight]
    · have equalAtColumn := firstPrefixValues column after
      rw [← equalAtColumn, leftTrue]

/-- Neighbour indices sorted by their concrete cross-row keys. -/
def order45SortedNeighborIndices (color : Coloring 45)
    (degree : Nat) : List (Fin degree) :=
  (allVertices degree).mergeSort fun left right =>
    decide (order45ColorCrossRowKey color degree left.val ≤
      order45ColorCrossRowKey color degree right.val)

@[simp] theorem order45SortedNeighborIndices_length
    (color : Coloring 45) (degree : Nat) :
    (order45SortedNeighborIndices color degree).length = degree := by
  simp [order45SortedNeighborIndices, allVertices]

theorem order45SortedNeighborIndices_perm
    (color : Coloring 45) (degree : Nat) :
    (order45SortedNeighborIndices color degree).Perm (allVertices degree) := by
  exact List.mergeSort_perm _ _

theorem order45SortedNeighborIndices_nodup
    (color : Coloring 45) (degree : Nat) :
    (order45SortedNeighborIndices color degree).Nodup := by
  exact (order45SortedNeighborIndices_perm color degree).nodup_iff.mpr
    (allVertices_nodup degree)

/-- The old neighbour placed at a new neighbour-block position. -/
def order45SortedNeighborMap (color : Coloring 45)
    (degree : Nat) : Fin degree → Fin degree := fun position =>
  (order45SortedNeighborIndices color degree)[position.val]'(by
    simp)

theorem ofFn_order45SortedNeighborMap (color : Coloring 45)
    (degree : Nat) :
    List.ofFn (order45SortedNeighborMap color degree) =
      order45SortedNeighborIndices color degree := by
  apply List.ext_getElem
  · simp
  · intro index leftInside rightInside
    simp [order45SortedNeighborMap]

theorem order45SortedNeighborMap_injective (color : Coloring 45)
    (degree : Nat) :
    Function.Injective (order45SortedNeighborMap color degree) := by
  intro left right equal
  apply Fin.ext
  apply (List.getElem_inj
    (order45SortedNeighborIndices_nodup color degree)).mp
  exact equal

set_option maxRecDepth 100000 in
theorem order45SortedNeighborIndices_pairwise
    (color : Coloring 45) (degree : Nat) :
    (order45SortedNeighborIndices color degree).Pairwise fun left right =>
      order45ColorCrossRowKey color degree left.val ≤
        order45ColorCrossRowKey color degree right.val := by
  let compare : Fin degree → Fin degree → Bool := fun left right =>
    decide (order45ColorCrossRowKey color degree left.val ≤
      order45ColorCrossRowKey color degree right.val)
  have sorted : (order45SortedNeighborIndices color degree).Pairwise
      (fun left right => compare left right = true) := by
    change ((allVertices degree).mergeSort compare).Pairwise
      (fun left right => compare left right = true)
    apply List.pairwise_mergeSort
    · intro left middle right leftMiddle middleRight
      simp [compare] at leftMiddle middleRight ⊢
      exact List.le_trans leftMiddle middleRight
    · intro left right
      simp [compare]
      exact Std.Total.total _ _
  simpa [compare] using sorted

set_option maxRecDepth 100000 in
theorem order45SortedNeighborMap_keys_ordered
    (color : Coloring 45) (degree comparison : Nat)
    (comparisonBound : comparison + 1 < degree) :
    order45ColorCrossRowKey color degree
        (order45SortedNeighborMap color degree
          ⟨comparison, by omega⟩).val ≤
      order45ColorCrossRowKey color degree
        (order45SortedNeighborMap color degree
          ⟨comparison + 1, comparisonBound⟩).val := by
  have pairwise := order45SortedNeighborIndices_pairwise color degree
  have ordered := (List.pairwise_iff_getElem.mp pairwise)
    comparison (comparison + 1)
    (by rw [order45SortedNeighborIndices_length]; omega)
    (by rw [order45SortedNeighborIndices_length]; omega) (by omega)
  simpa [order45SortedNeighborMap] using ordered

/-- Extend the sorted neighbour permutation to all 45 labels.  Vertex zero
and every nonneighbour-block label remain fixed. -/
def order45LexVertexMap (color : Coloring 45) (degree : Nat)
    (degreeBound : degree ≤ 44) : Fin 45 → Fin 45 := fun vertex =>
  if positive : 0 < vertex.val then
    if neighbor : vertex.val ≤ degree then
      order45NeighborBlockMap degree degreeBound
        (order45SortedNeighborMap color degree
          ⟨vertex.val - 1, by omega⟩)
    else vertex
  else vertex

@[simp] theorem order45LexVertexMap_zero
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44) :
    order45LexVertexMap color degree degreeBound 0 = 0 := by
  simp [order45LexVertexMap]

theorem order45LexVertexMap_neighbor
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (vertex : Fin 45) (positive : 0 < vertex.val)
    (neighbor : vertex.val ≤ degree) :
    order45LexVertexMap color degree degreeBound vertex =
      order45NeighborBlockMap degree degreeBound
        (order45SortedNeighborMap color degree
          ⟨vertex.val - 1, by omega⟩) := by
  simp [order45LexVertexMap, positive, neighbor]

theorem order45LexVertexMap_nonneighbor
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (vertex : Fin 45) (beyond : degree < vertex.val) :
    order45LexVertexMap color degree degreeBound vertex = vertex := by
  have positive : 0 < vertex.val := by omega
  have notNeighbor : ¬vertex.val ≤ degree := by omega
  simp [order45LexVertexMap, positive, notNeighbor]

theorem order45LexVertexMap_positive_iff
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (vertex : Fin 45) :
    0 < (order45LexVertexMap color degree degreeBound vertex).val ↔
      0 < vertex.val := by
  by_cases positive : 0 < vertex.val
  · by_cases neighbor : vertex.val ≤ degree
    · rw [order45LexVertexMap_neighbor color degree degreeBound vertex
        positive neighbor]
      constructor
      · intro mappedPositive
        exact positive
      · intro originalPositive
        simp [order45NeighborBlockMap]
    · simp [order45LexVertexMap, positive, neighbor]
  · have zero : vertex.val = 0 := by omega
    simp [order45LexVertexMap, zero]

theorem order45LexVertexMap_le_degree_iff
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (vertex : Fin 45) :
    (order45LexVertexMap color degree degreeBound vertex).val ≤ degree ↔
      vertex.val ≤ degree := by
  by_cases positive : 0 < vertex.val
  · by_cases neighbor : vertex.val ≤ degree
    · rw [order45LexVertexMap_neighbor color degree degreeBound vertex
        positive neighbor]
      constructor
      · intro mappedInside
        exact neighbor
      · intro originalInside
        simp [order45NeighborBlockMap]
        exact Nat.succ_le_of_lt
          (order45SortedNeighborMap color degree
            ⟨vertex.val - 1, by omega⟩).isLt
    · simp [order45LexVertexMap, positive, neighbor]
  · have zero : vertex.val = 0 := by omega
    simp [order45LexVertexMap, zero]

set_option maxRecDepth 100000 in
theorem order45LexVertexMap_injective
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44) :
    Function.Injective (order45LexVertexMap color degree degreeBound) := by
  intro left right equal
  by_cases leftPositive : 0 < left.val
  · have mappedLeftPositive :=
      (order45LexVertexMap_positive_iff color degree degreeBound left).2
        leftPositive
    have rightPositive : 0 < right.val := by
      apply (order45LexVertexMap_positive_iff color degree degreeBound right).1
      rw [← equal]
      exact mappedLeftPositive
    by_cases leftNeighbor : left.val ≤ degree
    · have mappedLeftNeighbor :=
        (order45LexVertexMap_le_degree_iff color degree degreeBound left).2
          leftNeighbor
      have rightNeighbor : right.val ≤ degree := by
        apply (order45LexVertexMap_le_degree_iff color degree degreeBound right).1
        rw [← equal]
        exact mappedLeftNeighbor
      rw [order45LexVertexMap_neighbor color degree degreeBound left
          leftPositive leftNeighbor,
        order45LexVertexMap_neighbor color degree degreeBound right
          rightPositive rightNeighbor] at equal
      have sortedEqual := order45NeighborBlockMap_injective degree degreeBound
        equal
      have indexEqual := order45SortedNeighborMap_injective color degree
        sortedEqual
      apply Fin.ext
      have values := congrArg Fin.val indexEqual
      simp at values
      omega
    · have leftBeyond : degree < left.val := by omega
      have mappedLeftBeyond : degree <
          (order45LexVertexMap color degree degreeBound left).val := by
        rw [order45LexVertexMap_nonneighbor color degree degreeBound left
          leftBeyond]
        exact leftBeyond
      have mappedRightBeyond : degree <
          (order45LexVertexMap color degree degreeBound right).val := by
        rw [← equal]
        exact mappedLeftBeyond
      have rightBeyond : degree < right.val := by
        by_cases rightNeighbor : right.val ≤ degree
        · have mappedRightNeighbor :=
            (order45LexVertexMap_le_degree_iff color degree degreeBound right).2
              rightNeighbor
          omega
        · omega
      rw [order45LexVertexMap_nonneighbor color degree degreeBound left
          leftBeyond,
        order45LexVertexMap_nonneighbor color degree degreeBound right
          rightBeyond] at equal
      exact equal
  · have leftZero : left.val = 0 := by omega
    have mappedLeftZero :
        (order45LexVertexMap color degree degreeBound left).val = 0 := by
      have leftFin : left = 0 := Fin.ext leftZero
      subst left
      simp
    have mappedRightZero :
        (order45LexVertexMap color degree degreeBound right).val = 0 := by
      rw [← equal]
      exact mappedLeftZero
    have notRightPositive : ¬0 < right.val := by
      intro rightPositive
      have := (order45LexVertexMap_positive_iff color degree degreeBound right).2
        rightPositive
      omega
    have rightZero : right.val = 0 := by omega
    exact Fin.ext (leftZero.trans rightZero.symm)

/-- Two duplicate-free lists of the same length are permutations when every
member of the first occurs in the second. -/
theorem perm_of_nodup_length_eq_subset {alpha : Type}
    [BEq alpha] [LawfulBEq alpha] :
    ∀ {left right : List alpha}, left.Nodup → right.Nodup →
      left.length = right.length → left ⊆ right → left.Perm right := by
  intro left
  induction left with
  | nil =>
      intro right leftNodup rightNodup lengths subset
      have rightNil : right = [] := by
        apply List.eq_nil_of_length_eq_zero
        simpa using lengths.symm
      subst right
      exact List.Perm.refl []
  | cons head tail inductionHypothesis =>
      intro right leftNodup rightNodup lengths subset
      have headMember : head ∈ right := subset (by simp)
      have tailNodup := leftNodup.tail
      have erasedNodup := rightNodup.erase head
      have erasedLength : tail.length = (right.erase head).length := by
        rw [List.length_erase_of_mem headMember]
        simp at lengths
        omega
      have tailSubset : tail ⊆ right.erase head := by
        intro value valueMember
        apply (rightNodup.mem_erase_iff).2
        constructor
        · intro equalHead
          subst value
          exact (List.nodup_cons.mp leftNodup).1 valueMember
        · exact subset (by simp [valueMember])
      have tailPerm := inductionHypothesis tailNodup erasedNodup
        erasedLength tailSubset
      exact (tailPerm.cons head).trans (List.perm_cons_erase headMember).symm

theorem order45LexVertexMap_isVertexRelabeling
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44) :
    IsVertexRelabeling (order45LexVertexMap color degree degreeBound) := by
  constructor
  · exact order45LexVertexMap_injective color degree degreeBound
  · have mappedNodup := nodup_ofFn_of_injective 45
      (order45LexVertexMap color degree degreeBound)
      (order45LexVertexMap_injective color degree degreeBound)
    apply perm_of_nodup_length_eq_subset mappedNodup (allVertices_nodup 45)
    · simp [allVertices]
    · intro vertex membership
      exact List.mem_ofFn.mpr ⟨vertex, rfl⟩

def order45LexRelabeledColor (color : Coloring 45) (degree : Nat)
    (degreeBound : degree ≤ 44) : Coloring 45 :=
  relabelColoring color (order45LexVertexMap color degree degreeBound)

theorem order45LexRelabeledColor_cross_entry
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 43)
    (row column : Nat) (rowBound : row < degree)
    (columnBound : column < 44 - degree) :
    order45NatColor
        (order45LexRelabeledColor color degree (by omega))
        (row + 1) (degree + column + 1) =
      order45NatColor color
        ((order45SortedNeighborMap color degree
          ⟨row, rowBound⟩).val + 1) (degree + column + 1) := by
  have rowInside : row + 1 < 45 := by omega
  have columnInside : degree + column + 1 < 45 := by omega
  have rowPositive : 0 < (⟨row + 1, rowInside⟩ : Fin 45).val := by simp
  have rowNeighbor : (⟨row + 1, rowInside⟩ : Fin 45).val ≤ degree := by
    simp
    omega
  have mappedRow := order45LexVertexMap_neighbor color degree (by omega)
    ⟨row + 1, rowInside⟩ rowPositive rowNeighbor
  have mappedColumn := order45LexVertexMap_nonneighbor color degree (by omega)
    ⟨degree + column + 1, columnInside⟩ (by simp; omega)
  have sortedRowInside :
      (order45SortedNeighborMap color degree ⟨row, rowBound⟩).val + 1 < 45 := by
    have := (order45SortedNeighborMap color degree ⟨row, rowBound⟩).isLt
    omega
  unfold order45NatColor order45LexRelabeledColor relabelColoring
  simp only [dif_pos rowInside, dif_pos columnInside]
  rw [mappedRow, mappedColumn]
  simp [order45NeighborBlockMap, sortedRowInside]

set_option maxRecDepth 100000 in
theorem order45LexRelabeledColor_rows_ordered
    (color : Coloring 45) (degree : Nat) (degreePositive : 0 < degree)
    (degreeBound : degree ≤ 43) :
    ∀ comparison, comparison < degree - 1 → ∀ column,
      column < 44 - degree →
      (∀ index, index < column →
        order45NatColor
            (order45LexRelabeledColor color degree (by omega))
            (comparison + 1) (degree + index + 1) =
          order45NatColor
            (order45LexRelabeledColor color degree (by omega))
            (comparison + 2) (degree + index + 1)) →
      order45NatColor
          (order45LexRelabeledColor color degree (by omega))
          (comparison + 1) (degree + column + 1) = true →
      order45NatColor
          (order45LexRelabeledColor color degree (by omega))
          (comparison + 2) (degree + column + 1) = true := by
  intro comparison comparisonBound column columnBound rowPrefix leftTrue
  have firstRowBound : comparison < degree := by omega
  have secondRowBound : comparison + 1 < degree := by omega
  have keyOrdered := order45SortedNeighborMap_keys_ordered color degree
    comparison (by omega)
  have implication := order45ColorCrossRowKey_le_implication color degree
    (order45SortedNeighborMap color degree
      ⟨comparison, firstRowBound⟩).val
    (order45SortedNeighborMap color degree
      ⟨comparison + 1, secondRowBound⟩).val keyOrdered
    column columnBound
  have result := implication
    (by
      intro index indexBound
      rw [← order45LexRelabeledColor_cross_entry color degree degreeBound
          comparison index firstRowBound (by omega),
        ← order45LexRelabeledColor_cross_entry color degree degreeBound
          (comparison + 1) index secondRowBound (by omega)]
      simpa [Nat.add_assoc] using rowPrefix index indexBound)
    (by
      rw [← order45LexRelabeledColor_cross_entry color degree degreeBound
        comparison column firstRowBound columnBound]
      exact leftTrue)
  rw [← order45LexRelabeledColor_cross_entry color degree degreeBound
    (comparison + 1) column secondRowBound columnBound] at result
  simpa [Nat.add_assoc] using result

theorem order45LexRelabeledColor_hasFixedStar
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (fixed : HasFixedStar color degree) :
    HasFixedStar (order45LexRelabeledColor color degree degreeBound) degree := by
  constructor
  · intro vertex positive neighbor
    unfold order45LexRelabeledColor relabelColoring
    rw [order45LexVertexMap_zero,
      order45LexVertexMap_neighbor color degree degreeBound vertex positive
        neighbor]
    apply fixed.1
    · simp [order45NeighborBlockMap]
    · simp [order45NeighborBlockMap]
      exact Nat.succ_le_of_lt
        (order45SortedNeighborMap color degree
          ⟨vertex.val - 1, by omega⟩).isLt
  · intro vertex beyond
    unfold order45LexRelabeledColor relabelColoring
    rw [order45LexVertexMap_zero,
      order45LexVertexMap_nonneighbor color degree degreeBound vertex beyond]
    exact fixed.2 vertex beyond

theorem LiteralPrefixEqual.at {variables : Nat}
    (assignment : CnfAssignment variables)
    (left right : Nat → CnfLiteral variables) :
    ∀ length, LiteralPrefixEqual assignment left right length →
      ∀ index, index < length →
        ((left index).Holds assignment ↔ (right index).Holds assignment) := by
  intro length
  induction length with
  | zero =>
      intro equal index indexBound
      omega
  | succ length inductionHypothesis =>
      intro equal index indexBound
      simp only [LiteralPrefixEqual] at equal
      by_cases last : index = length
      · subst index
        exact equal.2
      · exact inductionHypothesis equal.1 index (by omega)

theorem order45CrossRowInput_holds_iff
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (degree row column : Nat)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (degreeBound : degree ≤ 43) (rowBound : row < degree)
    (columnBound : column < 44 - degree) :
    (order45CrossRowInput maximum degree row column).Holds assignment ↔
      order45NatColor color (row + 1) (degree + column + 1) = true := by
  rw [← CnfLiteral.truthValue_eq_true_iff_holds]
  simpa [order45CrossRowInput] using
    congrArg (· = true)
      (represents (row + 1) (degree + column + 1) (by omega) (by omega))

set_option maxRecDepth 100000 in
theorem order45CrossRowsLexSorted_of_color_rows_ordered
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) (degree : Nat)
    (degreePositive : 0 < degree) (degreeBound : degree ≤ 43)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (rowsOrdered : ∀ comparison, comparison < degree - 1 → ∀ column,
      column < 44 - degree →
      (∀ index, index < column →
        order45NatColor color (comparison + 1) (degree + index + 1) =
          order45NatColor color (comparison + 2) (degree + index + 1)) →
      order45NatColor color (comparison + 1) (degree + column + 1) = true →
      order45NatColor color (comparison + 2)
        (degree + column + 1) = true) :
    Order45CrossRowsLexSorted maximum degree assignment := by
  intro comparison comparisonBound column columnBound prefixEqual leftHolds
  have firstRowBound : comparison < degree := by omega
  have secondRowBound : comparison + 1 < degree := by omega
  have colorPrefix : ∀ index, index < column →
      order45NatColor color (comparison + 1) (degree + index + 1) =
        order45NatColor color (comparison + 2) (degree + index + 1) := by
    intro index indexBound
    have literalEqual := LiteralPrefixEqual.at assignment
      (order45CrossRowInput maximum degree comparison)
      (order45CrossRowInput maximum degree (comparison + 1))
      column prefixEqual index indexBound
    have firstIff := order45CrossRowInput_holds_iff maximum assignment color
      degree comparison index represents degreeBound firstRowBound (by omega)
    have secondIff := order45CrossRowInput_holds_iff maximum assignment color
      degree (comparison + 1) index represents degreeBound secondRowBound
      (by omega)
    cases firstValue : order45NatColor color (comparison + 1)
        (degree + index + 1) <;>
      cases secondValue : order45NatColor color (comparison + 2)
        (degree + index + 1) <;> simp_all
  have firstIff := order45CrossRowInput_holds_iff maximum assignment color
    degree comparison column represents degreeBound firstRowBound columnBound
  have secondIff := order45CrossRowInput_holds_iff maximum assignment color
    degree (comparison + 1) column represents degreeBound secondRowBound
    columnBound
  apply secondIff.2
  apply rowsOrdered comparison comparisonBound column columnBound colorPrefix
  exact firstIff.1 leftHolds

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherAssignment_lexSorted_after_relabel
    (color : Coloring 45) :
    Order45CrossRowsLexSorted 78697 20
      (order45Degree20FullMotherAssignment
        (order45LexRelabeledColor color 20 (by omega))) := by
  apply order45CrossRowsLexSorted_of_color_rows_ordered 78697
    (order45Degree20FullMotherAssignment
      (order45LexRelabeledColor color 20 (by omega)))
    (order45LexRelabeledColor color 20 (by omega)) 20 (by omega) (by omega)
    (order45Degree20FullMotherAssignment_represents
      (order45LexRelabeledColor color 20 (by omega)))
  exact order45LexRelabeledColor_rows_ordered color 20 (by omega) (by omega)

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherAssignment_lexSorted_after_relabel
    (color : Coloring 45) :
    Order45CrossRowsLexSorted 77148 21
      (order45Degree21FullMotherAssignment
        (order45LexRelabeledColor color 21 (by omega))) := by
  apply order45CrossRowsLexSorted_of_color_rows_ordered 77148
    (order45Degree21FullMotherAssignment
      (order45LexRelabeledColor color 21 (by omega)))
    (order45LexRelabeledColor color 21 (by omega)) 21 (by omega) (by omega)
    (order45Degree21FullMotherAssignment_represents
      (order45LexRelabeledColor color 21 (by omega)))
  exact order45LexRelabeledColor_rows_ordered color 21 (by omega) (by omega)

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherAssignment_lexSorted_after_relabel
    (color : Coloring 45) :
    Order45CrossRowsLexSorted 76651 22
      (order45Degree22FullMotherAssignment
        (order45LexRelabeledColor color 22 (by omega))) := by
  apply order45CrossRowsLexSorted_of_color_rows_ordered 76651
    (order45Degree22FullMotherAssignment
      (order45LexRelabeledColor color 22 (by omega)))
    (order45LexRelabeledColor color 22 (by omega)) 22 (by omega) (by omega)
    (order45Degree22FullMotherAssignment_represents
      (order45LexRelabeledColor color 22 (by omega)))
  exact order45LexRelabeledColor_rows_ordered color 22 (by omega) (by omega)

theorem coloringDegreeSum_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (relabeling : IsVertexRelabeling vertexMap) :
    coloringDegreeSum (relabelColoring color vertexMap) =
      coloringDegreeSum color := by
  unfold coloringDegreeSum
  have pointwise :
      (fun vertex : Fin n =>
        coloringDegree (relabelColoring color vertexMap) vertex) =
      (fun vertex : Fin n => coloringDegree color (vertexMap vertex)) := by
    funext vertex
    exact coloringDegree_relabel color vertexMap relabeling vertex
  rw [pointwise]
  have mapped := relabeling.2.map (coloringDegree color)
  simpa [Function.comp_def] using mapped.sum_nat

theorem localNeighborhoodColoring_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (injective : Function.Injective vertexMap)
    (vertex : Fin n) :
    localNeighborhoodColoring (relabelColoring color vertexMap) vertex =
      relabelColoring (localNeighborhoodColoring color (vertexMap vertex))
        vertexMap := by
  funext left right
  have leftVertex : left = vertex ↔ vertexMap left = vertexMap vertex :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  have rightVertex : right = vertex ↔ vertexMap right = vertexMap vertex :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  have leftRight : left = right ↔ vertexMap left = vertexMap right :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  simp only [localNeighborhoodColoring, relabelColoring]
  simp [leftVertex, rightVertex, leftRight]

theorem localDualColoring_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (injective : Function.Injective vertexMap)
    (vertex : Fin n) :
    localDualColoring (relabelColoring color vertexMap) vertex =
      relabelColoring (localDualColoring color (vertexMap vertex))
        vertexMap := by
  funext left right
  have leftVertex : left = vertex ↔ vertexMap left = vertexMap vertex :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  have rightVertex : right = vertex ↔ vertexMap right = vertexMap vertex :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  have leftRight : left = right ↔ vertexMap left = vertexMap right :=
    ⟨fun equal => congrArg vertexMap equal, fun equal => injective equal⟩
  simp only [localDualColoring, relabelColoring]
  simp [leftVertex, rightVertex, leftRight]

set_option maxRecDepth 100000 in
theorem HasOrder45LocalEdgeCounts.relabel (color : Coloring 45)
    (vertexMap : Fin 45 → Fin 45) (relabeling : IsVertexRelabeling vertexMap)
    (vertex : Fin 45) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color (vertexMap vertex)
      edgesH edgesJ) :
    HasOrder45LocalEdgeCounts (relabelColoring color vertexMap) vertex
      edgesH edgesJ := by
  rcases counts with ⟨hCount, jCount, score⟩
  constructor
  · rw [localNeighborhoodColoring_relabel color vertexMap relabeling.1 vertex,
      coloringDegreeSum_relabel
        (localNeighborhoodColoring color (vertexMap vertex)) vertexMap
          relabeling]
    exact hCount
  constructor
  · rw [localDualColoring_relabel color vertexMap relabeling.1 vertex,
      coloringDegreeSum_relabel
        (localDualColoring color (vertexMap vertex)) vertexMap relabeling]
    exact jCount
  · rw [localExcessScore_relabel color vertexMap relabeling vertex,
      coloringDegree_relabel color vertexMap relabeling vertex]
    exact score

set_option maxRecDepth 100000 in
theorem order45LexRelabeledColor_localEdgeCounts
    (color : Coloring 45) (degree : Nat) (degreeBound : degree ≤ 44)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    HasOrder45LocalEdgeCounts
      (order45LexRelabeledColor color degree degreeBound) 0 edgesH edgesJ := by
  apply HasOrder45LocalEdgeCounts.relabel color
    (order45LexVertexMap color degree degreeBound)
    (order45LexVertexMap_isVertexRelabeling color degree degreeBound) 0
      edgesH edgesJ
  simpa using counts

set_option maxRecDepth 100000 in
theorem order45Degree20FullMotherFormula_complete
    (ramsey fixedFormula : CnfFormula (78697 + 1))
    (ramseyShape : IsOrder45RamseyFormula 78697 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 78697 20 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25) :
    CatalogBoundedDenseExcessCnfComplete
      20 226 68 100 116 132
      (order45Degree20FullMotherFormula ramsey fixedFormula) := by
  intro color simple ramseyFree edgesH edgesJ fixed counts dense hLower hUpper
    jLower jUpper
  let relabeled := order45LexRelabeledColor color 20 (by omega)
  have relabeling := order45LexVertexMap_isVertexRelabeling color 20 (by omega)
  have relabeledSimple : IsSimpleColoring relabeled := by
    exact relabelColoring_isSimple color
      (order45LexVertexMap color 20 (by omega)) simple
  have relabeledFree : IsRamseyFree55 relabeled := by
    exact ramseyFree55_relabel color
      (order45LexVertexMap color 20 (by omega)) relabeling.1 simple ramseyFree
  have relabeledFixed : HasFixedStar relabeled 20 := by
    exact order45LexRelabeledColor_hasFixedStar color 20 (by omega) fixed
  have relabeledCounts : HasOrder45LocalEdgeCounts relabeled 0 edgesH edgesJ := by
    exact order45LexRelabeledColor_localEdgeCounts color 20 (by omega)
      edgesH edgesJ counts
  refine ⟨order45Degree20FullMotherAssignment relabeled, ?_⟩
  exact order45Degree20FullMotherFormula_satisfied ramsey fixedFormula
    ramseyShape fixedShape r45 relabeled relabeledSimple relabeledFree
    relabeledFixed edgesH edgesJ relabeledCounts hLower hUpper jLower jUpper
    dense (order45Degree20FullMotherAssignment_lexSorted_after_relabel color)

set_option maxRecDepth 100000 in
theorem order45Degree21FullMotherFormula_complete
    (ramsey fixedFormula : CnfFormula (77148 + 1))
    (ramseyShape : IsOrder45RamseyFormula 77148 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 77148 21 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25) :
    CatalogBoundedDenseExcessCnfComplete
      21 222 77 107 101 122
      (order45Degree21FullMotherFormula ramsey fixedFormula) := by
  intro color simple ramseyFree edgesH edgesJ fixed counts dense hLower hUpper
    jLower jUpper
  let relabeled := order45LexRelabeledColor color 21 (by omega)
  have relabeling := order45LexVertexMap_isVertexRelabeling color 21 (by omega)
  have relabeledSimple : IsSimpleColoring relabeled := by
    exact relabelColoring_isSimple color
      (order45LexVertexMap color 21 (by omega)) simple
  have relabeledFree : IsRamseyFree55 relabeled := by
    exact ramseyFree55_relabel color
      (order45LexVertexMap color 21 (by omega)) relabeling.1 simple ramseyFree
  have relabeledFixed : HasFixedStar relabeled 21 := by
    exact order45LexRelabeledColor_hasFixedStar color 21 (by omega) fixed
  have relabeledCounts : HasOrder45LocalEdgeCounts relabeled 0 edgesH edgesJ := by
    exact order45LexRelabeledColor_localEdgeCounts color 21 (by omega)
      edgesH edgesJ counts
  refine ⟨order45Degree21FullMotherAssignment relabeled, ?_⟩
  exact order45Degree21FullMotherFormula_satisfied ramsey fixedFormula
    ramseyShape fixedShape r45 relabeled relabeledSimple relabeledFree
    relabeledFixed edgesH edgesJ relabeledCounts hLower hUpper jLower jUpper
    dense (order45Degree21FullMotherAssignment_lexSorted_after_relabel color)

set_option maxRecDepth 100000 in
theorem order45Degree22FullMotherFormula_complete
    (ramsey fixedFormula : CnfFormula (76651 + 1))
    (ramseyShape : IsOrder45RamseyFormula 76651 ramsey)
    (fixedShape : IsOrder45FixedStarFormula 76651 22 fixedFormula)
    (r45 : ForcesRed4OrBlue5 25) :
    CatalogBoundedDenseExcessCnfComplete
      22 220 88 114 88 114
      (order45Degree22FullMotherFormula ramsey fixedFormula) := by
  intro color simple ramseyFree edgesH edgesJ fixed counts dense hLower hUpper
    jLower jUpper
  let relabeled := order45LexRelabeledColor color 22 (by omega)
  have relabeling := order45LexVertexMap_isVertexRelabeling color 22 (by omega)
  have relabeledSimple : IsSimpleColoring relabeled := by
    exact relabelColoring_isSimple color
      (order45LexVertexMap color 22 (by omega)) simple
  have relabeledFree : IsRamseyFree55 relabeled := by
    exact ramseyFree55_relabel color
      (order45LexVertexMap color 22 (by omega)) relabeling.1 simple ramseyFree
  have relabeledFixed : HasFixedStar relabeled 22 := by
    exact order45LexRelabeledColor_hasFixedStar color 22 (by omega) fixed
  have relabeledCounts : HasOrder45LocalEdgeCounts relabeled 0 edgesH edgesJ := by
    exact order45LexRelabeledColor_localEdgeCounts color 22 (by omega)
      edgesH edgesJ counts
  refine ⟨order45Degree22FullMotherAssignment relabeled, ?_⟩
  exact order45Degree22FullMotherFormula_satisfied ramsey fixedFormula
    ramseyShape fixedShape r45 relabeled relabeledSimple relabeledFree
    relabeledFixed edgesH edgesJ relabeledCounts hLower hUpper jLower jUpper
    dense (order45Degree22FullMotherAssignment_lexSorted_after_relabel color)

#print axioms order45ColorCrossRowKey_le_implication
#print axioms order45SortedNeighborMap_injective
#print axioms order45SortedNeighborMap_keys_ordered
#print axioms order45LexVertexMap_injective
#print axioms order45LexVertexMap_isVertexRelabeling
#print axioms order45LexRelabeledColor_cross_entry
#print axioms order45LexRelabeledColor_rows_ordered
#print axioms order45LexRelabeledColor_hasFixedStar
#print axioms LiteralPrefixEqual.at
#print axioms order45CrossRowInput_holds_iff
#print axioms order45CrossRowsLexSorted_of_color_rows_ordered
#print axioms order45Degree20FullMotherAssignment_lexSorted_after_relabel
#print axioms order45Degree21FullMotherAssignment_lexSorted_after_relabel
#print axioms order45Degree22FullMotherAssignment_lexSorted_after_relabel
#print axioms coloringDegreeSum_relabel
#print axioms localNeighborhoodColoring_relabel
#print axioms localDualColoring_relabel
#print axioms HasOrder45LocalEdgeCounts.relabel
#print axioms order45LexRelabeledColor_localEdgeCounts
#print axioms order45Degree20FullMotherFormula_complete
#print axioms order45Degree21FullMotherFormula_complete
#print axioms order45Degree22FullMotherFormula_complete

end Ramsey55
