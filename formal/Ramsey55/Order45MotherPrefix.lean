import Ramsey55.Order45CounterAssignment
import Init.Data.List.Nat.Range
import Init.Data.List.Pairwise
import Init.Data.List.Sublist

namespace Ramsey55

def order45EdgeLiteral (maximum left right : Nat) (positive : Bool) :
    CnfLiteral (maximum + 1) :=
  dimacsLiteral maximum (orderedEdgeDimacsVariable (left, right)) positive

/-- One of the two generated ten-literal clauses on an increasing five-set.
`positive = false` forbids a true clique; `positive = true` forbids a false
clique. The literal order matches `itertools.combinations(vertices, 2)`. -/
def order45FiveSetClause (maximum a b c d e : Nat) (positive : Bool) :
    CnfClause (maximum + 1) :=
  [order45EdgeLiteral maximum a b positive,
    order45EdgeLiteral maximum a c positive,
    order45EdgeLiteral maximum a d positive,
    order45EdgeLiteral maximum a e positive,
    order45EdgeLiteral maximum b c positive,
    order45EdgeLiteral maximum b d positive,
    order45EdgeLiteral maximum b e positive,
    order45EdgeLiteral maximum c d positive,
    order45EdgeLiteral maximum c e positive,
    order45EdgeLiteral maximum d e positive]

/-- All `count`-element sublists, in the same include-first order used by
Python's `itertools.combinations`.  Recursion is on the input list so the
second recursive call may retain the requested cardinality. -/
def listCombinationsExact {alpha : Type} :
    List alpha → Nat → List (List alpha)
  | [], 0 => [[]]
  | [], _ + 1 => []
  | _ :: _, 0 => [[]]
  | head :: tail, count + 1 =>
      (listCombinationsExact tail count).map (head :: ·) ++
        listCombinationsExact tail (count + 1)

theorem mem_listCombinationsExact_length_sublist {alpha : Type} :
    ∀ (values : List alpha) (count : Nat) (chosen : List alpha),
      chosen ∈ listCombinationsExact values count →
        chosen.length = count ∧ List.Sublist chosen values := by
  intro values
  induction values with
  | nil =>
      intro count chosen membership
      cases count with
      | zero =>
          simp [listCombinationsExact] at membership
          subst chosen
          exact ⟨rfl, .slnil⟩
      | succ count =>
          simp [listCombinationsExact] at membership
  | cons head tail inductionHypothesis =>
      intro count chosen membership
      cases count with
      | zero =>
          simp [listCombinationsExact] at membership
          subst chosen
          exact ⟨rfl, List.nil_sublist (head :: tail)⟩
      | succ count =>
          simp only [listCombinationsExact, List.mem_append] at membership
          rcases membership with membership | membership
          · rw [List.mem_map] at membership
            rcases membership with ⟨tailChosen, tailMembership, rfl⟩
            rcases inductionHypothesis count tailChosen tailMembership with
              ⟨length, sublist⟩
            exact ⟨by simp [length], sublist.cons_cons head⟩
          · rcases inductionHypothesis (count + 1) chosen membership with
              ⟨length, sublist⟩
            exact ⟨length, sublist.cons head⟩

/-- The exact Ramsey-prefix stream emitted by `ramsey55_clauses(45)`: the
negative clause followed by the positive clause for every increasing
five-set in lexicographic combination order. -/
def order45ExactRamseyFormula (maximum : Nat) :
    CnfFormula (maximum + 1) :=
  (listCombinationsExact (List.range 45) 5).flatMap fun vertices =>
    match vertices with
    | [a, b, c, d, e] =>
        [order45FiveSetClause maximum a b c d e false,
          order45FiveSetClause maximum a b c d e true]
    | _ => []

theorem order45EdgeLiteral_holds_iff
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (left right : Nat) (ordered : left < right) (inside : right < 45)
    (positive : Bool) :
    (order45EdgeLiteral maximum left right positive).Holds assignment ↔
      order45NatColor color left right = positive := by
  unfold order45EdgeLiteral
  rw [← CnfLiteral.truthValue_eq_true_iff_holds]
  cases positive with
  | false =>
      rw [dimacsLiteral_false_truthValue_eq_not_true]
      rw [represents left right ordered inside]
      cases order45NatColor color left right <;> simp
  | true =>
      simpa using represents left right ordered inside

