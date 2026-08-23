import Ramsey55.Order45MotherPrefix

namespace Ramsey55

/-- An injective relabeling preserves the labelled `R(4,5)` property. -/
theorem isRamsey45Coloring_relabel {source target : Nat}
    (color : Coloring source) (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    (ramsey : IsRamsey45Coloring color) :
    IsRamsey45Coloring (relabelColoring color vertexMap) := by
  refine ⟨relabelColoring_isSimple color vertexMap ramsey.1, ?_, ?_⟩
  · intro a b c d distinct red
    exact ramsey.2.1 (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d)
      (Distinct4.map vertexMap injective distinct) (by
        simpa [relabelColoring, RedClique4] using red)
  · intro a b c d e distinct blue
    exact ramsey.2.2 (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d)
      (vertexMap e) (Distinct5.map vertexMap injective distinct) (by
        simpa [relabelColoring, BlueClique5, Monochromatic5] using blue)

/-- Every vertex of a simple order-25 graph has one of the 25 possible
degrees `0, ..., 24`. -/
theorem coloringDegree_lt_25 (color : Coloring 25)
    (simple : IsSimpleColoring color) (vertex : Fin 25) :
    coloringDegree color vertex < 25 := by
  have degreeLength := starNeighborCount color vertex simple
  have filteredBound := List.length_filter_le
    (l := (allVertices 25).erase vertex) (p := fun u => color vertex u)
  have vertexMember : vertex ∈ allVertices 25 :=
    List.mem_ofFn.mpr ⟨vertex, rfl⟩
  have erasedLength : ((allVertices 25).erase vertex).length = 24 := by
    rw [List.length_erase_of_mem vertexMember]
    simp [allVertices]
  rw [erasedLength] at filteredBound
  omega

/-- Exclusion statement for one fixed-star degree in an order-25
`R(4,5)` colouring. -/
def NoRamsey45FixedStar (degree : Nat) : Prop :=
  ∀ color : Coloring 25,
    IsRamsey45Coloring color → HasFixedStar color degree → False

/-- The 25 fixed-star degree cases are a complete symmetry cover of the
order-25 `R(4,5)` upper-bound statement. -/
theorem forcesRed4OrBlue5_of_fixedStarRefutations
    (exclude : ∀ degree : Nat, degree < 25 →
      NoRamsey45FixedStar degree) :
    ForcesRed4OrBlue5 25 := by
  intro color simple
  by_cases red : ∃ a b c d : Fin 25,
      Distinct4 a b c d ∧ RedClique4 color a b c d
  · exact Or.inl red
  by_cases blue : ∃ a b c d e : Fin 25,
      Distinct5 a b c d e ∧ BlueClique5 color a b c d e
  · exact Or.inr blue
  exfalso
  have ramsey : IsRamsey45Coloring color := by
    refine ⟨simple, ?_, ?_⟩
    · intro a b c d distinct clique
      exact red ⟨a, b, c, d, distinct, clique⟩
    · intro a b c d e distinct clique
      exact blue ⟨a, b, c, d, e, distinct, clique⟩
  let degree := coloringDegree color 0
  let normalized := relabelColoring color (starVertexMap color 0)
  have normalizedRamsey : IsRamsey45Coloring normalized := by
    exact isRamsey45Coloring_relabel color (starVertexMap color 0)
      (starVertexMap_isVertexRelabeling color 0).1 ramsey
  have fixed : HasFixedStar normalized degree := by
    exact relabelColoring_starVertexMap_hasFixedStar color 0 simple
  exact exclude degree (coloringDegree_lt_25 color simple 0)
    normalized normalizedRamsey fixed

/-- Graph-to-CNF completeness contract for one direct fixed-star
`R(4,5,25)` branch. -/
def Ramsey45FixedStarCnfComplete {variables : Nat} (degree : Nat)
    (formula : CnfFormula variables) : Prop :=
  ∀ color : Coloring 25,
    IsRamsey45Coloring color → HasFixedStar color degree →
      ∃ assignment, SatisfiesCnfFormula assignment formula

theorem noRamsey45FixedStar_of_cnfUnsat {variables degree : Nat}
    (formula : CnfFormula variables)
    (complete : Ramsey45FixedStarCnfComplete degree formula)
    (unsat : CnfFormulaIsUnsat formula) :
    NoRamsey45FixedStar degree := by
  intro color ramsey fixed
  exact unsat (complete color ramsey fixed)

/-- Certificate-facing reduction for the generated 25-branch family.  The
branch index is exactly the fixed degree at vertex zero after relabeling. -/
theorem forcesRed4OrBlue5_of_fixedStarCnfRefutations
    {variables : Nat} (formulas : Fin 25 → CnfFormula variables)
    (complete : ∀ degree : Fin 25,
      Ramsey45FixedStarCnfComplete degree.val (formulas degree))
    (unsat : ∀ degree : Fin 25, CnfFormulaIsUnsat (formulas degree)) :
    ForcesRed4OrBlue5 25 := by
  apply forcesRed4OrBlue5_of_fixedStarRefutations
  intro degree bounded
  let index : Fin 25 := ⟨degree, bounded⟩
  exact noRamsey45FixedStar_of_cnfUnsat (formulas index)
    (complete index) (unsat index)

/-! ## Classical three-degree reduction -/

def Distinct3 {n : Nat} (a b c : Fin n) : Prop :=
  a ≠ b ∧ a ≠ c ∧ b ≠ c

def RedClique3 {n : Nat} (color : Coloring n) (a b c : Fin n) : Prop :=
  color a b = true ∧ color a c = true ∧ color b c = true

def BlueClique4 {n : Nat} (color : Coloring n)
    (a b c d : Fin n) : Prop :=
  color a b = false ∧ color a c = false ∧ color a d = false ∧
    color b c = false ∧ color b d = false ∧ color c d = false

def ForcesRed3OrBlue5 (n : Nat) : Prop :=
  ∀ color : Coloring n, IsSimpleColoring color →
    (∃ a b c : Fin n, Distinct3 a b c ∧ RedClique3 color a b c) ∨
      (∃ a b c d e : Fin n,
        Distinct5 a b c d e ∧ BlueClique5 color a b c d e)

def ForcesRed4OrBlue4 (n : Nat) : Prop :=
  ∀ color : Coloring n, IsSimpleColoring color →
    (∃ a b c d : Fin n,
      Distinct4 a b c d ∧ RedClique4 color a b c d) ∨
      (∃ a b c d : Fin n,
        Distinct4 a b c d ∧ BlueClique4 color a b c d)

def ramsey45FirstNeighborMap : Fin 14 → Fin 25 :=
  fun i => ⟨i.val + 1, by omega⟩

theorem ramsey45FirstNeighborMap_injective :
    Function.Injective ramsey45FirstNeighborMap := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey45FirstNeighborMap] at values
  omega

