import Ramsey55.Definitions

namespace Ramsey55

/-- Swap the two edge colours while keeping the ignored diagonal in the
canonical `false` form required by `IsSimpleColoring`. -/
def complementColoring {n : Nat} (color : Coloring n) : Coloring n :=
  fun u v => if u = v then false else !color u v

theorem complementColoring_isSimple {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) :
    IsSimpleColoring (complementColoring color) := by
  constructor
  · intro vertex
    simp [complementColoring]
  · intro left right
    by_cases equal : left = right
    · subst right
      simp [complementColoring]
    · have reverse : right ≠ left := Ne.symm equal
      simp [complementColoring, equal, reverse, simple.2 left right]

/-- Count the `true` edges from `v` to the first `m` labelled vertices.  The
bound is an explicit argument so the definition needs no finite-set library. -/
def coloringDegreeUpTo {n : Nat} (color : Coloring n) (v : Fin n) :
    (m : Nat) → m ≤ n → Nat
  | 0, _ => 0
  | m + 1, within =>
      coloringDegreeUpTo color v m (Nat.le_trans (Nat.le_succ m) within) +
        if color v ⟨m, Nat.lt_of_succ_le within⟩ then 1 else 0

/-- The number of `true` edges incident with `v`.  A simple colouring has a
false diagonal, so scanning all `n` labels counts exactly its graph degree. -/
def coloringDegree {n : Nat} (color : Coloring n) (v : Fin n) : Nat :=
  coloringDegreeUpTo color v n (Nat.le_refl n)

