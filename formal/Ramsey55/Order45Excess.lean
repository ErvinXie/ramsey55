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

theorem perm_sum_int {left right : List Int} (permutation : left.Perm right) :
    left.sum = right.sum := by
  induction permutation with
  | nil => rfl
  | cons value permutation ih => simp [ih]
  | swap left right tail => simp; omega
  | trans first second ihFirst ihSecond => exact ihFirst.trans ihSecond

theorem sum_ofFn_comp_vertexRelabeling_int {n : Nat}
    (values : Fin n → Int) (vertexMap : Fin n → Fin n)
    (relabeling : IsVertexRelabeling vertexMap) :
    (List.ofFn fun i : Fin n => values (vertexMap i)).sum =
      (List.ofFn values).sum := by
  have mapped := relabeling.2.map values
  exact perm_sum_int (by
    simpa [Function.comp_def] using mapped)

theorem orderedTripleExcessScore_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (injective : Function.Injective vertexMap)
    (v x y : Fin n) :
    orderedTripleExcessScore (relabelColoring color vertexMap) v x y =
      orderedTripleExcessScore color (vertexMap v) (vertexMap x)
        (vertexMap y) := by
  by_cases vx : v = x
  · subst x
    simp [orderedTripleExcessScore]
  by_cases vy : v = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  by_cases xy : x = y
  · subst y
    simp [orderedTripleExcessScore, vx]
  have mappedVX : vertexMap v ≠ vertexMap x := fun equal => vx (injective equal)
  have mappedVY : vertexMap v ≠ vertexMap y := fun equal => vy (injective equal)
  have mappedXY : vertexMap x ≠ vertexMap y := fun equal => xy (injective equal)
  simp [orderedTripleExcessScore, relabelColoring, vx, vy, xy,
    mappedVX, mappedVY, mappedXY]

/-- A finite relabeling preserves the local excess score at the corresponding
old vertex. -/
theorem localExcessScore_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (relabeling : IsVertexRelabeling vertexMap)
    (v : Fin n) :
    localExcessScore (relabelColoring color vertexMap) v =
      localExcessScore color (vertexMap v) := by
  unfold localExcessScore
  calc
    (List.ofFn fun x : Fin n =>
        (List.ofFn fun y : Fin n =>
          orderedTripleExcessScore (relabelColoring color vertexMap) v x y
        ).sum).sum =
        (List.ofFn fun x : Fin n =>
          (List.ofFn fun y : Fin n =>
            orderedTripleExcessScore color (vertexMap v) (vertexMap x)
              (vertexMap y)).sum).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext x
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext y
      exact orderedTripleExcessScore_relabel color vertexMap
        relabeling.1 v x y
    _ = (List.ofFn fun x : Fin n =>
          (List.ofFn fun y : Fin n =>
            orderedTripleExcessScore color (vertexMap v) (vertexMap x) y
          ).sum).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext x
      exact sum_ofFn_comp_vertexRelabeling_int
        (fun y : Fin n =>
          orderedTripleExcessScore color (vertexMap v) (vertexMap x) y)
        vertexMap relabeling
    _ = (List.ofFn fun x : Fin n =>
          (List.ofFn fun y : Fin n =>
            orderedTripleExcessScore color (vertexMap v) x y).sum).sum := by
      exact sum_ofFn_comp_vertexRelabeling_int
        (fun x : Fin n =>
          (List.ofFn fun y : Fin n =>
            orderedTripleExcessScore color (vertexMap v) x y).sum)
        vertexMap relabeling

/-- Integer-valued edge indicator used to compare local scores with graph
degree sums. -/
def intEdgeWeight (edge : Bool) : Int := if edge then 1 else 0

/-- The graph induced on the neighbours of `v`, padded by isolated labels. -/
def localNeighborhoodColoring {n : Nat} (color : Coloring n) (v : Fin n) :
    Coloring n := fun x y =>
  if x = v ∨ y = v ∨ x = y then false
  else color v x && color v y && color x y