theorem order45FiveSetClause_satisfied
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (ramseyFree : IsRamseyFree55 color)
    (a b c d e : Nat)
    (ab : a < b) (bc : b < c) (cd : c < d) (de : d < e)
    (inside : e < 45) (positive : Bool) :
    SatisfiesCnfClause assignment
      (order45FiveSetClause maximum a b c d e positive) := by
  by_cases satisfied : SatisfiesCnfClause assignment
      (order45FiveSetClause maximum a b c d e positive)
  · exact satisfied
  · exfalso
    have edgeNe (left right : Nat) (ordered : left < right)
        (rightInside : right < 45)
        (membership : order45EdgeLiteral maximum left right positive ∈
          order45FiveSetClause maximum a b c d e positive) :
        order45NatColor color left right ≠ positive := by
      intro equal
      apply satisfied
      exact ⟨order45EdgeLiteral maximum left right positive, membership,
        (order45EdgeLiteral_holds_iff maximum assignment color represents
          left right ordered rightInside positive).mpr equal⟩
    have edgeValue (left right : Nat) (leftInside : left < 45)
        (rightInside : right < 45) (ordered : left < right)
        (membership : order45EdgeLiteral maximum left right positive ∈
          order45FiveSetClause maximum a b c d e positive) :
        color ⟨left, leftInside⟩ ⟨right, rightInside⟩ = !positive := by
      have different := edgeNe left right ordered rightInside membership
      have opposite : order45NatColor color left right = !positive := by
        cases value : order45NatColor color left right <;>
          cases positive <;> simp_all
      simpa [order45NatColor, leftInside, rightInside] using opposite
    let av : Fin 45 := ⟨a, by omega⟩
    let bv : Fin 45 := ⟨b, by omega⟩
    let cv : Fin 45 := ⟨c, by omega⟩
    let dv : Fin 45 := ⟨d, by omega⟩
    let ev : Fin 45 := ⟨e, inside⟩
    have edgeAB : color av bv = !positive := by
      simpa [av, bv] using edgeValue a b (by omega) (by omega) ab
        (by simp [order45FiveSetClause])
    have edgeAC : color av cv = !positive := by
      simpa [av, cv] using edgeValue a c (by omega) (by omega) (by omega)
        (by simp [order45FiveSetClause])
    have edgeAD : color av dv = !positive := by
      simpa [av, dv] using edgeValue a d (by omega) (by omega) (by omega)
        (by simp [order45FiveSetClause])
    have edgeAE : color av ev = !positive := by
      simpa [av, ev] using edgeValue a e (by omega) inside (by omega)
        (by simp [order45FiveSetClause])
    have edgeBC : color bv cv = !positive := by
      simpa [bv, cv] using edgeValue b c (by omega) (by omega) bc
        (by simp [order45FiveSetClause])
    have edgeBD : color bv dv = !positive := by
      simpa [bv, dv] using edgeValue b d (by omega) (by omega) (by omega)
        (by simp [order45FiveSetClause])
    have edgeBE : color bv ev = !positive := by
      simpa [bv, ev] using edgeValue b e (by omega) inside (by omega)
        (by simp [order45FiveSetClause])
    have edgeCD : color cv dv = !positive := by
      simpa [cv, dv] using edgeValue c d (by omega) (by omega) cd
        (by simp [order45FiveSetClause])
    have edgeCE : color cv ev = !positive := by
      simpa [cv, ev] using edgeValue c e (by omega) inside (by omega)
        (by simp [order45FiveSetClause])
    have edgeDE : color dv ev = !positive := by
      simpa [dv, ev] using edgeValue d e (by omega) inside de
        (by simp [order45FiveSetClause])
    apply ramseyFree av bv cv dv ev (by simp [av, bv]; omega)
      (by simp [bv, cv]; omega) (by simp [cv, dv]; omega)
      (by simp [dv, ev]; omega)
    cases positive <;> simp_all [Monochromatic5]

/-- A finite formula consists only of the two generated Ramsey clauses for
valid increasing five-sets. This avoids materializing 2,443,518 clauses in a
Lean list while retaining an exact per-clause data boundary. -/
def IsOrder45RamseyFormula (maximum : Nat)
    (formula : CnfFormula (maximum + 1)) : Prop :=
  ∀ clause ∈ formula, ∃ a b c d e : Nat,
    a < b ∧ b < c ∧ c < d ∧ d < e ∧ e < 45 ∧
      (clause = order45FiveSetClause maximum a b c d e false ∨
        clause = order45FiveSetClause maximum a b c d e true)

theorem order45ExactRamseyFormula_shape (maximum : Nat) :
    IsOrder45RamseyFormula maximum
      (order45ExactRamseyFormula maximum) := by
  intro clause membership
  simp only [order45ExactRamseyFormula, List.mem_flatMap] at membership
  rcases membership with
    ⟨vertices, verticesMembership, clauseMembership⟩
  rcases mem_listCombinationsExact_length_sublist
      (List.range 45) 5 vertices verticesMembership with
    ⟨verticesLength, verticesSublist⟩
  rcases list_eq_five_of_length verticesLength with
    ⟨a, b, c, d, e, rfl⟩
  have increasing : [a, b, c, d, e].Pairwise (· < ·) :=
    List.Pairwise.sublist verticesSublist
      (List.pairwise_lt_range (n := 45))
  have eInside : e < 45 := by
    apply List.mem_range.mp
    exact verticesSublist.subset (by simp)
  simp at increasing
  simp only [List.mem_cons, List.not_mem_nil, or_false] at clauseMembership
  rcases clauseMembership with rfl | rfl
  · exact ⟨a, b, c, d, e, by omega, by omega, by omega, by omega,
      eInside, Or.inl rfl⟩
  · exact ⟨a, b, c, d, e, by omega, by omega, by omega, by omega,
      eInside, Or.inr rfl⟩