def ramsey45FirstNonneighborMap (degree : Nat) (small : degree ≤ 6) :
    Fin 18 → Fin 25 := fun i => ⟨degree + i.val + 1, by omega⟩

theorem ramsey45FirstNonneighborMap_injective (degree : Nat)
    (small : degree ≤ 6) :
    Function.Injective (ramsey45FirstNonneighborMap degree small) := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey45FirstNonneighborMap] at values
  omega

theorem ramsey45_fixedStar_degree_le13
    (r35 : ForcesRed3OrBlue5 14)
    (color : Coloring 25) (ramsey : IsRamsey45Coloring color)
    (degree : Nat) (fixed : HasFixedStar color degree) :
    degree ≤ 13 := by
  by_cases bounded : degree ≤ 13
  · exact bounded
  exfalso
  have degree14 : 14 ≤ degree := by omega
  let induced := relabelColoring color ramsey45FirstNeighborMap
  have inducedSimple : IsSimpleColoring induced :=
    relabelColoring_isSimple color ramsey45FirstNeighborMap ramsey.1
  have neighbor (i : Fin 14) : color 0 (ramsey45FirstNeighborMap i) = true := by
    apply fixed.1
    · simp [ramsey45FirstNeighborMap]
    · simp [ramsey45FirstNeighborMap]
      omega
  have nonzero (i : Fin 14) : (0 : Fin 25) ≠ ramsey45FirstNeighborMap i := by
    intro equal
    have values := congrArg Fin.val equal
    simp [ramsey45FirstNeighborMap] at values
  rcases r35 induced inducedSimple with triangle | blue
  · rcases triangle with ⟨a, b, c, distinct, clique⟩
    have mappedDistinct : Distinct3 (ramsey45FirstNeighborMap a)
        (ramsey45FirstNeighborMap b) (ramsey45FirstNeighborMap c) := by
      rcases distinct with ⟨ab, ac, bc⟩
      exact ⟨fun equal => ab (ramsey45FirstNeighborMap_injective equal),
        fun equal => ac (ramsey45FirstNeighborMap_injective equal),
        fun equal => bc (ramsey45FirstNeighborMap_injective equal)⟩
    have mappedClique : RedClique3 color (ramsey45FirstNeighborMap a)
        (ramsey45FirstNeighborMap b) (ramsey45FirstNeighborMap c) := by
      simpa [induced, relabelColoring, RedClique3] using clique
    apply ramsey.2.1 0 (ramsey45FirstNeighborMap a)
      (ramsey45FirstNeighborMap b) (ramsey45FirstNeighborMap c)
    · exact ⟨nonzero a, nonzero b, nonzero c,
        mappedDistinct.1, mappedDistinct.2.1, mappedDistinct.2.2⟩
    · exact ⟨neighbor a, neighbor b, neighbor c,
        mappedClique.1, mappedClique.2.1, mappedClique.2.2⟩
  · rcases blue with ⟨a, b, c, d, e, distinct, clique⟩
    apply ramsey.2.2 (ramsey45FirstNeighborMap a)
      (ramsey45FirstNeighborMap b) (ramsey45FirstNeighborMap c)
      (ramsey45FirstNeighborMap d) (ramsey45FirstNeighborMap e)
    · exact Distinct5.map ramsey45FirstNeighborMap
        ramsey45FirstNeighborMap_injective distinct
    · simpa [induced, relabelColoring, BlueClique5, Monochromatic5] using clique

