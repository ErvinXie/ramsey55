import Ramsey55.Order45LocalCatalog
import Ramsey55.Order45Dimacs

namespace Ramsey55

/-- Canonical number of undirected true edges, obtained by scanning the
strict upper triangle one first vertex at a time.  This ordering matches the
pair blocks consumed by the generated DIMACS counters. -/
def coloringEdgeCount : (order : Nat) → Coloring order → Nat
  | 0, _ => 0
  | order + 1, color =>
      (List.ofFn fun i : Fin order => edgeWeight (color 0 i.succ)).sum +
        coloringEdgeCount order (tailColoring color)

/-- The corresponding ordered list of upper-triangle Boolean entries. -/
def coloringUpperEdgeValues : (order : Nat) → Coloring order → List Bool
  | 0, _ => []
  | order + 1, color =>
      List.ofFn (fun i : Fin order => color 0 i.succ) ++
        coloringUpperEdgeValues order (tailColoring color)

theorem coloringEdgeCount_eq_upperValues : ∀ (order : Nat)
    (color : Coloring order),
    coloringEdgeCount order color =
      ((coloringUpperEdgeValues order color).map edgeWeight).sum := by
  intro order
  induction order with
  | zero =>
      intro color
      rfl
  | succ order inductionHypothesis =>
      intro color
      simp only [coloringEdgeCount, coloringUpperEdgeValues, List.map_append,
        List.sum_append]
      rw [inductionHypothesis (tailColoring color)]
      congr 1
      simp [Function.comp_def]

/-- Exact handshake identity for the canonical upper-triangle edge count. -/
theorem coloringDegreeSum_eq_twice_coloringEdgeCount :
    ∀ (order : Nat) (color : Coloring order),
      IsSimpleColoring color →
        coloringDegreeSum color = 2 * coloringEdgeCount order color := by
  intro order
  induction order with
  | zero =>
      intro color simple
      simp [coloringDegreeSum, coloringEdgeCount]
  | succ order inductionHypothesis =>
      intro color simple
      rw [coloringDegreeSum_eq_listColoringDegreeSum,
        listColoringDegreeSum_succ color,
        listColoringDegree_zero_succ color simple,
        listColoringDegree_tail_rows color,
        coloring_cross_sum_eq color simple,
        ← coloringDegreeSum_eq_listColoringDegreeSum (tailColoring color),
        inductionHypothesis (tailColoring color)
          (tailColoring_isSimple color simple)]
      simp only [coloringEdgeCount]
      omega

/-- A consecutive labelled block of an order-45 colouring. -/
def order45BlockColoring (color : Coloring 45) (start order : Nat)
    (within : start + order ≤ 45) : Coloring order := fun i j =>
  color ⟨start + i.val, by omega⟩ ⟨start + j.val, by omega⟩

theorem range_succ_eq_zero_cons_map_succ (length : Nat) :
    List.range (length + 1) =
      0 :: (List.range length).map (fun value => value + 1) := by
  rw [List.range_eq_range', List.range'_succ,
    List.range'_eq_map_range, List.range_eq_range']
  simp [Nat.add_comm]

