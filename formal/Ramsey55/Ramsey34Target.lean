import Ramsey55.RamseySmallBounds

namespace Ramsey55

/-! ## Exact DIMACS target for `R(3,4) ≤ 9` -/

def ramsey34NatColor (color : Coloring 9) (left right : Nat) : Bool :=
  if leftInside : left < 9 then
    if rightInside : right < 9 then
      color ⟨left, leftInside⟩ ⟨right, rightInside⟩
    else false
  else false

theorem ramsey34NatColor_eq (color : Coloring 9) (left right : Nat)
    (leftInside : left < 9) (rightInside : right < 9) :
    ramsey34NatColor color left right =
      color ⟨left, leftInside⟩ ⟨right, rightInside⟩ := by
  simp [ramsey34NatColor, leftInside, rightInside]

def RepresentsRamsey34Primary (assignment : CnfAssignment 37)
    (color : Coloring 9) : Prop :=
  ∀ left right : Nat, left < right → right < 9 →
    (dimacsLiteral 36 (orderedEdgeDimacsVariable (left, right)) true).truthValue
      assignment = ramsey34NatColor color left right

theorem ramsey34EdgeIdentifiers_nodup :
    ((orderedPairsFrom 0 9).map orderedEdgeDimacsVariable).Nodup := by
  apply nodup_map_of_nodup_of_injective_on_mem
  · exact orderedPairsFrom_nodup 0 9
  · intro first firstMembership second secondMembership equal
    exact orderedEdgeDimacsVariable_injective_of_strict first second
      (mem_orderedPairsFrom_strict 0 9 first firstMembership)
      (mem_orderedPairsFrom_strict 0 9 second secondMembership) equal

theorem mem_orderedPairsFrom_zero_9 (left right : Nat)
    (ordered : left < right) (inside : right < 9) :
    (left, right) ∈ orderedPairsFrom 0 9 := by
  simp only [orderedPairsFrom, List.mem_flatMap, List.mem_range, List.mem_map]
  refine ⟨left, by omega, right - left - 1, by omega, ?_⟩
  apply Prod.ext <;> simp <;> omega

theorem orderedEdgeDimacsVariable_le_36 (left right : Nat)
    (ordered : left < right) (inside : right < 9) :
    orderedEdgeDimacsVariable (left, right) ≤ 36 := by
  have rightBound : right ≤ 8 := by omega
  have predecessorBound : right - 1 ≤ 7 := by omega
  have productBound : right * (right - 1) ≤ 8 * 7 :=
    Nat.mul_le_mul rightBound predecessorBound
  have quotientBound : right * (right - 1) / 2 ≤ 28 := by
    have divided := Nat.div_le_div_right (c := 2) productBound
    have calculation : 8 * 7 / 2 = 28 := by decide
    rwa [calculation] at divided
  have leftBound : left ≤ 7 := by omega
  change right * (right - 1) / 2 + left + 1 ≤ 36
  omega

def ramsey34PrimaryEntries (color : Coloring 9) : List (Nat × Bool) :=
  (orderedPairsFrom 0 9).map fun pair =>
    (orderedEdgeDimacsVariable pair,
      ramsey34NatColor color pair.1 pair.2)

def ramsey34PrimaryAssignment (color : Coloring 9) : CnfAssignment 37 :=
  fun index => (List.lookup index.val (ramsey34PrimaryEntries color)).getD false

theorem ramsey34PrimaryAssignment_represents (color : Coloring 9) :
    RepresentsRamsey34Primary (ramsey34PrimaryAssignment color) color := by
  intro left right ordered inside
  have membership := mem_orderedPairsFrom_zero_9 left right ordered inside
  have lookup := lookup_mapped_of_nodup orderedEdgeDimacsVariable
    (fun pair : Nat × Nat => ramsey34NatColor color pair.1 pair.2)
    (orderedPairsFrom 0 9) (left, right) ramsey34EdgeIdentifiers_nodup
    membership
  have identifierBound :=
    orderedEdgeDimacsVariable_le_36 left right ordered inside
  have identifierInside :
      orderedEdgeDimacsVariable (left, right) < 37 := by omega
  unfold CnfLiteral.truthValue dimacsLiteral ramsey34PrimaryAssignment
  simp [Fin.val_ofNat, Nat.mod_eq_of_lt identifierInside,
    ramsey34PrimaryEntries, lookup]