theorem ramsey45_fixedStar_degree_ge7
    (r44 : ForcesRed4OrBlue4 18)
    (color : Coloring 25) (ramsey : IsRamsey45Coloring color)
    (degree : Nat) (fixed : HasFixedStar color degree) :
    7 ≤ degree := by
  by_cases bounded : 7 ≤ degree
  · exact bounded
  exfalso
  have small : degree ≤ 6 := by omega
  let vertexMap := ramsey45FirstNonneighborMap degree small
  let induced := relabelColoring color vertexMap
  have inducedSimple : IsSimpleColoring induced :=
    relabelColoring_isSimple color vertexMap ramsey.1
  have nonneighbor (i : Fin 18) : color 0 (vertexMap i) = false := by
    apply fixed.2
    simp [vertexMap, ramsey45FirstNonneighborMap]
    omega
  have nonzero (i : Fin 18) : (0 : Fin 25) ≠ vertexMap i := by
    intro equal
    have values := congrArg Fin.val equal
    simp [vertexMap, ramsey45FirstNonneighborMap] at values
  rcases r44 induced inducedSimple with red | blue
  · rcases red with ⟨a, b, c, d, distinct, clique⟩
    apply ramsey.2.1 (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d)
    · exact Distinct4.map vertexMap
        (ramsey45FirstNonneighborMap_injective degree small) distinct
    · simpa [induced, relabelColoring, RedClique4] using clique
  · rcases blue with ⟨a, b, c, d, distinct, clique⟩
    have mappedDistinct := Distinct4.map vertexMap
      (ramsey45FirstNonneighborMap_injective degree small) distinct
    have mappedBlue : BlueClique4 color (vertexMap a) (vertexMap b)
        (vertexMap c) (vertexMap d) := by
      simpa [induced, relabelColoring, BlueClique4] using clique
    rcases mappedDistinct with ⟨abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
    rcases mappedBlue with ⟨ab, ac, ad, bc, bd, cd⟩
    apply ramsey.2.2 0 (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d)
    · exact ⟨nonzero a, nonzero b, nonzero c, nonzero d,
        abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
    · exact ⟨by simp [Monochromatic5, nonneighbor, ab, ac, ad, bc, bd, cd],
        nonneighbor a⟩

theorem ramsey45_degree_window_of_small_bounds
    (r35 : ForcesRed3OrBlue5 14) (r44 : ForcesRed4OrBlue4 18)
    (color : Coloring 25) (ramsey : IsRamsey45Coloring color) :
    ∀ vertex : Fin 25,
      7 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 13 := by
  intro vertex
  let normalized := relabelColoring color (starVertexMap color vertex)
  have normalizedRamsey : IsRamsey45Coloring normalized :=
    isRamsey45Coloring_relabel color (starVertexMap color vertex)
      (starVertexMap_isVertexRelabeling color vertex).1 ramsey
  have fixed : HasFixedStar normalized (coloringDegree color vertex) :=
    relabelColoring_starVertexMap_hasFixedStar color vertex ramsey.1
  exact ⟨ramsey45_fixedStar_degree_ge7 r44 normalized normalizedRamsey
      (coloringDegree color vertex) fixed,
    ramsey45_fixedStar_degree_le13 r35 normalized normalizedRamsey
      (coloringDegree color vertex) fixed⟩

theorem ramsey45_even_degree_candidate
    (color : Coloring 25) (ramsey : IsRamsey45Coloring color)
    (window : ∀ vertex : Fin 25,
      7 ≤ coloringDegree color vertex ∧ coloringDegree color vertex ≤ 13) :
    ∃ vertex : Fin 25,
      coloringDegree color vertex = 8 ∨
        coloringDegree color vertex = 10 ∨
        coloringDegree color vertex = 12 := by
  letI : Decidable (∃ vertex : Fin 25,
      coloringDegree color vertex = 8 ∨
        coloringDegree color vertex = 10 ∨
        coloringDegree color vertex = 12) := inferInstance
  by_cases candidate : ∃ vertex : Fin 25,
      coloringDegree color vertex = 8 ∨
        coloringDegree color vertex = 10 ∨
        coloringDegree color vertex = 12
  · exact candidate
  · have allOdd : ∀ vertex : Fin 25, ∃ half : Nat,
        coloringDegree color vertex = 2 * half + 1 := by
      intro vertex
      have bounds := window vertex
      have not8 : coloringDegree color vertex ≠ 8 := by
        intro equal
        exact candidate ⟨vertex, Or.inl equal⟩
      have not10 : coloringDegree color vertex ≠ 10 := by
        intro equal
        exact candidate ⟨vertex, Or.inr (Or.inl equal)⟩
      have not12 : coloringDegree color vertex ≠ 12 := by
        intro equal
        exact candidate ⟨vertex, Or.inr (Or.inr equal)⟩
      have alternatives : coloringDegree color vertex = 7 ∨
          coloringDegree color vertex = 9 ∨
          coloringDegree color vertex = 11 ∨
          coloringDegree color vertex = 13 := by omega
      rcases alternatives with degree7 | degree9 | degree11 | degree13
      · exact ⟨3, by omega⟩
      · exact ⟨4, by omega⟩
      · exact ⟨5, by omega⟩
      · exact ⟨6, by omega⟩
    rcases sum_ofFn_of_all_odd
        (fun vertex : Fin 25 => coloringDegree color vertex) allOdd with
      ⟨oddHalf, oddSum⟩
    rcases coloringDegreeSum_even color ramsey.1 with ⟨evenHalf, evenSum⟩
    change (List.ofFn fun vertex : Fin 25 =>
      coloringDegree color vertex).sum = 2 * evenHalf at evenSum
    omega