/-- Recursive decomposition of the exact pair order used by the generator. -/
theorem orderedPairsFrom_succ (start count : Nat) :
    orderedPairsFrom start (count + 1) =
      (List.range count).map (fun rightOffset =>
        (start, start + rightOffset + 1)) ++
      orderedPairsFrom (start + 1) count := by
  rw [orderedPairsFrom, range_succ_eq_zero_cons_map_succ]
  simp only [List.flatMap_cons, List.flatMap_map]
  simp [orderedPairsFrom, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

/-- Evaluate a pair of natural labels safely inside the fixed order 45. -/
def order45NatColor (color : Coloring 45) (left right : Nat) : Bool :=
  if leftInside : left < 45 then
    if rightInside : right < 45 then
      color ⟨left, leftInside⟩ ⟨right, rightInside⟩
    else false
  else false

/-- Boolean primary-edge stream obtained from the generator's pair order. -/
def order45PairValues (color : Coloring 45) (start count : Nat) : List Bool :=
  (orderedPairsFrom start count).map fun pair =>
    order45NatColor color pair.1 pair.2

theorem tailColoring_order45BlockColoring
    (color : Coloring 45) (start order : Nat)
    (within : start + (order + 1) ≤ 45) :
    tailColoring (order45BlockColoring color start (order + 1) within) =
      order45BlockColoring color (start + 1) order (by omega) := by
  funext i j
  unfold tailColoring order45BlockColoring
  congr 1 <;> apply Fin.ext <;> simp <;> omega

/-- The numeric pair generator scans exactly the canonical upper-triangle
stream of the corresponding consecutive graph block. -/
theorem order45PairValues_eq_upperEdgeValues
    (color : Coloring 45) : ∀ (order start : Nat)
    (within : start + order ≤ 45),
    order45PairValues color start order =
      coloringUpperEdgeValues order
        (order45BlockColoring color start order within) := by
  intro order
  induction order with
  | zero =>
      intro start within
      simp [order45PairValues, orderedPairsFrom, coloringUpperEdgeValues]
  | succ order inductionHypothesis =>
      intro start within
      rw [order45PairValues, orderedPairsFrom_succ]
      simp only [List.map_append, List.map_map, coloringUpperEdgeValues]
      have rowEquality :
          (List.range order).map
              (fun rightOffset =>
                order45NatColor color start (start + rightOffset + 1)) =
            List.ofFn (fun i : Fin order =>
              order45BlockColoring color start (order + 1) within 0 i.succ) := by
        apply List.ext_getElem
        · simp
        · intro index leftInside rightInside
          have indexInside : index < order := by simpa using leftInside
          have startInside : start < 45 := by omega
          have endpointInside : start + index + 1 < 45 := by omega
          simp [order45NatColor, order45BlockColoring,
            startInside, endpointInside]
          congr 1 <;> apply Fin.ext <;> simp <;> omega
      change
        (List.range order).map (fun rightOffset =>
            order45NatColor color start (start + rightOffset + 1)) ++
          order45PairValues color (start + 1) order = _
      rw [rowEquality]
      congr 1
      rw [tailColoring_order45BlockColoring color start order within]
      exact inductionHypothesis (start + 1) (by omega)

/-- A primary assignment agrees with the graph on every non-diagonal order-45
edge variable. Auxiliary and counter variables remain unconstrained here. -/
def RepresentsOrder45Primary (maximum : Nat)
    (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45) : Prop :=
  ∀ left right : Nat, left < right → right < 45 →
    (dimacsLiteral maximum
      (orderedEdgeDimacsVariable (left, right)) true).truthValue assignment =
        order45NatColor color left right

theorem lookup_mapped_of_nodup {alpha : Type}
    (key : alpha → Nat) (value : alpha → Bool) :
    ∀ (items : List alpha) (item : alpha),
    (items.map key).Nodup → item ∈ items →
      List.lookup (key item)
        (items.map fun entry => (key entry, value entry)) =
          some (value item) := by
  intro items
  induction items with
  | nil =>
      intro item nodup membership
      simp at membership
  | cons head tail inductionHypothesis =>
      intro item nodup membership
      simp only [List.map_cons, List.nodup_cons] at nodup
      simp only [List.mem_cons] at membership
      rcases membership with equal | membership
      · subst item
        simp
      · have keyNe : key item ≠ key head := by
          intro equal
          apply nodup.1
          rw [List.mem_map]
          exact ⟨item, membership, equal⟩
        have beqFalse : (key item == key head) = false :=
          beq_eq_false_iff_ne.mpr keyNe
        simp [List.lookup, beqFalse,
          inductionHypothesis item nodup.2 membership]

theorem nodup_map_of_injective {alpha beta : Type}
    (mapping : alpha → beta) (injective : Function.Injective mapping) :
    ∀ items : List alpha, items.Nodup → (items.map mapping).Nodup := by
  intro items
  induction items with
  | nil => simp
  | cons head tail inductionHypothesis =>
      intro nodup
      simp only [List.nodup_cons] at nodup
      simp only [List.map_cons, List.nodup_cons]
      constructor
      · intro mappedMembership
        rw [List.mem_map] at mappedMembership
        rcases mappedMembership with
          ⟨tailItem, tailMembership, mappedEqual⟩
        have itemEqual := injective mappedEqual
        subst tailItem
        exact nodup.1 tailMembership
      · exact inductionHypothesis nodup.2

theorem nodup_map_of_nodup_of_injective_on_mem {alpha beta : Type}
    (mapping : alpha → beta) : ∀ items : List alpha,
    items.Nodup →
      (∀ first, first ∈ items → ∀ second, second ∈ items →
        mapping first = mapping second → first = second) →
      (items.map mapping).Nodup := by
  intro items
  induction items with
  | nil => simp
  | cons head tail inductionHypothesis =>
      intro nodup injective
      simp only [List.nodup_cons] at nodup
      simp only [List.map_cons, List.nodup_cons]
      constructor
      · intro mappedMembership
        rw [List.mem_map] at mappedMembership
        rcases mappedMembership with
          ⟨tailItem, tailMembership, mappedEqual⟩
        have itemEqual := injective tailItem (by simp [tailMembership])
          head (by simp) mappedEqual
        subst tailItem
        exact nodup.1 tailMembership
      · apply inductionHypothesis nodup.2
        intro first firstMembership second secondMembership equal
        exact injective first (by simp [firstMembership]) second
          (by simp [secondMembership]) equal

theorem nodup_append_of_nodup_of_disjoint {alpha : Type} :
    ∀ first second : List alpha,
    first.Nodup → second.Nodup →
      (∀ item, item ∈ first → item ∉ second) →
      (first ++ second).Nodup := by
  intro first
  induction first with
  | nil => simp
  | cons head tail inductionHypothesis =>
      intro second firstNodup secondNodup disjoint
      simp only [List.nodup_cons] at firstNodup
      simp only [List.cons_append, List.nodup_cons]
      constructor
      · intro membership
        rw [List.mem_append] at membership
        rcases membership with tailMembership | secondMembership
        · exact firstNodup.1 tailMembership
        · exact disjoint head (by simp) secondMembership
      · apply inductionHypothesis second firstNodup.2 secondNodup
        intro item tailMembership
        exact disjoint item (by simp [tailMembership])

theorem range_nodup_structural : ∀ length : Nat,
    (List.range length).Nodup := by
  intro length
  induction length with
  | zero => simp
  | succ length inductionHypothesis =>
      rw [range_succ_eq_zero_cons_map_succ]
      simp only [List.nodup_cons]
      constructor
      · intro membership
        rw [List.mem_map] at membership
        rcases membership with ⟨value, valueMembership, equal⟩
        omega
      · apply nodup_map_of_injective (fun value => value + 1)
        · intro first second equal
          have reduced : first + 1 = second + 1 := by simpa only using equal
          omega
        · exact inductionHypothesis

theorem orderedPairsFrom_nodup (start count : Nat) :
    (orderedPairsFrom start count).Nodup := by
  induction count generalizing start with
  | zero => simp [orderedPairsFrom]
  | succ count inductionHypothesis =>
      rw [orderedPairsFrom_succ]
      apply nodup_append_of_nodup_of_disjoint
      · apply nodup_map_of_injective
          (fun rightOffset => (start, start + rightOffset + 1))
        · intro first second equal
          have rightEqual := congrArg Prod.snd equal
          simp at rightEqual
          omega
        · exact range_nodup_structural count
      · exact inductionHypothesis (start := start + 1)
      · intro pair rowMembership tailMembership
        simp only [List.mem_map, List.mem_range] at rowMembership
        rcases rowMembership with ⟨rightOffset, rightInside, rfl⟩
        simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range,
          List.mem_map] at tailMembership
        rcases tailMembership with
          ⟨leftOffset, leftInside, secondOffset, secondInside, pairEqual⟩
        have firstEqual := congrArg Prod.fst pairEqual
        simp at firstEqual
        omega