/-- The complement graph induced on the nonneighbours of `v`, padded by
isolated labels.  This is the local J graph used in the excess formula. -/
def localDualColoring {n : Nat} (color : Coloring n) (v : Fin n) :
    Coloring n := fun x y =>
  if x = v ∨ y = v ∨ x = y then false
  else !color v x && !color v y && !color x y

theorem localNeighborhoodColoring_isSimple {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (v : Fin n) :
    IsSimpleColoring (localNeighborhoodColoring color v) := by
  constructor
  · intro x
    simp [localNeighborhoodColoring]
  · intro x y
    by_cases xv : x = v
    · subst x
      simp [localNeighborhoodColoring]
    by_cases yv : y = v
    · subst y
      simp [localNeighborhoodColoring]
    by_cases xy : x = y
    · subst y
      simp [localNeighborhoodColoring]
    have yx : y ≠ x := Ne.symm xy
    simp [localNeighborhoodColoring, xv, yv, xy, yx, simple.2]
    cases color v x <;> cases color v y <;> simp

theorem localDualColoring_isSimple {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (v : Fin n) :
    IsSimpleColoring (localDualColoring color v) := by
  constructor
  · intro x
    simp [localDualColoring]
  · intro x y
    by_cases xv : x = v
    · subst x
      simp [localDualColoring]
    by_cases yv : y = v
    · subst y
      simp [localDualColoring]
    by_cases xy : x = y
    · subst y
      simp [localDualColoring]
    have yx : y ≠ x := Ne.symm xy
    simp [localDualColoring, xv, yv, xy, yx, simple.2]
    cases color v x <;> cases color v y <;> simp

/-- Edge-independent part of one ordered local pair. -/
def orderedPairExcessBase {n : Nat} (color : Coloring n)
    (v x y : Fin n) : Int :=
  if x = v ∨ y = v ∨ x = y then 0
  else
    match color v x, color v y with
    | true, true => 2
    | false, false => 2
    | _, _ => -1

theorem orderedTripleExcessScore_edge_decomposition {n : Nat}
    (color : Coloring n) (v x y : Fin n) :
    orderedTripleExcessScore color v x y +
        2 * intEdgeWeight (localNeighborhoodColoring color v x y) +
        2 * intEdgeWeight (localDualColoring color v x y) =
      orderedPairExcessBase color v x y := by
  by_cases xv : x = v
  · subst x
    simp [orderedTripleExcessScore, orderedPairExcessBase,
      localNeighborhoodColoring, localDualColoring, intEdgeWeight]
  by_cases yv : y = v
  · subst y
    simp [orderedTripleExcessScore, orderedPairExcessBase,
      localNeighborhoodColoring, localDualColoring, intEdgeWeight]
  by_cases xy : x = y
  · subst y
    simp [orderedTripleExcessScore, orderedPairExcessBase,
      localNeighborhoodColoring, localDualColoring, intEdgeWeight]
  have vx : v ≠ x := Ne.symm xv
  have vy : v ≠ y := Ne.symm yv
  cases colorVX : color v x <;>
    cases colorVY : color v y <;>
    cases colorXY : color x y <;>
    simp [orderedTripleExcessScore, orderedPairExcessBase,
      localNeighborhoodColoring, localDualColoring, intEdgeWeight,
      xv, yv, xy, vx, vy, colorVX, colorVY, colorXY]

theorem intCast_sum_ofFn_nat {n : Nat} (values : Fin n → Nat) :
    ((List.ofFn values).sum : Int) =
      (List.ofFn fun i : Fin n => (values i : Int)).sum := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ, List.ofFn_succ]
      simp only [List.sum_cons, Int.natCast_add]
      rw [ih (fun i => values i.succ)]

theorem intEdgeWeight_eq_cast_edgeWeight (edge : Bool) :
    intEdgeWeight edge = (edgeWeight edge : Int) := by
  cases edge <;> rfl

theorem sumFin2_intEdgeWeight_eq_degreeSum {n : Nat} (color : Coloring n) :
    sumFin2 (fun x y => intEdgeWeight (color x y)) =
      (coloringDegreeSum color : Int) := by
  rw [coloringDegreeSum_eq_listColoringDegreeSum]
  unfold listColoringDegreeSum listColoringDegree sumFin2
  rw [intCast_sum_ofFn_nat]
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext x
  rw [intCast_sum_ofFn_nat]
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext y
  exact intEdgeWeight_eq_cast_edgeWeight (color x y)

theorem sum_ofFn_mul_int {n : Nat} (constant : Int) (values : Fin n → Int) :
    (List.ofFn fun i => constant * values i).sum =
      constant * (List.ofFn values).sum := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ, List.ofFn_succ]
      simp only [List.sum_cons]
      rw [ih (fun i => values i.succ)]
      rw [Int.mul_add]