theorem coloringDegreeUpTo_complement_add {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (v : Fin n) :
    ∀ (m : Nat) (within : m ≤ n),
      coloringDegreeUpTo (complementColoring color) v m within +
          coloringDegreeUpTo color v m within =
        m - if v.val < m then 1 else 0 := by
  intro m
  induction m with
  | zero =>
      intro within
      simp [coloringDegreeUpTo]
  | succ m ih =>
      intro within
      have previous : m ≤ n := Nat.le_trans (Nat.le_succ m) within
      have step_lt : m < n := Nat.lt_of_succ_le within
      let u : Fin n := ⟨m, step_lt⟩
      have induction := ih previous
      rw [coloringDegreeUpTo, coloringDegreeUpTo]
      change
        (coloringDegreeUpTo (complementColoring color) v m previous +
              (if complementColoring color v u then 1 else 0)) +
            (coloringDegreeUpTo color v m previous +
              (if color v u then 1 else 0)) =
          m + 1 - if v.val < m + 1 then 1 else 0
      by_cases equal : v = u
      · have value_equal : v.val = m := congrArg Fin.val equal
        have diagonal : color v u = false := by
          rw [equal]
          exact simple.1 u
        have complementDiagonal : complementColoring color v u = false := by
          simp [complementColoring, equal]
        have before : ¬ v.val < m := by omega
        have after : v.val < m + 1 := by omega
        have induction' :
            coloringDegreeUpTo (complementColoring color) v m previous +
                coloringDegreeUpTo color v m previous = m := by
          simpa [before] using induction
        simpa [complementDiagonal, diagonal, after] using induction'
      · have value_ne : v.val ≠ m := by
          intro value_equal
          apply equal
          exact Fin.ext value_equal
        have complementEdge :
            complementColoring color v u = !color v u := by
          simp [complementColoring, equal]
        by_cases before : v.val < m
        · have after : v.val < m + 1 := by omega
          have induction' :
              coloringDegreeUpTo (complementColoring color) v m previous +
                  coloringDegreeUpTo color v m previous = m - 1 := by
            simpa [before] using induction
          cases edge : color v u <;>
            simp [complementEdge, edge, after]
          all_goals omega
        · have after : ¬ v.val < m + 1 := by omega
          have induction' :
              coloringDegreeUpTo (complementColoring color) v m previous +
                  coloringDegreeUpTo color v m previous = m := by
            simpa [before] using induction
          cases edge : color v u <;>
            simp [complementEdge, edge, after]
          all_goals omega

/-- Colour complementation exchanges the degree of a vertex with its number
of non-neighbours among the other `n - 1` vertices. -/
theorem coloringDegree_complement_add {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (v : Fin n) :
    coloringDegree (complementColoring color) v + coloringDegree color v =
      n - 1 := by
  rw [coloringDegree, coloringDegree,
    coloringDegreeUpTo_complement_add color simple v n (Nat.le_refl n)]
  have : v.val < n := v.isLt
  simp [this]

/-- On 45 vertices, the complement of a degree-24 vertex has degree 20. -/
theorem order45_complement_degree24 (color : Coloring 45)
    (simple : IsSimpleColoring color) (v : Fin 45)
    (degree24 : coloringDegree color v = 24) :
    coloringDegree (complementColoring color) v = 20 := by
  have total := coloringDegree_complement_add color simple v
  omega

theorem monochromatic5_complement_iff {n : Nat} (color : Coloring n)
    (a b c d e : Fin n)
    (ab : a.val < b.val) (bc : b.val < c.val)
    (cd : c.val < d.val) (de : d.val < e.val) :
    Monochromatic5 (complementColoring color) a b c d e ↔
      Monochromatic5 color a b c d e := by
  have neOfValLt : ∀ {left right : Fin n},
      left.val < right.val → left ≠ right := by
    intro left right less equal
    subst right
    omega
  have ac : a.val < c.val := by omega
  have ad : a.val < d.val := by omega
  have ae : a.val < e.val := by omega
  have bd : b.val < d.val := by omega
  have be : b.val < e.val := by omega
  have ce : c.val < e.val := by omega
  simp [Monochromatic5, complementColoring,
    neOfValLt ab, neOfValLt ac, neOfValLt ad, neOfValLt ae,
    neOfValLt bc, neOfValLt bd, neOfValLt be,
    neOfValLt cd, neOfValLt ce, neOfValLt de]

theorem ramseyFree55_complement_iff {n : Nat} (color : Coloring n) :
    IsRamseyFree55 (complementColoring color) ↔ IsRamseyFree55 color := by
  constructor
  · intro complementFree a b c d e ab bc cd de monochromatic
    exact complementFree a b c d e ab bc cd de
      ((monochromatic5_complement_iff color a b c d e ab bc cd de).2
        monochromatic)
  · intro colorFree a b c d e ab bc cd de monochromatic
    exact colorFree a b c d e ab bc cd de
      ((monochromatic5_complement_iff color a b c d e ab bc cd de).1
        monochromatic)

/-- Twice the constant part of the order-45 local excess contribution for a
vertex of degree `degree`.  If `H` is its neighbourhood and `J` is the
complement of its dual neighbourhood, the full doubled contribution is this
constant minus `2 * (e(H) + e(J))`. -/
def twoOrder45LocalExcessConstant (degree : Nat) : Int :=
  let d : Int := degree
  (44 - d) * (43 - d) - d * (45 - 2 * d)

theorem twoOrder45LocalExcessConstant_values :
    twoOrder45LocalExcessConstant 20 = 452 ∧
    twoOrder45LocalExcessConstant 21 = 443 ∧
    twoOrder45LocalExcessConstant 22 = 440 ∧
    twoOrder45LocalExcessConstant 23 = 443 ∧
    twoOrder45LocalExcessConstant 24 = 452 := by
  decide

/-- Arithmetic core of the order-45 degree normalization.  The five counts
sum to 45, while the handshake lemma says that the number of odd-degree
vertices is even.  Hence an even degree 20, 22, or 24 occurs; complementation
turns the degree-24 case into degree 20.  Connecting these counts to an actual
Ramsey-free colouring and proving its 20--24 degree window are separate
graph-theoretic obligations. -/
theorem order45_even_degree_split_from_counts
    (n20 n21 n22 n23 n24 oddPairs : Nat)
    (total : n20 + n21 + n22 + n23 + n24 = 45)
    (oddDegrees : n21 + n23 = 2 * oddPairs) :
    (0 < n20 ∨ 0 < n24) ∨ 0 < n22 := by
  omega

theorem order45_dense_pair_of_nonpositive_degree20
    (edgesH edgesJ : Int)
    (nonpositive : 452 - 2 * (edgesH + edgesJ) ≤ 0) :
    226 ≤ edgesH + edgesJ := by
  omega

theorem order45_dense_pair_of_nonpositive_degree21
    (edgesH edgesJ : Int)
    (nonpositive : 443 - 2 * (edgesH + edgesJ) ≤ 0) :
    222 ≤ edgesH + edgesJ := by
  omega

theorem order45_dense_pair_of_nonpositive_degree22
    (edgesH edgesJ : Int)
    (nonpositive : 440 - 2 * (edgesH + edgesJ) ≤ 0) :
    220 ≤ edgesH + edgesJ := by
  omega

#print axioms order45_even_degree_split_from_counts
#print axioms order45_dense_pair_of_nonpositive_degree20
#print axioms order45_dense_pair_of_nonpositive_degree21
#print axioms order45_dense_pair_of_nonpositive_degree22
#print axioms complementColoring_isSimple
#print axioms coloringDegreeUpTo_complement_add
#print axioms coloringDegree_complement_add
#print axioms order45_complement_degree24
#print axioms monochromatic5_complement_iff
#print axioms ramseyFree55_complement_iff

end Ramsey55