theorem mem_orderedPairsFrom_strict (start count : Nat)
    (pair : Nat × Nat) (membership : pair ∈ orderedPairsFrom start count) :
    pair.1 < pair.2 := by
  simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range,
    List.mem_map] at membership
  rcases membership with
    ⟨leftOffset, leftInside, rightOffset, rightInside, rfl⟩
  omega

/-- The triangular offset before the row with second endpoint `right`. -/
def triangularOffset : Nat → Nat
  | 0 => 0
  | right + 1 => triangularOffset right + right

theorem pairCountFormula_succ (right : Nat) :
    (right + 1) * right / 2 =
      right * (right - 1) / 2 + right := by
  have productIdentity :
      (right + 1) * right = right * (right - 1) + right * 2 := by
    cases right with
    | zero => simp
    | succ right =>
        simp [Nat.add_mul, Nat.mul_add, Nat.mul_comm, Nat.add_assoc, Nat.add_comm,
          Nat.add_left_comm]
  rw [productIdentity, Nat.add_mul_div_right _ right (by omega)]

theorem triangularOffset_eq_pairCountFormula : ∀ right : Nat,
    triangularOffset right = right * (right - 1) / 2 := by
  intro right
  induction right with
  | zero => rfl
  | succ right inductionHypothesis =>
      simp only [triangularOffset]
      rw [inductionHypothesis]
      simpa using (pairCountFormula_succ right).symm

theorem triangularOffset_mono {first second : Nat}
    (bounded : first ≤ second) :
    triangularOffset first ≤ triangularOffset second := by
  induction second generalizing first with
  | zero =>
      have : first = 0 := by omega
      subst first
      exact Nat.le_refl 0
  | succ second inductionHypothesis =>
      by_cases equal : first = second + 1
      · subst first
        exact Nat.le_refl (triangularOffset (second + 1))
      · have firstBounded : first ≤ second := by omega
        exact Nat.le_trans (inductionHypothesis firstBounded) (by
          simp only [triangularOffset]
          omega)