def ramsey34EdgeLiteral (left right : Nat) (positive : Bool) :
    CnfLiteral 37 :=
  dimacsLiteral 36 (orderedEdgeDimacsVariable (left, right)) positive

theorem ramsey34EdgeLiteral_holds_iff
    (assignment : CnfAssignment 37) (color : Coloring 9)
    (represents : RepresentsRamsey34Primary assignment color)
    (left right : Nat) (ordered : left < right) (inside : right < 9)
    (positive : Bool) :
    (ramsey34EdgeLiteral left right positive).Holds assignment ↔
      ramsey34NatColor color left right = positive := by
  unfold ramsey34EdgeLiteral
  rw [← CnfLiteral.truthValue_eq_true_iff_holds]
  cases positive with
  | false =>
      rw [dimacsLiteral_false_truthValue_eq_not_true]
      rw [represents left right ordered inside]
      cases ramsey34NatColor color left right <;> simp
  | true =>
      simpa using represents left right ordered inside

def ramsey34ThreeSetClause (a b c : Nat) : CnfClause 37 :=
  [ramsey34EdgeLiteral a b false,
    ramsey34EdgeLiteral a c false,
    ramsey34EdgeLiteral b c false]

def ramsey34FourSetClause (a b c d : Nat) : CnfClause 37 :=
  [ramsey34EdgeLiteral a b true,
    ramsey34EdgeLiteral a c true,
    ramsey34EdgeLiteral a d true,
    ramsey34EdgeLiteral b c true,
    ramsey34EdgeLiteral b d true,
    ramsey34EdgeLiteral c d true]

def ramsey34ExactFormula : CnfFormula 37 :=
  ((listCombinationsExact (List.range 9) 3).flatMap fun vertices =>
      match vertices with
      | [a, b, c] => [ramsey34ThreeSetClause a b c]
      | _ => [])
    ++
  ((listCombinationsExact (List.range 9) 4).flatMap fun vertices =>
      match vertices with
      | [a, b, c, d] => [ramsey34FourSetClause a b c d]
      | _ => [])

theorem list_eq_three_of_length {alpha : Type} {values : List alpha}
    (length : values.length = 3) :
    ∃ a b c : alpha, values = [a, b, c] := by
  rcases values with _ | ⟨a, values⟩
  · simp at length
  rcases values with _ | ⟨b, values⟩
  · simp at length
  rcases values with _ | ⟨c, values⟩
  · simp at length
  rcases values with _ | ⟨extra, values⟩
  · exact ⟨a, b, c, rfl⟩
  · simp at length

def IsRamsey34Formula (formula : CnfFormula 37) : Prop :=
  ∀ clause ∈ formula,
    (∃ a b c : Nat,
      a < b ∧ b < c ∧ c < 9 ∧ clause = ramsey34ThreeSetClause a b c) ∨
    (∃ a b c d : Nat,
      a < b ∧ b < c ∧ c < d ∧ d < 9 ∧
        clause = ramsey34FourSetClause a b c d)

theorem ramsey34ExactFormula_shape :
    IsRamsey34Formula ramsey34ExactFormula := by
  intro clause membership
  simp only [ramsey34ExactFormula, List.mem_append,
    List.mem_flatMap] at membership
  rcases membership with membership | membership
  · rcases membership with ⟨vertices, verticesMembership, clauseMembership⟩
    rcases mem_listCombinationsExact_length_sublist
        (List.range 9) 3 vertices verticesMembership with
      ⟨verticesLength, verticesSublist⟩
    rcases list_eq_three_of_length verticesLength with ⟨a, b, c, rfl⟩
    have increasing : [a, b, c].Pairwise (· < ·) :=
      List.Pairwise.sublist verticesSublist
        (List.pairwise_lt_range (n := 9))
    have cInside : c < 9 := List.mem_range.mp
      (verticesSublist.subset (by simp))
    simp at increasing
    simp only [List.mem_cons, List.not_mem_nil, or_false] at clauseMembership
    subst clause
    exact Or.inl ⟨a, b, c, by omega, by omega, cInside, rfl⟩
  · rcases membership with ⟨vertices, verticesMembership, clauseMembership⟩
    rcases mem_listCombinationsExact_length_sublist
        (List.range 9) 4 vertices verticesMembership with
      ⟨verticesLength, verticesSublist⟩
    rcases list_eq_four_of_length verticesLength with ⟨a, b, c, d, rfl⟩
    have increasing : [a, b, c, d].Pairwise (· < ·) :=
      List.Pairwise.sublist verticesSublist
        (List.pairwise_lt_range (n := 9))
    have dInside : d < 9 := List.mem_range.mp
      (verticesSublist.subset (by simp))
    simp at increasing
    simp only [List.mem_cons, List.not_mem_nil, or_false] at clauseMembership
    subst clause
    exact Or.inr ⟨a, b, c, d, by omega, by omega, by omega, dInside, rfl⟩