theorem ramsey45_fixedStar_normalize_three_degrees
    (r35 : ForcesRed3OrBlue5 14) (r44 : ForcesRed4OrBlue4 18)
    (color : Coloring 25) (ramsey : IsRamsey45Coloring color) :
    ∃ normalized : Coloring 25,
      IsRamsey45Coloring normalized ∧
        (HasFixedStar normalized 8 ∨ HasFixedStar normalized 10 ∨
          HasFixedStar normalized 12) := by
  have window := ramsey45_degree_window_of_small_bounds r35 r44 color ramsey
  rcases ramsey45_even_degree_candidate color ramsey window with
    ⟨vertex, degree8 | degree10 | degree12⟩
  all_goals
    let normalized := relabelColoring color (starVertexMap color vertex)
    have normalizedRamsey : IsRamsey45Coloring normalized :=
      isRamsey45Coloring_relabel color (starVertexMap color vertex)
        (starVertexMap_isVertexRelabeling color vertex).1 ramsey
    have fixed : HasFixedStar normalized (coloringDegree color vertex) :=
      relabelColoring_starVertexMap_hasFixedStar color vertex ramsey.1
  · exact ⟨normalized, normalizedRamsey, Or.inl (by simpa [degree8] using fixed)⟩
  · exact ⟨normalized, normalizedRamsey,
      Or.inr (Or.inl (by simpa [degree10] using fixed))⟩
  · exact ⟨normalized, normalizedRamsey,
      Or.inr (Or.inr (by simpa [degree12] using fixed))⟩

theorem forcesRed4OrBlue5_of_threeFixedStarRefutations
    (r35 : ForcesRed3OrBlue5 14) (r44 : ForcesRed4OrBlue4 18)
    (exclude8 : NoRamsey45FixedStar 8)
    (exclude10 : NoRamsey45FixedStar 10)
    (exclude12 : NoRamsey45FixedStar 12) :
    ForcesRed4OrBlue5 25 := by
  intro color simple
  by_cases red : ∃ a b c d : Fin 25,
      Distinct4 a b c d ∧ RedClique4 color a b c d
  · exact Or.inl red
  by_cases blue : ∃ a b c d e : Fin 25,
      Distinct5 a b c d e ∧ BlueClique5 color a b c d e
  · exact Or.inr blue
  exfalso
  have ramsey : IsRamsey45Coloring color := by
    refine ⟨simple, ?_, ?_⟩
    · intro a b c d distinct clique
      exact red ⟨a, b, c, d, distinct, clique⟩
    · intro a b c d e distinct clique
      exact blue ⟨a, b, c, d, e, distinct, clique⟩
  rcases ramsey45_fixedStar_normalize_three_degrees r35 r44 color ramsey with
    ⟨normalized, normalizedRamsey, branch⟩
  rcases branch with fixed8 | fixed10 | fixed12
  · exact exclude8 normalized normalizedRamsey fixed8
  · exact exclude10 normalized normalizedRamsey fixed10
  · exact exclude12 normalized normalizedRamsey fixed12

/-! ## Exact direct order-25 DIMACS encoding -/

def ramsey45NatColor (color : Coloring 25) (left right : Nat) : Bool :=
  if leftInside : left < 25 then
    if rightInside : right < 25 then
      color ⟨left, leftInside⟩ ⟨right, rightInside⟩
    else false
  else false

theorem ramsey45NatColor_eq (color : Coloring 25) (left right : Nat)
    (leftInside : left < 25) (rightInside : right < 25) :
    ramsey45NatColor color left right =
      color ⟨left, leftInside⟩ ⟨right, rightInside⟩ := by
  simp [ramsey45NatColor, leftInside, rightInside]

def RepresentsRamsey45Primary (assignment : CnfAssignment 301)
    (color : Coloring 25) : Prop :=
  ∀ left right : Nat, left < right → right < 25 →
    (dimacsLiteral 300 (orderedEdgeDimacsVariable (left, right)) true).truthValue
      assignment = ramsey45NatColor color left right

theorem ramsey45EdgeIdentifiers_nodup :
    ((orderedPairsFrom 0 25).map orderedEdgeDimacsVariable).Nodup := by
  apply nodup_map_of_nodup_of_injective_on_mem
  · exact orderedPairsFrom_nodup 0 25
  · intro first firstMembership second secondMembership equal
    exact orderedEdgeDimacsVariable_injective_of_strict first second
      (mem_orderedPairsFrom_strict 0 25 first firstMembership)
      (mem_orderedPairsFrom_strict 0 25 second secondMembership) equal