theorem orderedEdgeDimacsVariable_injective_of_strict
    (first second : Nat × Nat)
    (firstStrict : first.1 < first.2)
    (secondStrict : second.1 < second.2)
    (equal : orderedEdgeDimacsVariable first =
      orderedEdgeDimacsVariable second) :
    first = second := by
  change first.2 * (first.2 - 1) / 2 + first.1 + 1 =
    second.2 * (second.2 - 1) / 2 + second.1 + 1 at equal
  rw [← triangularOffset_eq_pairCountFormula,
    ← triangularOffset_eq_pairCountFormula] at equal
  by_cases rightEqual : first.2 = second.2
  · rw [rightEqual] at equal
    have leftEqual : first.1 = second.1 := by omega
    apply Prod.ext <;> assumption
  · by_cases forward : first.2 < second.2
    · have firstUpper :
          triangularOffset first.2 + first.1 + 1 ≤
            triangularOffset (first.2 + 1) := by
          simp only [triangularOffset]
          omega
      have middle := triangularOffset_mono (show first.2 + 1 ≤ second.2 by
        omega)
      have secondLower :
          triangularOffset second.2 <
            triangularOffset second.2 + second.1 + 1 := by omega
      omega
    · have reverse : second.2 < first.2 := by omega
      have secondUpper :
          triangularOffset second.2 + second.1 + 1 ≤
            triangularOffset (second.2 + 1) := by
          simp only [triangularOffset]
          omega
      have middle := triangularOffset_mono (show second.2 + 1 ≤ first.2 by
        omega)
      have firstLower :
          triangularOffset first.2 <
            triangularOffset first.2 + first.1 + 1 := by omega
      omega

theorem order45EdgeIdentifiers_nodup :
    ((orderedPairsFrom 0 45).map orderedEdgeDimacsVariable).Nodup := by
  apply nodup_map_of_nodup_of_injective_on_mem
  · exact orderedPairsFrom_nodup 0 45
  · intro first firstMembership second secondMembership equal
    exact orderedEdgeDimacsVariable_injective_of_strict first second
      (mem_orderedPairsFrom_strict 0 45 first firstMembership)
      (mem_orderedPairsFrom_strict 0 45 second secondMembership) equal

theorem mem_orderedPairsFrom_zero_45 (left right : Nat)
    (ordered : left < right) (inside : right < 45) :
    (left, right) ∈ orderedPairsFrom 0 45 := by
  simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range, List.mem_map]
  refine ⟨left, by omega, right - left - 1, by omega, ?_⟩
  apply Prod.ext <;> simp <;> omega

theorem orderedEdgeDimacsVariable_le_990 (left right : Nat)
    (ordered : left < right) (inside : right < 45) :
    orderedEdgeDimacsVariable (left, right) ≤ 990 := by
  have rightBound : right ≤ 44 := by omega
  have predecessorBound : right - 1 ≤ 43 := by omega
  have productBound : right * (right - 1) ≤ 44 * 43 :=
    Nat.mul_le_mul rightBound predecessorBound
  have quotientBound : right * (right - 1) / 2 ≤ 946 := by
    have divided := Nat.div_le_div_right (c := 2) productBound
    have calculation : 44 * 43 / 2 = 946 := by decide
    rwa [calculation] at divided
  have leftBound : left ≤ 43 := by omega
  change right * (right - 1) / 2 + left + 1 ≤ 990
  omega

/-- Association list assigning every order-45 edge identifier its graph
colour. -/
def order45PrimaryEntries (color : Coloring 45) : List (Nat × Bool) :=
  (orderedPairsFrom 0 45).map fun pair =>
    (orderedEdgeDimacsVariable pair,
      order45NatColor color pair.1 pair.2)

/-- Total assignment with graph primaries filled and every non-primary
variable initially false. Counter and lex auxiliaries can subsequently be
overridden on their disjoint identifier ranges. -/
def order45GraphPrimaryAssignment (maximum : Nat) (color : Coloring 45) :
    CnfAssignment (maximum + 1) := fun index =>
  (List.lookup index.val (order45PrimaryEntries color)).getD false

theorem order45GraphPrimaryAssignment_represents (maximum : Nat)
    (enough : 990 ≤ maximum) (color : Coloring 45) :
    RepresentsOrder45Primary maximum
      (order45GraphPrimaryAssignment maximum color) color := by
  intro left right ordered inside
  have membership := mem_orderedPairsFrom_zero_45 left right ordered inside
  have lookup := lookup_mapped_of_nodup orderedEdgeDimacsVariable
    (fun pair : Nat × Nat => order45NatColor color pair.1 pair.2)
    (orderedPairsFrom 0 45) (left, right) order45EdgeIdentifiers_nodup
    membership
  have identifierBound :=
    orderedEdgeDimacsVariable_le_990 left right ordered inside
  have identifierInside :
      orderedEdgeDimacsVariable (left, right) < maximum + 1 := by omega
  unfold CnfLiteral.truthValue dimacsLiteral order45GraphPrimaryAssignment
  simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside,
    order45PrimaryEntries, lookup]

