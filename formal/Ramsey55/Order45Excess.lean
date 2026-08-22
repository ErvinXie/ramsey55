import Ramsey55.Order45Window

namespace Ramsey55

/-- A symmetric integer contribution attached to an ordered triple.  Summing
over the last two labels gives twice the doubled local excess used by the
order-45 excess formulation.  The factor two lets a mixed neighbour/
nonneighbour pair contribute `-1` in both orders. -/
def orderedTripleExcessScore {n : Nat} (color : Coloring n)
    (v x y : Fin n) : Int :=
  if v = x ∨ v = y ∨ x = y then 0
  else
    match color v x, color v y, color x y with
    | false, false, true => 2
    | true, true, false => 2
    | true, false, _ => -1
    | false, true, _ => -1
    | _, _, _ => 0

/-- Sum the ordered-triple score over the two labels other than the chosen
vertex.  Equality cases vanish inside `orderedTripleExcessScore`, so the
definition can use rectangular finite scans. -/
def localExcessScore {n : Nat} (color : Coloring n) (v : Fin n) : Int :=
  (List.ofFn fun x : Fin n =>
    (List.ofFn fun y : Fin n => orderedTripleExcessScore color v x y).sum).sum

/-- Sum a two-dimensional integer array by rows. -/
def sumFin2 {n m : Nat} (values : Fin n → Fin m → Int) : Int :=
  (List.ofFn fun i : Fin n => (List.ofFn fun j : Fin m => values i j).sum).sum

/-- Sum a three-dimensional integer array in label order. -/
def sumFin3 {n m k : Nat} (values : Fin n → Fin m → Fin k → Int) : Int :=
  (List.ofFn fun i : Fin n => sumFin2 (fun j k => values i j k)).sum

theorem sum_ofFn_add_int {n : Nat} (left right : Fin n → Int) :
    (List.ofFn fun i => left i + right i).sum =
      (List.ofFn left).sum + (List.ofFn right).sum := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ, List.ofFn_succ, List.ofFn_succ]
      simp only [List.sum_cons]
      rw [ih (fun i => left i.succ) (fun i => right i.succ)]
      omega

theorem sum_ofFn_zero_int {n : Nat} :
    (List.ofFn fun _ : Fin n => (0 : Int)).sum = 0 := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ]
      simp [ih]

theorem sumFin2_add {n m : Nat} (left right : Fin n → Fin m → Int) :
    sumFin2 (fun i j => left i j + right i j) =
      sumFin2 left + sumFin2 right := by
  unfold sumFin2
  calc
    (List.ofFn fun i : Fin n =>
        (List.ofFn fun j : Fin m => left i j + right i j).sum).sum =
        (List.ofFn fun i : Fin n =>
          (List.ofFn fun j : Fin m => left i j).sum +
            (List.ofFn fun j : Fin m => right i j).sum).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext i
      exact sum_ofFn_add_int (left i) (right i)
    _ = _ := sum_ofFn_add_int _ _

theorem sumFin2_zero {n m : Nat} :
    sumFin2 (fun _ : Fin n => fun _ : Fin m => (0 : Int)) = 0 := by
  simp [sumFin2, sum_ofFn_zero_int]

/-- Finite rectangular integer sums commute. -/
theorem sumFin2_swap {n m : Nat} (values : Fin n → Fin m → Int) :
    sumFin2 values = sumFin2 (fun j i => values i j) := by
  induction n with
  | zero =>
      simp [sumFin2, sum_ofFn_zero_int]
  | succ n ih =>
      unfold sumFin2
      rw [List.ofFn_succ]
      simp only [List.sum_cons]
      have splitColumns :
          (List.ofFn fun j : Fin m =>
            (List.ofFn fun i : Fin (n + 1) => values i j).sum).sum =
          (List.ofFn fun j : Fin m => values 0 j).sum +
            (List.ofFn fun j : Fin m =>
              (List.ofFn fun i : Fin n => values i.succ j).sum).sum := by
        calc
          _ = (List.ofFn fun j : Fin m =>
              values 0 j +
                (List.ofFn fun i : Fin n => values i.succ j).sum).sum := by
            apply congrArg List.sum
            apply congrArg List.ofFn
            funext j
            rw [List.ofFn_succ]
            simp
          _ = _ := sum_ofFn_add_int _ _
      rw [splitColumns]
      have tailSwap := ih (fun i : Fin n => fun j : Fin m => values i.succ j)
      unfold sumFin2 at tailSwap
      rw [tailSwap]

