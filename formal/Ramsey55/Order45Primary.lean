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

#print axioms coloringDegreeSum_eq_twice_coloringEdgeCount
#print axioms fixedStar_localEdgeCounts_eq_primaryBlockCounts
#print axioms order45Degree20PrimaryInputCounts
#print axioms order45Degree21PrimaryInputCounts
#print axioms order45Degree22PrimaryInputCounts

end Ramsey55