theorem mem_orderedPairsFrom_bounds (start count : Nat) (pair : Nat × Nat)
    (membership : pair ∈ orderedPairsFrom start count) :
    start ≤ pair.1 ∧ pair.1 < pair.2 ∧ pair.2 < start + count := by
  simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range,
    List.mem_map] at membership
  rcases membership with
    ⟨leftOffset, leftInside, rightOffset, rightInside, rfl⟩
  omega

theorem trueCountPrefix_eq_sum_ofFn (input : Nat → Bool) :
    ∀ length : Nat, trueCountPrefix input length =
      (List.ofFn fun i : Fin length =>
        if input i.val = true then 1 else 0).sum := by
  intro length
  induction length with
  | zero => simp [trueCountPrefix]
  | succ length inductionHypothesis =>
      rw [List.ofFn_succ_last]
      simp only [List.sum_append, List.sum_singleton, trueCountPrefix]
      rw [inductionHypothesis]
      congr 1

theorem counterInputDimacsLiteral_eq_getElem (maximum : Nat)
    (identifiers : List Nat) (positive : Bool) (row : Nat)
    (inside : row < identifiers.length) :
    counterInputDimacsLiteral maximum identifiers positive row =
      dimacsLiteral maximum identifiers[row] positive := by
  simp [counterInputDimacsLiteral, List.getD_eq_getElem?_getD, inside]

theorem primaryPositiveInputTruthValues_eq_pairValues
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (start count : Nat) (within : start + count ≤ 45) :
    List.ofFn (fun i : Fin (orderedPairsFrom start count).length =>
      (counterInputDimacsLiteral maximum
        ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
        true i.val).truthValue assignment) =
      order45PairValues color start count := by
  apply List.ext_getElem
  · simp [order45PairValues]
  · intro index leftInside rightInside
    let pairs := orderedPairsFrom start count
    have indexInside : index < pairs.length := by
      simpa [pairs] using leftInside
    let pair := pairs[index]
    have membership : pair ∈ pairs := List.getElem_mem indexInside
    have bounds := mem_orderedPairsFrom_bounds start count pair
      (by simpa [pairs] using membership)
    have ordered : pair.1 < pair.2 := bounds.2.1
    have rightBound : pair.2 < 45 := by omega
    rw [List.getElem_ofFn]
    rw [show counterInputDimacsLiteral maximum
          ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
          true index =
        dimacsLiteral maximum (orderedEdgeDimacsVariable pair) true by
      simp [counterInputDimacsLiteral, List.getD_eq_getElem?_getD,
        indexInside, pair, pairs]]
    rw [represents pair.1 pair.2 ordered rightBound]
    simp [order45PairValues, pair, pairs]

theorem dimacsLiteral_false_truthValue_eq_not_true
    (maximum identifier : Nat) (assignment : CnfAssignment (maximum + 1)) :
    (dimacsLiteral maximum identifier false).truthValue assignment =
      !((dimacsLiteral maximum identifier true).truthValue assignment) := by
  simp [CnfLiteral.truthValue, dimacsLiteral]

theorem order45NatColor_complement (color : Coloring 45)
    (left right : Nat) (ordered : left < right) (rightBound : right < 45) :
    order45NatColor (complementColoring color) left right =
      !order45NatColor color left right := by
  have leftBound : left < 45 := by omega
  have distinct : (⟨left, leftBound⟩ : Fin 45) ≠ ⟨right, rightBound⟩ := by
    intro equal
    have values := congrArg Fin.val equal
    simp at values
    omega
  simp [order45NatColor, leftBound, rightBound, complementColoring, distinct]

theorem primaryNegativeInputTruthValues_eq_pairValues
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (start count : Nat) (within : start + count ≤ 45) :
    List.ofFn (fun i : Fin (orderedPairsFrom start count).length =>
      (counterInputDimacsLiteral maximum
        ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
        false i.val).truthValue assignment) =
      order45PairValues (complementColoring color) start count := by
  apply List.ext_getElem
  · simp [order45PairValues]
  · intro index leftInside rightInside
    let pairs := orderedPairsFrom start count
    have indexInside : index < pairs.length := by
      simpa [pairs] using leftInside
    let pair := pairs[index]
    have membership : pair ∈ pairs := List.getElem_mem indexInside
    have bounds := mem_orderedPairsFrom_bounds start count pair
      (by simpa [pairs] using membership)
    have ordered : pair.1 < pair.2 := bounds.2.1
    have rightBound : pair.2 < 45 := by omega
    rw [List.getElem_ofFn]
    rw [show counterInputDimacsLiteral maximum
          ((orderedPairsFrom start count).map orderedEdgeDimacsVariable)
          false index =
        dimacsLiteral maximum (orderedEdgeDimacsVariable pair) false by
      simp [counterInputDimacsLiteral, List.getD_eq_getElem?_getD,
        indexInside, pair, pairs]]
    rw [dimacsLiteral_false_truthValue_eq_not_true,
      represents pair.1 pair.2 ordered rightBound,
      ← order45NatColor_complement color pair.1 pair.2 ordered rightBound]
    simp [order45PairValues, pair, pairs]