theorem sumFin3_add {n m k : Nat}
    (left right : Fin n → Fin m → Fin k → Int) :
    sumFin3 (fun i j k => left i j k + right i j k) =
      sumFin3 left + sumFin3 right := by
  unfold sumFin3
  calc
    (List.ofFn fun i : Fin n =>
        sumFin2 (fun j k => left i j k + right i j k)).sum =
        (List.ofFn fun i : Fin n =>
          sumFin2 (left i) + sumFin2 (right i)).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext i
      exact sumFin2_add (left i) (right i)
    _ = _ := sum_ofFn_add_int _ _

theorem sumFin3_zero {n m k : Nat} :
    sumFin3 (fun _ : Fin n => fun _ : Fin m => fun _ : Fin k => (0 : Int)) =
      0 := by
  simp [sumFin3, sumFin2_zero, sum_ofFn_zero_int]

/-- A cyclic permutation of three equally sized finite axes preserves the
total sum. -/
theorem sumFin3_cycle {n : Nat} (values : Fin n → Fin n → Fin n → Int) :
    sumFin3 (fun i j k => values j k i) = sumFin3 values := by
  unfold sumFin3
  calc
    (List.ofFn fun i : Fin n =>
        sumFin2 (fun j k => values j k i)).sum =
        (List.ofFn fun j : Fin n =>
          (List.ofFn fun i : Fin n =>
            (List.ofFn fun k : Fin n => values j k i).sum).sum).sum := by
      exact sumFin2_swap
        (fun i : Fin n => fun j : Fin n =>
          (List.ofFn fun k : Fin n => values j k i).sum)
    _ = (List.ofFn fun j : Fin n =>
          sumFin2 (fun i k => values j k i)).sum := rfl
    _ = (List.ofFn fun j : Fin n =>
          sumFin2 (fun k i => values j k i)).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext j
      exact sumFin2_swap (fun i : Fin n => fun k : Fin n => values j k i)
    _ = (List.ofFn fun j : Fin n =>
          sumFin2 (fun i k => values j i k)).sum := rfl