theorem sumFin2_mul_int {n m : Nat} (constant : Int)
    (values : Fin n → Fin m → Int) :
    sumFin2 (fun i j => constant * values i j) =
      constant * sumFin2 values := by
  unfold sumFin2
  calc
    (List.ofFn fun i : Fin n =>
        (List.ofFn fun j : Fin m => constant * values i j).sum).sum =
        (List.ofFn fun i : Fin n =>
          constant * (List.ofFn fun j : Fin m => values i j).sum).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext i
      exact sum_ofFn_mul_int constant (values i)
    _ = _ := sum_ofFn_mul_int constant _

/-- Summed form of the pointwise local edge decomposition. -/
theorem localExcessScore_edge_decomposition {n : Nat}
    (color : Coloring n) (v : Fin n) :
    localExcessScore color v +
        2 * (coloringDegreeSum (localNeighborhoodColoring color v) : Int) +
        2 * (coloringDegreeSum (localDualColoring color v) : Int) =
      sumFin2 (fun x y => orderedPairExcessBase color v x y) := by
  have pointwise := congrArg sumFin2 (funext fun x => funext fun y =>
    orderedTripleExcessScore_edge_decomposition color v x y)
  rw [sumFin2_add, sumFin2_add, sumFin2_mul_int, sumFin2_mul_int,
    sumFin2_intEdgeWeight_eq_degreeSum,
    sumFin2_intEdgeWeight_eq_degreeSum] at pointwise
  exact pointwise

/-- Pure fixed-star version of the edge-independent pair score. -/
def fixedStarOrderedPairExcessBase (degree : Nat) (x y : Fin 45) : Int :=
  if x = 0 ∨ y = 0 ∨ x = y then 0
  else if (x.val ≤ degree ↔ y.val ≤ degree) then 2 else -1

set_option maxRecDepth 100000 in
theorem fixedStarOrderedPairExcessBase_values :
    sumFin2 (fixedStarOrderedPairExcessBase 20) = 904 ∧
    sumFin2 (fixedStarOrderedPairExcessBase 21) = 886 ∧
    sumFin2 (fixedStarOrderedPairExcessBase 22) = 880 := by
  unfold sumFin2 fixedStarOrderedPairExcessBase
  decide

theorem fixedStar_zero_row {color : Coloring 45} (simple : IsSimpleColoring color)
    (degree : Nat) (fixed : HasFixedStar color degree) (i : Fin 45) :
    color 0 i = decide (0 < i.val ∧ i.val ≤ degree) := by
  by_cases zero : i.val = 0
  · have equal : i = 0 := Fin.ext zero
    subst i
    simp [simple.1]
  by_cases bounded : i.val ≤ degree
  · have positive : 0 < i.val := by omega
    rw [fixed.1 i positive bounded]
    simp [positive, bounded]
  · have beyond : degree < i.val := by omega
    rw [fixed.2 i beyond]
    simp [beyond]