theorem sequentialCounterPositiveInputCount_eq_blockEdgeCount
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (start count : Nat) (within : start + count ≤ 45) :
    sequentialCounterInputCount assignment
        (counterInputDimacsLiteral maximum
          ((orderedPairsFrom start count).map orderedEdgeDimacsVariable) true)
        (orderedPairsFrom start count).length =
      coloringEdgeCount count
        (order45BlockColoring color start count within) := by
  have values := primaryPositiveInputTruthValues_eq_pairValues maximum
    assignment color represents start count within
  have mapped := congrArg (fun entries : List Bool =>
    (entries.map edgeWeight).sum) values
  rw [order45PairValues_eq_upperEdgeValues color count start within,
    ← coloringEdgeCount_eq_upperValues] at mapped
  rw [sequentialCounterInputCount, trueCountPrefix_eq_sum_ofFn]
  simpa [edgeWeight, Function.comp_def] using mapped

theorem sequentialCounterNegativeInputCount_eq_blockEdgeCount
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (start count : Nat) (within : start + count ≤ 45) :
    sequentialCounterInputCount assignment
        (counterInputDimacsLiteral maximum
          ((orderedPairsFrom start count).map orderedEdgeDimacsVariable) false)
        (orderedPairsFrom start count).length =
      coloringEdgeCount count
        (order45BlockColoring (complementColoring color) start count within) := by
  have values := primaryNegativeInputTruthValues_eq_pairValues maximum
    assignment color represents start count within
  have mapped := congrArg (fun entries : List Bool =>
    (entries.map edgeWeight).sum) values
  rw [order45PairValues_eq_upperEdgeValues (complementColoring color)
    count start within, ← coloringEdgeCount_eq_upperValues] at mapped
  rw [sequentialCounterInputCount, trueCountPrefix_eq_sum_ofFn]
  simpa [edgeWeight, Function.comp_def] using mapped

theorem order45NeighborhoodInduced_eq_block
    (color : Coloring 45) (degree : Nat) (bounded : degree ≤ 44) :
    order45NeighborhoodInduced color degree bounded =
      order45BlockColoring color 1 degree (by omega) := by
  funext i j
  unfold order45NeighborhoodInduced order45BlockColoring relabelColoring
  congr 1 <;> apply Fin.ext <;>
    simp [order45NeighborBlockMap] <;> omega

theorem order45DualInduced_eq_block
    (color : Coloring 45) (degree : Nat) (bounded : degree ≤ 44) :
    order45DualInduced color degree bounded =
      order45BlockColoring (complementColoring color) (degree + 1)
        (44 - degree) (by omega) := by
  funext i j
  unfold order45DualInduced order45BlockColoring relabelColoring
  congr 1 <;> apply Fin.ext <;>
    simp [order45NonneighborBlockMap] <;> omega

/-- The H/J natural numbers in the local excess identity are exactly the
canonical upper-triangle counts of the two consecutive primary-variable
blocks.  The remaining DIMACS bridge only has to show that its input literal
lists scan these values in this order. -/
theorem fixedStar_localEdgeCounts_eq_primaryBlockCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    coloringEdgeCount degree
        (order45BlockColoring color 1 degree (by omega)) = edgesH ∧
      coloringEdgeCount (44 - degree)
        (order45BlockColoring (complementColoring color) (degree + 1)
          (44 - degree) (by omega)) = edgesJ := by
  have hSimple := relabelColoring_isSimple color
    (order45NeighborBlockMap degree bounded) simple
  have jSimple := relabelColoring_isSimple (complementColoring color)
    (order45NonneighborBlockMap degree bounded)
    (complementColoring_isSimple color simple)
  have hHandshake := coloringDegreeSum_eq_twice_coloringEdgeCount degree
    (order45NeighborhoodInduced color degree bounded) hSimple
  have jHandshake := coloringDegreeSum_eq_twice_coloringEdgeCount
    (44 - degree) (order45DualInduced color degree bounded) jSimple
  have hDegreeSum := localNeighborhoodColoring_fixedStar_degreeSum_eq_catalog
    color simple degree bounded fixed
  have jDegreeSum := localDualColoring_fixedStar_degreeSum_eq_catalog
    color simple degree bounded fixed
  rcases counts with ⟨hLocal, jLocal, score⟩
  have hDouble :
      2 * coloringEdgeCount degree
          (order45NeighborhoodInduced color degree bounded) =
        2 * edgesH :=
    hHandshake.symm.trans (hDegreeSum.symm.trans hLocal)
  have jDouble :
      2 * coloringEdgeCount (44 - degree)
          (order45DualInduced color degree bounded) =
        2 * edgesJ :=
    jHandshake.symm.trans (jDegreeSum.symm.trans jLocal)
  have hCount : coloringEdgeCount degree
      (order45NeighborhoodInduced color degree bounded) = edgesH := by omega
  have jCount : coloringEdgeCount (44 - degree)
      (order45DualInduced color degree bounded) = edgesJ := by omega
  constructor
  · rw [← order45NeighborhoodInduced_eq_block color degree bounded]
    exact hCount
  · rw [← order45DualInduced_eq_block color degree bounded]
    exact jCount