/-- Every three-label orbit contributes zero.  This is the local four-case
core of the global excess identity: empty and complete triples contribute
zero directly, while a one-edge or two-edge triple contributes `2-1-1`. -/
theorem orderedTripleExcessScore_cycle {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (v x y : Fin n) :
    orderedTripleExcessScore color v x y +
      orderedTripleExcessScore color x y v +
      orderedTripleExcessScore color y v x = 0 := by
  by_cases vx : v = x
  · subst x
    simp [orderedTripleExcessScore]
  by_cases vy : v = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  by_cases xy : x = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  have xv : x ≠ v := Ne.symm vx
  have yv : y ≠ v := Ne.symm vy
  have yx : y ≠ x := Ne.symm xy
  have colorXV : color x v = color v x := simple.2 x v
  have colorYV : color y v = color v y := simple.2 y v
  have colorYX : color y x = color x y := simple.2 y x
  cases colorVX : color v x <;>
    cases colorVY : color v y <;>
    cases colorXY : color x y <;>
    simp [orderedTripleExcessScore, vx, vy, xy, xv, yv, yx,
      colorXV, colorYV, colorYX, colorVX, colorVY, colorXY]

/-- Swapping the two graph colours leaves the symmetric ordered-triple score
unchanged. -/
theorem orderedTripleExcessScore_complement {n : Nat} (color : Coloring n)
    (v x y : Fin n) :
    orderedTripleExcessScore (complementColoring color) v x y =
      orderedTripleExcessScore color v x y := by
  by_cases vx : v = x
  · subst x
    simp [orderedTripleExcessScore]
  by_cases vy : v = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  by_cases xy : x = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  cases colorVX : color v x <;>
    cases colorVY : color v y <;>
    cases colorXY : color x y <;>
    simp [orderedTripleExcessScore, complementColoring, vx, vy, xy,
      colorVX, colorVY, colorXY]

theorem localExcessScore_complement {n : Nat} (color : Coloring n)
    (v : Fin n) :
    localExcessScore (complementColoring color) v =
      localExcessScore color v := by
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext x
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext y
  exact orderedTripleExcessScore_complement color v x y

/-- The global sum of all local excess scores is zero for every finite simple
two-colouring. -/
theorem globalExcessScore_identity {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) :
    (List.ofFn fun v : Fin n => localExcessScore color v).sum = 0 := by
  let score := orderedTripleExcessScore color
  have pointwise : ∀ v x y : Fin n,
      score v x y + score x y v + score y v x = 0 := by
    intro v x y
    exact orderedTripleExcessScore_cycle color simple v x y
  have summedPointwise :
      sumFin3 (fun v x y => score v x y + score x y v + score y v x) = 0 := by
    calc
      _ = sumFin3 (fun _ : Fin n => fun _ : Fin n =>
          fun _ : Fin n => (0 : Int)) := by
        apply congrArg sumFin3
        funext v x y
        exact pointwise v x y
      _ = 0 := sumFin3_zero
  have firstCycle := sumFin3_cycle score
  have secondCycle := sumFin3_cycle (fun v x y => score x y v)
  rw [sumFin3_add, sumFin3_add] at summedPointwise
  have totalScore : sumFin3 score = 0 := by
    rw [firstCycle] at summedPointwise
    have secondCycle' : sumFin3 (fun v x y => score y v x) = sumFin3 score := by
      calc
        _ = sumFin3 (fun v x y => score x y v) := secondCycle
        _ = sumFin3 score := firstCycle
    rw [secondCycle'] at summedPointwise
    omega
  exact totalScore

theorem sum_ofFn_nonnegative_int {n : Nat} (values : Fin n → Int)
    (nonnegative : ∀ i, 0 ≤ values i) :
    0 ≤ (List.ofFn values).sum := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ]
      simp only [List.sum_cons]
      have head := nonnegative (0 : Fin (n + 1))
      have tail := ih (fun i : Fin n => values i.succ) (fun i => nonnegative i.succ)
      omega

theorem sum_ofFn_positive_int {n : Nat} (values : Fin (n + 1) → Int)
    (positive : ∀ i, 0 < values i) :
    0 < (List.ofFn values).sum := by
  rw [List.ofFn_succ]
  simp only [List.sum_cons]
  have head := positive (0 : Fin (n + 1))
  have tail := sum_ofFn_nonnegative_int (fun i : Fin n => values i.succ)
    (fun i => Int.le_of_lt (positive i.succ))
  omega

/-- Every nonempty finite simple colouring has a vertex with nonpositive
local excess score. -/
theorem exists_nonpositive_localExcessScore {n : Nat}
    (color : Coloring (n + 1)) (simple : IsSimpleColoring color) :
    ∃ v : Fin (n + 1), localExcessScore color v ≤ 0 := by
  by_cases witness : ∃ v : Fin (n + 1), localExcessScore color v ≤ 0
  · exact witness
  exfalso
  have positive : ∀ v : Fin (n + 1), 0 < localExcessScore color v := by
    intro v
    have notNonpositive : ¬ localExcessScore color v ≤ 0 := by
      intro nonpositive
      exact witness ⟨v, nonpositive⟩
    omega
  have sumPositive := sum_ofFn_positive_int
    (fun v : Fin (n + 1) => localExcessScore color v) positive
  rw [globalExcessScore_identity color simple] at sumPositive
  omega

/-- Under the order-45 degree window, the global identity supplies a
nonpositive witness of degree 20 through 24. -/
theorem order45_exists_nonpositive_window_vertex
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ v : Fin 45,
      localExcessScore color v ≤ 0 ∧
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24 := by
  rcases exists_nonpositive_localExcessScore color simple with
    ⟨v, nonpositive⟩
  exact ⟨v, nonpositive, window v⟩

/-- Colour complementation normalizes a nonpositive excess witness to degree
20, 21, or 22 while preserving its score. -/
theorem order45_normalize_nonpositive_excess_witness
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        localExcessScore normalized v ≤ 0 ∧
        (coloringDegree normalized v = 20 ∨
          coloringDegree normalized v = 21 ∨
          coloringDegree normalized v = 22) := by
  rcases order45_exists_nonpositive_window_vertex color simple window with
    ⟨v, nonpositive, lower, upper⟩
  have cases : coloringDegree color v = 20 ∨
      coloringDegree color v = 21 ∨ coloringDegree color v = 22 ∨
      coloringDegree color v = 23 ∨ coloringDegree color v = 24 := by
    omega
  rcases cases with degree20 | degree21 | degree22 | degree23 | degree24
  · exact ⟨color, v, simple, ramseyFree, nonpositive, Or.inl degree20⟩
  · exact ⟨color, v, simple, ramseyFree, nonpositive,
      Or.inr (Or.inl degree21)⟩
  · exact ⟨color, v, simple, ramseyFree, nonpositive,
      Or.inr (Or.inr degree22)⟩
  · let normalized := complementColoring color
    have degreeTotal := coloringDegree_complement_add color simple v
    have normalizedFree := (ramseyFree55_complement_iff color).2 ramseyFree
    refine ⟨normalized, v, complementColoring_isSimple color simple,
      normalizedFree, ?_, ?_⟩
    · simpa [normalized, localExcessScore_complement color v] using
        nonpositive
    · right
      left
      simp [normalized]
      omega
  · let normalized := complementColoring color
    have degreeTotal := coloringDegree_complement_add color simple v
    have normalizedFree := (ramseyFree55_complement_iff color).2 ramseyFree
    refine ⟨normalized, v, complementColoring_isSimple color simple,
      normalizedFree, ?_, ?_⟩
    · simpa [normalized, localExcessScore_complement color v] using
        nonpositive
    · left
      simp [normalized]
      omega

/-- Concrete contract still to be discharged by the neighbourhood/J edge
counter bridge.  The score is twice
`twoOrder45LocalExcessConstant d - 2 * (e(H) + e(J))`. -/
def HasOrder45LocalEdgeCounts (color : Coloring 45) (v : Fin 45)
    (edgesH edgesJ : Nat) : Prop :=
  localExcessScore color v =
    2 * (twoOrder45LocalExcessConstant (coloringDegree color v) -
      2 * ((edgesH : Int) + (edgesJ : Int)))

/-- Once the concrete local edge counters satisfy their exact score contract,
the global identity yields one of the three dense excess branches used by the
mother CNFs. -/
theorem order45_exists_dense_excess_branch
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (counted : ∀ candidate : Coloring 45, IsSimpleColoring candidate →
      ∀ v : Fin 45, ∃ edgesH edgesJ : Nat,
        HasOrder45LocalEdgeCounts candidate v edgesH edgesJ) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45, ∃ edgesH edgesJ : Nat,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
      HasOrder45LocalEdgeCounts normalized v edgesH edgesJ ∧
      ((coloringDegree normalized v = 20 ∧ 226 ≤ edgesH + edgesJ) ∨
        (coloringDegree normalized v = 21 ∧ 222 ≤ edgesH + edgesJ) ∨
        (coloringDegree normalized v = 22 ∧ 220 ≤ edgesH + edgesJ)) := by
  rcases order45_normalize_nonpositive_excess_witness color simple ramseyFree
      window with
    ⟨normalized, v, normalizedSimple, normalizedFree, nonpositive,
      degree20 | degree21 | degree22⟩
  · rcases counted normalized normalizedSimple v with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, v, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inl ⟨degree20, ?_⟩⟩
    rw [counts, degree20] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega
  · rcases counted normalized normalizedSimple v with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, v, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inr (Or.inl ⟨degree21, ?_⟩)⟩
    rw [counts, degree21] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega
  · rcases counted normalized normalizedSimple v with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, v, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inr (Or.inr ⟨degree22, ?_⟩)⟩
    rw [counts, degree22] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega

#print axioms globalExcessScore_identity
#print axioms exists_nonpositive_localExcessScore
#print axioms order45_normalize_nonpositive_excess_witness
#print axioms order45_exists_dense_excess_branch

end Ramsey55