theorem mem_orderedPairsFrom_zero_25 (left right : Nat)
    (ordered : left < right) (inside : right < 25) :
    (left, right) ∈ orderedPairsFrom 0 25 := by
  simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range, List.mem_map]
  refine ⟨left, by omega, right - left - 1, by omega, ?_⟩
  apply Prod.ext <;> simp <;> omega

theorem orderedEdgeDimacsVariable_le_300 (left right : Nat)
    (ordered : left < right) (inside : right < 25) :
    orderedEdgeDimacsVariable (left, right) ≤ 300 := by
  have rightBound : right ≤ 24 := by omega
  have predecessorBound : right - 1 ≤ 23 := by omega
  have productBound : right * (right - 1) ≤ 24 * 23 :=
    Nat.mul_le_mul rightBound predecessorBound
  have quotientBound : right * (right - 1) / 2 ≤ 276 := by
    have divided := Nat.div_le_div_right (c := 2) productBound
    have calculation : 24 * 23 / 2 = 276 := by decide
    rwa [calculation] at divided
  have leftBound : left ≤ 23 := by omega
  change right * (right - 1) / 2 + left + 1 ≤ 300
  omega

def ramsey45PrimaryEntries (color : Coloring 25) : List (Nat × Bool) :=
  (orderedPairsFrom 0 25).map fun pair =>
    (orderedEdgeDimacsVariable pair,
      ramsey45NatColor color pair.1 pair.2)

def ramsey45PrimaryAssignment (color : Coloring 25) : CnfAssignment 301 :=
  fun index => (List.lookup index.val (ramsey45PrimaryEntries color)).getD false

theorem ramsey45PrimaryAssignment_represents (color : Coloring 25) :
    RepresentsRamsey45Primary (ramsey45PrimaryAssignment color) color := by
  intro left right ordered inside
  have membership := mem_orderedPairsFrom_zero_25 left right ordered inside
  have lookup := lookup_mapped_of_nodup orderedEdgeDimacsVariable
    (fun pair : Nat × Nat => ramsey45NatColor color pair.1 pair.2)
    (orderedPairsFrom 0 25) (left, right) ramsey45EdgeIdentifiers_nodup
    membership
  have identifierBound :=
    orderedEdgeDimacsVariable_le_300 left right ordered inside
  have identifierInside :
      orderedEdgeDimacsVariable (left, right) < 301 := by omega
  unfold CnfLiteral.truthValue dimacsLiteral ramsey45PrimaryAssignment
  simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside,
    ramsey45PrimaryEntries, lookup]

def ramsey45EdgeLiteral (left right : Nat) (positive : Bool) :
    CnfLiteral 301 :=
  dimacsLiteral 300 (orderedEdgeDimacsVariable (left, right)) positive

theorem ramsey45EdgeLiteral_holds_iff
    (assignment : CnfAssignment 301) (color : Coloring 25)
    (represents : RepresentsRamsey45Primary assignment color)
    (left right : Nat) (ordered : left < right) (inside : right < 25)
    (positive : Bool) :
    (ramsey45EdgeLiteral left right positive).Holds assignment ↔
      ramsey45NatColor color left right = positive := by
  unfold ramsey45EdgeLiteral
  rw [← CnfLiteral.truthValue_eq_true_iff_holds]
  cases positive with
  | false =>
      rw [dimacsLiteral_false_truthValue_eq_not_true]
      rw [represents left right ordered inside]
      cases ramsey45NatColor color left right <;> simp
  | true =>
      simpa using represents left right ordered inside

def ramsey45FourSetClause (a b c d : Nat) : CnfClause 301 :=
  [ramsey45EdgeLiteral a b false,
    ramsey45EdgeLiteral a c false,
    ramsey45EdgeLiteral a d false,
    ramsey45EdgeLiteral b c false,
    ramsey45EdgeLiteral b d false,
    ramsey45EdgeLiteral c d false]

def ramsey45FiveSetClause (a b c d e : Nat) : CnfClause 301 :=
  [ramsey45EdgeLiteral a b true,
    ramsey45EdgeLiteral a c true,
    ramsey45EdgeLiteral a d true,
    ramsey45EdgeLiteral a e true,
    ramsey45EdgeLiteral b c true,
    ramsey45EdgeLiteral b d true,
    ramsey45EdgeLiteral b e true,
    ramsey45EdgeLiteral c d true,
    ramsey45EdgeLiteral c e true,
    ramsey45EdgeLiteral d e true]

theorem list_eq_four_of_length {alpha : Type} {values : List alpha}
    (length : values.length = 4) :
    ∃ a b c d : alpha, values = [a, b, c, d] := by
  rcases values with _ | ⟨a, values⟩
  · simp at length
  rcases values with _ | ⟨b, values⟩
  · simp at length
  rcases values with _ | ⟨c, values⟩
  · simp at length
  rcases values with _ | ⟨d, values⟩
  · simp at length
  rcases values with _ | ⟨extra, values⟩
  · exact ⟨a, b, c, d, rfl⟩
  · simp at length