/-- Concrete degree-20 DIMACS input streams count exactly the graph-side H/J
edges whenever the primary variables represent the colouring. -/
theorem order45Degree20PrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 20) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (assignment : CnfAssignment (78697 + 1))
    (represents : RepresentsOrder45Primary 78697 assignment color) :
    sequentialCounterInputCount assignment order45Degree20HInput 190 = edgesH ∧
      sequentialCounterInputCount assignment order45Degree20JInput 276 =
        edgesJ := by
  have blockCounts := fixedStar_localEdgeCounts_eq_primaryBlockCounts color
    simple 20 (by omega) fixed edgesH edgesJ counts
  have hSemantic := sequentialCounterPositiveInputCount_eq_blockEdgeCount
    78697 assignment color represents 1 20 (by omega)
  have jSemantic := sequentialCounterNegativeInputCount_eq_blockEdgeCount
    78697 assignment color represents 21 24 (by omega)
  have dimensions := order45InternalInputDimensions
  have hRows : (orderedPairsFrom 1 20).length = 190 := by
    simpa [order45HInputIdentifiers] using dimensions.1
  have jRows : (orderedPairsFrom 21 24).length = 276 := by
    simpa [order45JInputIdentifiers] using dimensions.2.1
  constructor
  · calc
      sequentialCounterInputCount assignment order45Degree20HInput 190 =
          coloringEdgeCount 20
            (order45BlockColoring color 1 20 (by omega)) := by
        simpa [order45Degree20HInput, order45HInputIdentifiers, hRows] using
          hSemantic
      _ = edgesH := blockCounts.1
  · calc
      sequentialCounterInputCount assignment order45Degree20JInput 276 =
          coloringEdgeCount 24
            (order45BlockColoring (complementColoring color) 21 24
              (by omega)) := by
        simpa [order45Degree20JInput, order45JInputIdentifiers, jRows] using
          jSemantic
      _ = edgesJ := by simpa using blockCounts.2

theorem order45Degree21PrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 21) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (assignment : CnfAssignment (77148 + 1))
    (represents : RepresentsOrder45Primary 77148 assignment color) :
    sequentialCounterInputCount assignment order45Degree21HInput 210 = edgesH ∧
      sequentialCounterInputCount assignment order45Degree21JInput 253 =
        edgesJ := by
  have blockCounts := fixedStar_localEdgeCounts_eq_primaryBlockCounts color
    simple 21 (by omega) fixed edgesH edgesJ counts
  have hSemantic := sequentialCounterPositiveInputCount_eq_blockEdgeCount
    77148 assignment color represents 1 21 (by omega)
  have jSemantic := sequentialCounterNegativeInputCount_eq_blockEdgeCount
    77148 assignment color represents 22 23 (by omega)
  have dimensions := order45InternalInputDimensions
  have hRows : (orderedPairsFrom 1 21).length = 210 := by
    simpa [order45HInputIdentifiers] using dimensions.2.2.1
  have jRows : (orderedPairsFrom 22 23).length = 253 := by
    simpa [order45JInputIdentifiers] using dimensions.2.2.2.1
  constructor
  · calc
      sequentialCounterInputCount assignment order45Degree21HInput 210 =
          coloringEdgeCount 21
            (order45BlockColoring color 1 21 (by omega)) := by
        simpa [order45Degree21HInput, order45HInputIdentifiers, hRows] using
          hSemantic
      _ = edgesH := blockCounts.1
  · calc
      sequentialCounterInputCount assignment order45Degree21JInput 253 =
          coloringEdgeCount 23
            (order45BlockColoring (complementColoring color) 22 23
              (by omega)) := by
        simpa [order45Degree21JInput, order45JInputIdentifiers, jRows] using
          jSemantic
      _ = edgesJ := by simpa using blockCounts.2