theorem orderedPairExcessBase_fixedStar {color : Coloring 45}
    (simple : IsSimpleColoring color) (degree : Nat)
    (fixed : HasFixedStar color degree) (x y : Fin 45) :
    orderedPairExcessBase color 0 x y =
      fixedStarOrderedPairExcessBase degree x y := by
  unfold orderedPairExcessBase
  rw [fixedStar_zero_row simple degree fixed x,
    fixedStar_zero_row simple degree fixed y]
  by_cases xzero : x = 0
  · subst x
    simp [fixedStarOrderedPairExcessBase]
  by_cases yzero : y = 0
  · subst y
    simp [fixedStarOrderedPairExcessBase]
  by_cases xy : x = y
  · subst y
    simp [fixedStarOrderedPairExcessBase]
  have xpos : 0 < x.val := by
    have : x.val ≠ 0 := fun equal => xzero (Fin.ext equal)
    omega
  have ypos : 0 < y.val := by
    have : y.val ≠ 0 := fun equal => yzero (Fin.ext equal)
    omega
  by_cases xbounded : x.val ≤ degree <;>
    by_cases ybounded : y.val ≤ degree <;>
    simp [fixedStarOrderedPairExcessBase, xzero, yzero, xy, xpos, ypos,
      xbounded, ybounded]

theorem fixedStar_pairBase_sum {color : Coloring 45}
    (simple : IsSimpleColoring color) (degree : Nat)
    (fixed : HasFixedStar color degree) :
    sumFin2 (fun x y => orderedPairExcessBase color 0 x y) =
      sumFin2 (fixedStarOrderedPairExcessBase degree) := by
  apply congrArg sumFin2
  funext x y
  exact orderedPairExcessBase_fixedStar simple degree fixed x y

/-- The concrete H/J graphs provide natural edge counts whose doubled degree
sums satisfy the local score formula. -/
theorem exists_fixedStar_localEdgeCounts_raw {color : Coloring 45}
    (simple : IsSimpleColoring color) (degree : Nat)
    (fixed : HasFixedStar color degree) (constant : Int)
    (baseValue : sumFin2 (fixedStarOrderedPairExcessBase degree) =
      2 * constant) :
    ∃ edgesH edgesJ : Nat,
      coloringDegreeSum (localNeighborhoodColoring color 0) = 2 * edgesH ∧
      coloringDegreeSum (localDualColoring color 0) = 2 * edgesJ ∧
        localExcessScore color 0 =
          2 * (constant - 2 * ((edgesH : Int) + (edgesJ : Int))) := by
  have hSimple := localNeighborhoodColoring_isSimple color simple 0
  have jSimple := localDualColoring_isSimple color simple 0
  rcases coloringDegreeSum_even (localNeighborhoodColoring color 0) hSimple with
    ⟨edgesH, hEven⟩
  rcases coloringDegreeSum_even (localDualColoring color 0) jSimple with
    ⟨edgesJ, jEven⟩
  have hEvenInt := congrArg (fun value : Nat => (value : Int)) hEven
  have jEvenInt := congrArg (fun value : Nat => (value : Int)) jEven
  simp only [Int.natCast_mul] at hEvenInt jEvenInt
  have decomposition := localExcessScore_edge_decomposition color 0
  have actualBase :
      sumFin2 (fun x y => orderedPairExcessBase color 0 x y) =
        2 * constant :=
    (fixedStar_pairBase_sum simple degree fixed).trans baseValue
  refine ⟨edgesH, edgesJ, hEven, jEven, ?_⟩
  rw [actualBase] at decomposition
  omega

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