theorem ramsey34ThreeSetClause_satisfied
    (assignment : CnfAssignment 37) (color : Coloring 9)
    (represents : RepresentsRamsey34Primary assignment color)
    (noRed : ¬∃ a b c : Fin 9,
      Distinct3 a b c ∧ RedClique3 color a b c)
    (a b c : Nat) (ab : a < b) (bc : b < c) (inside : c < 9) :
    SatisfiesCnfClause assignment (ramsey34ThreeSetClause a b c) := by
  by_cases satisfied :
      SatisfiesCnfClause assignment (ramsey34ThreeSetClause a b c)
  · exact satisfied
  exfalso
  have edgeTrue (left right : Nat) (ordered : left < right)
      (rightInside : right < 9)
      (membership : ramsey34EdgeLiteral left right false ∈
        ramsey34ThreeSetClause a b c) :
      ramsey34NatColor color left right = true := by
    have notFalse : ramsey34NatColor color left right ≠ false := by
      intro value
      apply satisfied
      exact ⟨ramsey34EdgeLiteral left right false, membership,
        (ramsey34EdgeLiteral_holds_iff assignment color represents
          left right ordered rightInside false).mpr value⟩
    cases value : ramsey34NatColor color left right <;> simp_all
  let av : Fin 9 := ⟨a, by omega⟩
  let bv : Fin 9 := ⟨b, by omega⟩
  let cv : Fin 9 := ⟨c, inside⟩
  apply noRed
  refine ⟨av, bv, cv, ?_, ?_⟩
  · simp [Distinct3, av, bv, cv]
    omega
  · simp only [RedClique3]
    constructor
    · rw [← ramsey34NatColor_eq color a b (by omega) (by omega)]
      exact edgeTrue a b ab (by omega) (by simp [ramsey34ThreeSetClause])
    constructor
    · rw [← ramsey34NatColor_eq color a c (by omega) inside]
      exact edgeTrue a c (by omega) inside
        (by simp [ramsey34ThreeSetClause])
    · rw [← ramsey34NatColor_eq color b c (by omega) inside]
      exact edgeTrue b c bc inside (by simp [ramsey34ThreeSetClause])