theorem order45Degree22PrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 22) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ)
    (assignment : CnfAssignment (76651 + 1))
    (represents : RepresentsOrder45Primary 76651 assignment color) :
    sequentialCounterInputCount assignment order45Degree22HInput 231 = edgesH ∧
      sequentialCounterInputCount assignment order45Degree22JInput 231 =
        edgesJ := by
  have blockCounts := fixedStar_localEdgeCounts_eq_primaryBlockCounts color
    simple 22 (by omega) fixed edgesH edgesJ counts
  have hSemantic := sequentialCounterPositiveInputCount_eq_blockEdgeCount
    76651 assignment color represents 1 22 (by omega)
  have jSemantic := sequentialCounterNegativeInputCount_eq_blockEdgeCount
    76651 assignment color represents 23 22 (by omega)
  have dimensions := order45InternalInputDimensions
  have hRows : (orderedPairsFrom 1 22).length = 231 := by
    simpa [order45HInputIdentifiers] using dimensions.2.2.2.2.1
  have jRows : (orderedPairsFrom 23 22).length = 231 := by
    simpa [order45JInputIdentifiers] using dimensions.2.2.2.2.2
  constructor
  · calc
      sequentialCounterInputCount assignment order45Degree22HInput 231 =
          coloringEdgeCount 22
            (order45BlockColoring color 1 22 (by omega)) := by
        simpa [order45Degree22HInput, order45HInputIdentifiers, hRows] using
          hSemantic
      _ = edgesH := blockCounts.1
  · calc
      sequentialCounterInputCount assignment order45Degree22JInput 231 =
          coloringEdgeCount 22
            (order45BlockColoring (complementColoring color) 23 22
              (by omega)) := by
        simpa [order45Degree22JInput, order45JInputIdentifiers, jRows] using
          jSemantic
      _ = edgesJ := by simpa using blockCounts.2

/-- The canonical graph-primary assignment makes the concrete degree-20
counter inputs count the local catalogue edges, with no representation
premise left for later encoding proofs. -/
theorem order45Degree20GraphPrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 20) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    sequentialCounterInputCount
        (order45GraphPrimaryAssignment 78697 color)
        order45Degree20HInput 190 = edgesH ∧
      sequentialCounterInputCount
        (order45GraphPrimaryAssignment 78697 color)
        order45Degree20JInput 276 = edgesJ := by
  apply order45Degree20PrimaryInputCounts color simple fixed edgesH edgesJ counts
    (order45GraphPrimaryAssignment 78697 color)
  exact order45GraphPrimaryAssignment_represents 78697 (by omega) color

/-- Representation-free degree-21 counterpart. -/
theorem order45Degree21GraphPrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 21) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    sequentialCounterInputCount
        (order45GraphPrimaryAssignment 77148 color)
        order45Degree21HInput 210 = edgesH ∧
      sequentialCounterInputCount
        (order45GraphPrimaryAssignment 77148 color)
        order45Degree21JInput 253 = edgesJ := by
  apply order45Degree21PrimaryInputCounts color simple fixed edgesH edgesJ counts
    (order45GraphPrimaryAssignment 77148 color)
  exact order45GraphPrimaryAssignment_represents 77148 (by omega) color

/-- Representation-free degree-22 counterpart. -/
theorem order45Degree22GraphPrimaryInputCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (fixed : HasFixedStar color 22) (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    sequentialCounterInputCount
        (order45GraphPrimaryAssignment 76651 color)
        order45Degree22HInput 231 = edgesH ∧
      sequentialCounterInputCount
        (order45GraphPrimaryAssignment 76651 color)
        order45Degree22JInput 231 = edgesJ := by
  apply order45Degree22PrimaryInputCounts color simple fixed edgesH edgesJ counts
    (order45GraphPrimaryAssignment 76651 color)
  exact order45GraphPrimaryAssignment_represents 76651 (by omega) color

#print axioms coloringDegreeSum_eq_twice_coloringEdgeCount
#print axioms order45EdgeIdentifiers_nodup
#print axioms order45GraphPrimaryAssignment_represents
#print axioms fixedStar_localEdgeCounts_eq_primaryBlockCounts
#print axioms order45Degree20PrimaryInputCounts
#print axioms order45Degree21PrimaryInputCounts
#print axioms order45Degree22PrimaryInputCounts
#print axioms order45Degree20GraphPrimaryInputCounts
#print axioms order45Degree21GraphPrimaryInputCounts
#print axioms order45Degree22GraphPrimaryInputCounts

end Ramsey55