def ramsey45ExactBaseFormula : CnfFormula 301 :=
  ((listCombinationsExact (List.range 25) 4).flatMap fun vertices =>
      match vertices with
      | [a, b, c, d] => [ramsey45FourSetClause a b c d]
      | _ => [])
    ++
  ((listCombinationsExact (List.range 25) 5).flatMap fun vertices =>
      match vertices with
      | [a, b, c, d, e] => [ramsey45FiveSetClause a b c d e]
      | _ => [])

def IsRamsey45BaseFormula (formula : CnfFormula 301) : Prop :=
  ∀ clause ∈ formula,
    (∃ a b c d : Nat,
      a < b ∧ b < c ∧ c < d ∧ d < 25 ∧
        clause = ramsey45FourSetClause a b c d) ∨
    (∃ a b c d e : Nat,
      a < b ∧ b < c ∧ c < d ∧ d < e ∧ e < 25 ∧
        clause = ramsey45FiveSetClause a b c d e)

theorem ramsey45ExactBaseFormula_shape :
    IsRamsey45BaseFormula ramsey45ExactBaseFormula := by
  intro clause membership
  simp only [ramsey45ExactBaseFormula, List.mem_append,
    List.mem_flatMap] at membership
  rcases membership with membership | membership
  · rcases membership with ⟨vertices, verticesMembership, clauseMembership⟩
    rcases mem_listCombinationsExact_length_sublist
        (List.range 25) 4 vertices verticesMembership with
      ⟨verticesLength, verticesSublist⟩
    rcases list_eq_four_of_length verticesLength with ⟨a, b, c, d, rfl⟩
    have increasing : [a, b, c, d].Pairwise (· < ·) :=
      List.Pairwise.sublist verticesSublist
        (List.pairwise_lt_range (n := 25))
    have dInside : d < 25 := List.mem_range.mp
      (verticesSublist.subset (by simp))
    simp at increasing
    simp only [List.mem_cons, List.not_mem_nil, or_false] at clauseMembership
    subst clause
    exact Or.inl ⟨a, b, c, d, by omega, by omega, by omega, dInside, rfl⟩
  · rcases membership with ⟨vertices, verticesMembership, clauseMembership⟩
    rcases mem_listCombinationsExact_length_sublist
        (List.range 25) 5 vertices verticesMembership with
      ⟨verticesLength, verticesSublist⟩
    rcases list_eq_five_of_length verticesLength with
      ⟨a, b, c, d, e, rfl⟩
    have increasing : [a, b, c, d, e].Pairwise (· < ·) :=
      List.Pairwise.sublist verticesSublist
        (List.pairwise_lt_range (n := 25))
    have eInside : e < 25 := List.mem_range.mp
      (verticesSublist.subset (by simp))
    simp at increasing
    simp only [List.mem_cons, List.not_mem_nil, or_false] at clauseMembership
    subst clause
    exact Or.inr ⟨a, b, c, d, e, by omega, by omega, by omega, by omega,
      eInside, rfl⟩

theorem ramsey45FourSetClause_satisfied
    (assignment : CnfAssignment 301) (color : Coloring 25)
    (represents : RepresentsRamsey45Primary assignment color)
    (ramsey : IsRamsey45Coloring color)
    (a b c d : Nat) (ab : a < b) (bc : b < c) (cd : c < d)
    (inside : d < 25) :
    SatisfiesCnfClause assignment (ramsey45FourSetClause a b c d) := by
  by_cases satisfied :
      SatisfiesCnfClause assignment (ramsey45FourSetClause a b c d)
  · exact satisfied
  exfalso
  have edgeTrue (left right : Nat) (ordered : left < right)
      (rightInside : right < 25)
      (membership : ramsey45EdgeLiteral left right false ∈
        ramsey45FourSetClause a b c d) :
      ramsey45NatColor color left right = true := by
    have notFalse : ramsey45NatColor color left right ≠ false := by
      intro value
      apply satisfied
      exact ⟨ramsey45EdgeLiteral left right false, membership,
        (ramsey45EdgeLiteral_holds_iff assignment color represents
          left right ordered rightInside false).mpr value⟩
    cases value : ramsey45NatColor color left right <;> simp_all
  let av : Fin 25 := ⟨a, by omega⟩
  let bv : Fin 25 := ⟨b, by omega⟩
  let cv : Fin 25 := ⟨c, by omega⟩
  let dv : Fin 25 := ⟨d, inside⟩
  apply ramsey.2.1 av bv cv dv
  · simp [Distinct4, av, bv, cv, dv]
    omega
  · simp only [RedClique4]
    constructor
    · rw [← ramsey45NatColor_eq color a b (by omega) (by omega)]
      exact edgeTrue a b ab (by omega) (by simp [ramsey45FourSetClause])
    constructor
    · rw [← ramsey45NatColor_eq color a c (by omega) (by omega)]
      exact edgeTrue a c (by omega) (by omega)
        (by simp [ramsey45FourSetClause])
    constructor
    · rw [← ramsey45NatColor_eq color a d (by omega) inside]
      exact edgeTrue a d (by omega) inside (by simp [ramsey45FourSetClause])
    constructor
    · rw [← ramsey45NatColor_eq color b c (by omega) (by omega)]
      exact edgeTrue b c bc (by omega) (by simp [ramsey45FourSetClause])
    constructor
    · rw [← ramsey45NatColor_eq color b d (by omega) inside]
      exact edgeTrue b d (by omega) inside (by simp [ramsey45FourSetClause])
    · rw [← ramsey45NatColor_eq color c d (by omega) inside]
      exact edgeTrue c d cd inside (by simp [ramsey45FourSetClause])