theorem ramsey34FourSetClause_satisfied
    (assignment : CnfAssignment 37) (color : Coloring 9)
    (represents : RepresentsRamsey34Primary assignment color)
    (noBlue : ¬∃ a b c d : Fin 9,
      Distinct4 a b c d ∧ BlueClique4 color a b c d)
    (a b c d : Nat) (ab : a < b) (bc : b < c) (cd : c < d)
    (inside : d < 9) :
    SatisfiesCnfClause assignment (ramsey34FourSetClause a b c d) := by
  by_cases satisfied :
      SatisfiesCnfClause assignment (ramsey34FourSetClause a b c d)
  · exact satisfied
  exfalso
  have edgeFalse (left right : Nat) (ordered : left < right)
      (rightInside : right < 9)
      (membership : ramsey34EdgeLiteral left right true ∈
        ramsey34FourSetClause a b c d) :
      ramsey34NatColor color left right = false := by
    have notTrue : ramsey34NatColor color left right ≠ true := by
      intro value
      apply satisfied
      exact ⟨ramsey34EdgeLiteral left right true, membership,
        (ramsey34EdgeLiteral_holds_iff assignment color represents
          left right ordered rightInside true).mpr value⟩
    cases value : ramsey34NatColor color left right <;> simp_all
  let av : Fin 9 := ⟨a, by omega⟩
  let bv : Fin 9 := ⟨b, by omega⟩
  let cv : Fin 9 := ⟨c, by omega⟩
  let dv : Fin 9 := ⟨d, inside⟩
  apply noBlue
  refine ⟨av, bv, cv, dv, ?_, ?_⟩
  · simp [Distinct4, av, bv, cv, dv]
    omega
  · simp only [BlueClique4]
    constructor
    · rw [← ramsey34NatColor_eq color a b (by omega) (by omega)]
      exact edgeFalse a b ab (by omega) (by simp [ramsey34FourSetClause])
    constructor
    · rw [← ramsey34NatColor_eq color a c (by omega) (by omega)]
      exact edgeFalse a c (by omega) (by omega)
        (by simp [ramsey34FourSetClause])
    constructor
    · rw [← ramsey34NatColor_eq color a d (by omega) inside]
      exact edgeFalse a d (by omega) inside
        (by simp [ramsey34FourSetClause])
    constructor
    · rw [← ramsey34NatColor_eq color b c (by omega) (by omega)]
      exact edgeFalse b c bc (by omega) (by simp [ramsey34FourSetClause])
    constructor
    · rw [← ramsey34NatColor_eq color b d (by omega) inside]
      exact edgeFalse b d (by omega) inside
        (by simp [ramsey34FourSetClause])
    · rw [← ramsey34NatColor_eq color c d (by omega) inside]
      exact edgeFalse c d cd inside (by simp [ramsey34FourSetClause])

theorem ramsey34ExactFormula_satisfied
    (formula : CnfFormula 37) (shape : IsRamsey34Formula formula)
    (assignment : CnfAssignment 37) (color : Coloring 9)
    (represents : RepresentsRamsey34Primary assignment color)
    (noRed : ¬∃ a b c : Fin 9,
      Distinct3 a b c ∧ RedClique3 color a b c)
    (noBlue : ¬∃ a b c d : Fin 9,
      Distinct4 a b c d ∧ BlueClique4 color a b c d) :
    SatisfiesCnfFormula assignment formula := by
  intro clause membership
  rcases shape clause membership with
    ⟨a, b, c, ab, bc, inside, rfl⟩ |
      ⟨a, b, c, d, ab, bc, cd, inside, rfl⟩
  · exact ramsey34ThreeSetClause_satisfied assignment color represents noRed
      a b c ab bc inside
  · exact ramsey34FourSetClause_satisfied assignment color represents noBlue
      a b c d ab bc cd inside

theorem forcesRed3OrBlue4_9_of_exactCnfUnsat
    (unsat : CnfFormulaIsUnsat ramsey34ExactFormula) :
    ForcesRed3OrBlue4 9 := by
  intro color simple
  by_cases red : ∃ a b c : Fin 9,
      Distinct3 a b c ∧ RedClique3 color a b c
  · exact Or.inl red
  by_cases blue : ∃ a b c d : Fin 9,
      Distinct4 a b c d ∧ BlueClique4 color a b c d
  · exact Or.inr blue
  exfalso
  apply unsat
  let assignment := ramsey34PrimaryAssignment color
  exact ⟨assignment,
    ramsey34ExactFormula_satisfied ramsey34ExactFormula
      ramsey34ExactFormula_shape assignment color
      (ramsey34PrimaryAssignment_represents color) red blue⟩

theorem forcesRed4OrBlue5_of_r34ExactCnfAndThreeExactFixedStarUnsat
    (r34Unsat : CnfFormulaIsUnsat ramsey34ExactFormula)
    (unsat8 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 8))
    (unsat10 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 10))
    (unsat12 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 12)) :
    ForcesRed4OrBlue5 25 := by
  exact forcesRed4OrBlue5_of_r34_and_threeExactFixedStarUnsat
    (forcesRed3OrBlue4_9_of_exactCnfUnsat r34Unsat)
    unsat8 unsat10 unsat12

#print axioms ramsey34ExactFormula_shape
#print axioms forcesRed3OrBlue4_9_of_exactCnfUnsat
#print axioms forcesRed4OrBlue5_of_r34ExactCnfAndThreeExactFixedStarUnsat

end Ramsey55