/-- Relabel the selected excess witness to the exact fixed-apex convention
used by the three excess mother formulas. -/
theorem order45_fixedStar_normalize_nonpositive_excess_witness
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ normalized : Coloring 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
      localExcessScore normalized 0 ≤ 0 ∧
      ((HasFixedStar normalized 20 ∧ coloringDegree normalized 0 = 20) ∨
        (HasFixedStar normalized 21 ∧ coloringDegree normalized 0 = 21) ∨
        (HasFixedStar normalized 22 ∧ coloringDegree normalized 0 = 22)) := by
  rcases order45_normalize_nonpositive_excess_witness color simple ramseyFree
      window with
    ⟨base, v, baseSimple, baseFree, nonpositive,
      degree20 | degree21 | degree22⟩
  all_goals
    let normalized := relabelColoring base (starVertexMap base v)
    have facts := starRelabeling_normalizes base v baseSimple baseFree
    have scoreEquality := localExcessScore_relabel base
      (starVertexMap base v) (starVertexMap_isVertexRelabeling base v) 0
    rw [starVertexMap_zero] at scoreEquality
    have normalizedNonpositive : localExcessScore normalized 0 ≤ 0 := by
      rw [scoreEquality]
      exact nonpositive
  · refine ⟨normalized, facts.1, facts.2.1, normalizedNonpositive, Or.inl ?_⟩
    exact ⟨by simpa [degree20] using facts.2.2.1,
      facts.2.2.2.trans degree20⟩
  · refine ⟨normalized, facts.1, facts.2.1, normalizedNonpositive,
      Or.inr (Or.inl ?_)⟩
    exact ⟨by simpa [degree21] using facts.2.2.1,
      facts.2.2.2.trans degree21⟩
  · refine ⟨normalized, facts.1, facts.2.1, normalizedNonpositive,
      Or.inr (Or.inr ?_)⟩
    exact ⟨by simpa [degree22] using facts.2.2.1,
      facts.2.2.2.trans degree22⟩

/-- Concrete contract still to be discharged by the neighbourhood/J edge
counter bridge.  The score is twice
`twoOrder45LocalExcessConstant d - 2 * (e(H) + e(J))`. -/
def HasOrder45LocalEdgeCounts (color : Coloring 45) (v : Fin 45)
    (edgesH edgesJ : Nat) : Prop :=
  coloringDegreeSum (localNeighborhoodColoring color v) = 2 * edgesH ∧
  coloringDegreeSum (localDualColoring color v) = 2 * edgesJ ∧
    localExcessScore color v =
      2 * (twoOrder45LocalExcessConstant (coloringDegree color v) -
        2 * ((edgesH : Int) + (edgesJ : Int)))

theorem exists_order45LocalEdgeCounts_degree20 {color : Coloring 45}
    (simple : IsSimpleColoring color) (fixed : HasFixedStar color 20)
    (degree : coloringDegree color 0 = 20) :
    ∃ edgesH edgesJ : Nat, HasOrder45LocalEdgeCounts color 0 edgesH edgesJ := by
  have baseValues := fixedStarOrderedPairExcessBase_values
  have base : sumFin2 (fixedStarOrderedPairExcessBase 20) = 2 * (452 : Int) := by
    omega
  rcases exists_fixedStar_localEdgeCounts_raw simple 20 fixed 452 base with
    ⟨edgesH, edgesJ, hCount, jCount, counts⟩
  exact ⟨edgesH, edgesJ, hCount, jCount, by
    simpa [degree, twoOrder45LocalExcessConstant] using counts⟩

theorem exists_order45LocalEdgeCounts_degree21 {color : Coloring 45}
    (simple : IsSimpleColoring color) (fixed : HasFixedStar color 21)
    (degree : coloringDegree color 0 = 21) :
    ∃ edgesH edgesJ : Nat, HasOrder45LocalEdgeCounts color 0 edgesH edgesJ := by
  have baseValues := fixedStarOrderedPairExcessBase_values
  have base : sumFin2 (fixedStarOrderedPairExcessBase 21) = 2 * (443 : Int) := by
    omega
  rcases exists_fixedStar_localEdgeCounts_raw simple 21 fixed 443 base with
    ⟨edgesH, edgesJ, hCount, jCount, counts⟩
  exact ⟨edgesH, edgesJ, hCount, jCount, by
    simpa [degree, twoOrder45LocalExcessConstant] using counts⟩