theorem order45RamseyFormula_satisfied
    (maximum : Nat) (formula : CnfFormula (maximum + 1))
    (shape : IsOrder45RamseyFormula maximum formula)
    (assignment : CnfAssignment (maximum + 1)) (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (ramseyFree : IsRamseyFree55 color) :
    SatisfiesCnfFormula assignment formula := by
  intro clause membership
  rcases shape clause membership with
    ⟨a, b, c, d, e, ab, bc, cd, de, inside, rfl | rfl⟩
  · exact order45FiveSetClause_satisfied maximum assignment color represents
      ramseyFree a b c d e ab bc cd de inside false
  · exact order45FiveSetClause_satisfied maximum assignment color represents
      ramseyFree a b c d e ab bc cd de inside true

def order45FixedStarClause (maximum degree vertex : Nat) :
    CnfClause (maximum + 1) :=
  [order45EdgeLiteral maximum 0 vertex (decide (vertex ≤ degree))]

/-- The exact 44 unit clauses emitted by `fixed_star_clauses(45, degree)`,
in increasing endpoint order. -/
def order45ExactFixedStarFormula (maximum degree : Nat) :
    CnfFormula (maximum + 1) :=
  (List.range 44).map fun offset =>
    order45FixedStarClause maximum degree (offset + 1)

theorem order45FixedStarClause_satisfied
    (maximum : Nat) (assignment : CnfAssignment (maximum + 1))
    (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (degree vertex : Nat) (fixed : HasFixedStar color degree)
    (positive : 0 < vertex) (inside : vertex < 45) :
    SatisfiesCnfClause assignment
      (order45FixedStarClause maximum degree vertex) := by
  have graphValue : order45NatColor color 0 vertex = decide (vertex ≤ degree) := by
    by_cases neighbor : vertex ≤ degree
    · have edge := fixed.1 ⟨vertex, inside⟩ positive neighbor
      simpa [order45NatColor, inside, neighbor] using edge
    · have degreeLess : degree < vertex := by omega
      have nonedge := fixed.2 ⟨vertex, inside⟩ (by simpa using degreeLess)
      simpa [order45NatColor, inside, neighbor] using nonedge
  exact ⟨order45EdgeLiteral maximum 0 vertex (decide (vertex ≤ degree)),
    by simp [order45FixedStarClause],
    (order45EdgeLiteral_holds_iff maximum assignment color represents
      0 vertex positive inside (decide (vertex ≤ degree))).mpr graphValue⟩

def IsOrder45FixedStarFormula (maximum degree : Nat)
    (formula : CnfFormula (maximum + 1)) : Prop :=
  ∀ clause ∈ formula, ∃ vertex : Nat,
    0 < vertex ∧ vertex < 45 ∧
      clause = order45FixedStarClause maximum degree vertex

theorem order45ExactFixedStarFormula_shape (maximum degree : Nat) :
    IsOrder45FixedStarFormula maximum degree
      (order45ExactFixedStarFormula maximum degree) := by
  intro clause membership
  rw [order45ExactFixedStarFormula, List.mem_map] at membership
  rcases membership with ⟨offset, offsetMembership, rfl⟩
  have offsetBound : offset < 44 := List.mem_range.mp offsetMembership
  exact ⟨offset + 1, by omega, by omega, rfl⟩

@[simp] theorem order45ExactFixedStarFormula_length
    (maximum degree : Nat) :
    (order45ExactFixedStarFormula maximum degree).length = 44 := by
  simp [order45ExactFixedStarFormula]

theorem order45FixedStarFormula_satisfied
    (maximum degree : Nat) (formula : CnfFormula (maximum + 1))
    (shape : IsOrder45FixedStarFormula maximum degree formula)
    (assignment : CnfAssignment (maximum + 1)) (color : Coloring 45)
    (represents : RepresentsOrder45Primary maximum assignment color)
    (fixed : HasFixedStar color degree) :
    SatisfiesCnfFormula assignment formula := by
  intro clause membership
  rcases shape clause membership with ⟨vertex, positive, inside, rfl⟩
  exact order45FixedStarClause_satisfied maximum assignment color represents
    degree vertex fixed positive inside

#print axioms order45FiveSetClause_satisfied
#print axioms mem_listCombinationsExact_length_sublist
#print axioms order45ExactRamseyFormula_shape
#print axioms order45RamseyFormula_satisfied
#print axioms order45FixedStarClause_satisfied
#print axioms order45ExactFixedStarFormula_shape
#print axioms order45FixedStarFormula_satisfied

end Ramsey55