theorem ramsey45FiveSetClause_satisfied
    (assignment : CnfAssignment 301) (color : Coloring 25)
    (represents : RepresentsRamsey45Primary assignment color)
    (ramsey : IsRamsey45Coloring color)
    (a b c d e : Nat) (ab : a < b) (bc : b < c) (cd : c < d)
    (de : d < e) (inside : e < 25) :
    SatisfiesCnfClause assignment (ramsey45FiveSetClause a b c d e) := by
  by_cases satisfied :
      SatisfiesCnfClause assignment (ramsey45FiveSetClause a b c d e)
  · exact satisfied
  exfalso
  have edgeFalse (left right : Nat) (ordered : left < right)
      (rightInside : right < 25)
      (membership : ramsey45EdgeLiteral left right true ∈
        ramsey45FiveSetClause a b c d e) :
      ramsey45NatColor color left right = false := by
    have notTrue : ramsey45NatColor color left right ≠ true := by
      intro value
      apply satisfied
      exact ⟨ramsey45EdgeLiteral left right true, membership,
        (ramsey45EdgeLiteral_holds_iff assignment color represents
          left right ordered rightInside true).mpr value⟩
    cases value : ramsey45NatColor color left right <;> simp_all
  let av : Fin 25 := ⟨a, by omega⟩
  let bv : Fin 25 := ⟨b, by omega⟩
  let cv : Fin 25 := ⟨c, by omega⟩
  let dv : Fin 25 := ⟨d, by omega⟩
  let ev : Fin 25 := ⟨e, inside⟩
  have edgeAB : color av bv = false := by
    rw [← ramsey45NatColor_eq color a b (by omega) (by omega)]
    exact edgeFalse a b ab (by omega) (by simp [ramsey45FiveSetClause])
  have edgeAC : color av cv = false := by
    rw [← ramsey45NatColor_eq color a c (by omega) (by omega)]
    exact edgeFalse a c (by omega) (by omega)
      (by simp [ramsey45FiveSetClause])
  have edgeAD : color av dv = false := by
    rw [← ramsey45NatColor_eq color a d (by omega) (by omega)]
    exact edgeFalse a d (by omega) (by omega)
      (by simp [ramsey45FiveSetClause])
  have edgeAE : color av ev = false := by
    rw [← ramsey45NatColor_eq color a e (by omega) inside]
    exact edgeFalse a e (by omega) inside (by simp [ramsey45FiveSetClause])
  have edgeBC : color bv cv = false := by
    rw [← ramsey45NatColor_eq color b c (by omega) (by omega)]
    exact edgeFalse b c bc (by omega) (by simp [ramsey45FiveSetClause])
  have edgeBD : color bv dv = false := by
    rw [← ramsey45NatColor_eq color b d (by omega) (by omega)]
    exact edgeFalse b d (by omega) (by omega)
      (by simp [ramsey45FiveSetClause])
  have edgeBE : color bv ev = false := by
    rw [← ramsey45NatColor_eq color b e (by omega) inside]
    exact edgeFalse b e (by omega) inside (by simp [ramsey45FiveSetClause])
  have edgeCD : color cv dv = false := by
    rw [← ramsey45NatColor_eq color c d (by omega) (by omega)]
    exact edgeFalse c d cd (by omega) (by simp [ramsey45FiveSetClause])
  have edgeCE : color cv ev = false := by
    rw [← ramsey45NatColor_eq color c e (by omega) inside]
    exact edgeFalse c e (by omega) inside (by simp [ramsey45FiveSetClause])
  have edgeDE : color dv ev = false := by
    rw [← ramsey45NatColor_eq color d e (by omega) inside]
    exact edgeFalse d e de inside (by simp [ramsey45FiveSetClause])
  apply ramsey.2.2 av bv cv dv ev
  · simp [Distinct5, av, bv, cv, dv, ev]
    omega
  · exact ⟨by simp [Monochromatic5, edgeAB, edgeAC, edgeAD, edgeAE,
      edgeBC, edgeBD, edgeBE, edgeCD, edgeCE, edgeDE], edgeAB⟩

theorem ramsey45BaseFormula_satisfied
    (formula : CnfFormula 301) (shape : IsRamsey45BaseFormula formula)
    (assignment : CnfAssignment 301) (color : Coloring 25)
    (represents : RepresentsRamsey45Primary assignment color)
    (ramsey : IsRamsey45Coloring color) :
    SatisfiesCnfFormula assignment formula := by
  intro clause membership
  rcases shape clause membership with
    ⟨a, b, c, d, ab, bc, cd, inside, rfl⟩ |
      ⟨a, b, c, d, e, ab, bc, cd, de, inside, rfl⟩
  · exact ramsey45FourSetClause_satisfied assignment color represents ramsey
      a b c d ab bc cd inside
  · exact ramsey45FiveSetClause_satisfied assignment color represents ramsey
      a b c d e ab bc cd de inside