theorem exists_order45LocalEdgeCounts_degree22 {color : Coloring 45}
    (simple : IsSimpleColoring color) (fixed : HasFixedStar color 22)
    (degree : coloringDegree color 0 = 22) :
    ∃ edgesH edgesJ : Nat, HasOrder45LocalEdgeCounts color 0 edgesH edgesJ := by
  have baseValues := fixedStarOrderedPairExcessBase_values
  have base : sumFin2 (fixedStarOrderedPairExcessBase 22) = 2 * (440 : Int) := by
    omega
  rcases exists_fixedStar_localEdgeCounts_raw simple 22 fixed 440 base with
    ⟨edgesH, edgesJ, hCount, jCount, counts⟩
  exact ⟨edgesH, edgesJ, hCount, jCount, by
    simpa [degree, twoOrder45LocalExcessConstant] using counts⟩

/-- Once the concrete local edge counters satisfy their exact score contract,
the global identity yields one of the three dense excess branches used by the
mother CNFs. -/
theorem order45_exists_dense_excess_branch
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ normalized : Coloring 45, ∃ edgesH edgesJ : Nat,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
      HasOrder45LocalEdgeCounts normalized 0 edgesH edgesJ ∧
      ((HasFixedStar normalized 20 ∧ coloringDegree normalized 0 = 20 ∧
          226 ≤ edgesH + edgesJ) ∨
        (HasFixedStar normalized 21 ∧ coloringDegree normalized 0 = 21 ∧
          222 ≤ edgesH + edgesJ) ∨
        (HasFixedStar normalized 22 ∧ coloringDegree normalized 0 = 22 ∧
          220 ≤ edgesH + edgesJ)) := by
  rcases order45_fixedStar_normalize_nonpositive_excess_witness color simple
      ramseyFree window with
    ⟨normalized, normalizedSimple, normalizedFree, nonpositive,
      branch20 | branch21 | branch22⟩
  · rcases exists_order45LocalEdgeCounts_degree20 normalizedSimple
      branch20.1 branch20.2 with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inl ⟨branch20.1, branch20.2, ?_⟩⟩
    have degree20 := branch20.2
    rw [counts.2.2, degree20] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega

  · rcases exists_order45LocalEdgeCounts_degree21 normalizedSimple
      branch21.1 branch21.2 with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inr (Or.inl ⟨branch21.1, branch21.2, ?_⟩)⟩
    have degree21 := branch21.2
    rw [counts.2.2, degree21] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega

  · rcases exists_order45LocalEdgeCounts_degree22 normalizedSimple
      branch22.1 branch22.2 with ⟨edgesH, edgesJ, counts⟩
    refine ⟨normalized, edgesH, edgesJ, normalizedSimple, normalizedFree,
      counts, Or.inr (Or.inr ⟨branch22.1, branch22.2, ?_⟩)⟩
    have degree22 := branch22.2
    rw [counts.2.2, degree22] at nonpositive
    have constants := twoOrder45LocalExcessConstant_values
    omega

/-- End-to-end graph-side excess reduction with the checked order-25 Ramsey
statement as its sole external mathematical input. -/
theorem order45_exists_dense_excess_branch_of_r45
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    ∃ normalized : Coloring 45, ∃ edgesH edgesJ : Nat,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
      HasOrder45LocalEdgeCounts normalized 0 edgesH edgesJ ∧
      ((HasFixedStar normalized 20 ∧ coloringDegree normalized 0 = 20 ∧
          226 ≤ edgesH + edgesJ) ∨
        (HasFixedStar normalized 21 ∧ coloringDegree normalized 0 = 21 ∧
          222 ≤ edgesH + edgesJ) ∨
        (HasFixedStar normalized 22 ∧ coloringDegree normalized 0 = 22 ∧
          220 ≤ edgesH + edgesJ)) := by
  exact order45_exists_dense_excess_branch color simple ramseyFree
    (order45_degree_window_of_r45 r45 color simple ramseyFree)

#print axioms globalExcessScore_identity
#print axioms exists_nonpositive_localExcessScore
#print axioms order45_normalize_nonpositive_excess_witness
#print axioms order45_fixedStar_normalize_nonpositive_excess_witness
#print axioms order45_exists_dense_excess_branch
#print axioms order45_exists_dense_excess_branch_of_r45

end Ramsey55