def ramsey45FixedStarClause (degree vertex : Nat) : CnfClause 301 :=
  [ramsey45EdgeLiteral 0 vertex (decide (vertex ≤ degree))]

def ramsey45ExactFixedStarUnits (degree : Nat) : CnfFormula 301 :=
  (List.range 24).map fun offset =>
    ramsey45FixedStarClause degree (offset + 1)

theorem ramsey45FixedStarUnits_satisfied
    (assignment : CnfAssignment 301) (color : Coloring 25)
    (represents : RepresentsRamsey45Primary assignment color)
    (degree : Nat) (fixed : HasFixedStar color degree) :
    SatisfiesCnfFormula assignment (ramsey45ExactFixedStarUnits degree) := by
  intro clause membership
  rw [ramsey45ExactFixedStarUnits, List.mem_map] at membership
  rcases membership with ⟨offset, offsetMembership, rfl⟩
  have offsetBound : offset < 24 := List.mem_range.mp offsetMembership
  let vertex := offset + 1
  have positive : 0 < vertex := by omega
  have inside : vertex < 25 := by omega
  have graphValue :
      ramsey45NatColor color 0 vertex = decide (vertex ≤ degree) := by
    by_cases neighbor : vertex ≤ degree
    · have edge := fixed.1 ⟨vertex, inside⟩ positive neighbor
      simpa [ramsey45NatColor, inside, neighbor] using edge
    · have beyond : degree < vertex := by omega
      have nonedge := fixed.2 ⟨vertex, inside⟩ (by simpa using beyond)
      simpa [ramsey45NatColor, inside, neighbor] using nonedge
  exact ⟨ramsey45EdgeLiteral 0 vertex (decide (vertex ≤ degree)),
    by simp [ramsey45FixedStarClause, vertex],
    (ramsey45EdgeLiteral_holds_iff assignment color represents 0 vertex
      positive inside (decide (vertex ≤ degree))).mpr graphValue⟩

def ramsey45ExactFixedStarFormula (degree : Nat) : CnfFormula 301 :=
  ramsey45ExactBaseFormula ++ ramsey45ExactFixedStarUnits degree

theorem ramsey45ExactFixedStarCnfComplete (degree : Nat) :
    Ramsey45FixedStarCnfComplete degree
      (ramsey45ExactFixedStarFormula degree) := by
  intro color ramsey fixed
  let assignment := ramsey45PrimaryAssignment color
  refine ⟨assignment, ?_⟩
  intro clause membership
  rw [ramsey45ExactFixedStarFormula, List.mem_append] at membership
  rcases membership with base | star
  · exact ramsey45BaseFormula_satisfied ramsey45ExactBaseFormula
      ramsey45ExactBaseFormula_shape assignment color
      (ramsey45PrimaryAssignment_represents color) ramsey clause base
  · exact ramsey45FixedStarUnits_satisfied assignment color
      (ramsey45PrimaryAssignment_represents color) degree fixed clause star

theorem forcesRed4OrBlue5_of_exactFixedStarUnsat
    (unsat : ∀ degree : Fin 25,
      CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula degree.val)) :
    ForcesRed4OrBlue5 25 := by
  exact forcesRed4OrBlue5_of_fixedStarCnfRefutations
    (fun degree => ramsey45ExactFixedStarFormula degree.val)
    (fun degree => ramsey45ExactFixedStarCnfComplete degree.val) unsat

theorem forcesRed4OrBlue5_of_threeExactFixedStarUnsat
    (r35 : ForcesRed3OrBlue5 14) (r44 : ForcesRed4OrBlue4 18)
    (unsat8 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 8))
    (unsat10 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 10))
    (unsat12 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 12)) :
    ForcesRed4OrBlue5 25 := by
  exact forcesRed4OrBlue5_of_threeFixedStarRefutations r35 r44
    (noRamsey45FixedStar_of_cnfUnsat (ramsey45ExactFixedStarFormula 8)
      (ramsey45ExactFixedStarCnfComplete 8) unsat8)
    (noRamsey45FixedStar_of_cnfUnsat (ramsey45ExactFixedStarFormula 10)
      (ramsey45ExactFixedStarCnfComplete 10) unsat10)
    (noRamsey45FixedStar_of_cnfUnsat (ramsey45ExactFixedStarFormula 12)
      (ramsey45ExactFixedStarCnfComplete 12) unsat12)

#print axioms isRamsey45Coloring_relabel
#print axioms coloringDegree_lt_25
#print axioms forcesRed4OrBlue5_of_fixedStarRefutations
#print axioms forcesRed4OrBlue5_of_fixedStarCnfRefutations
#print axioms ramsey45_degree_window_of_small_bounds
#print axioms ramsey45_fixedStar_normalize_three_degrees
#print axioms forcesRed4OrBlue5_of_threeFixedStarRefutations
#print axioms ramsey45ExactBaseFormula_shape
#print axioms ramsey45ExactFixedStarCnfComplete
#print axioms forcesRed4OrBlue5_of_exactFixedStarUnsat
#print axioms forcesRed4OrBlue5_of_threeExactFixedStarUnsat

end Ramsey55
