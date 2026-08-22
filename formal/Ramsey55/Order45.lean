import Ramsey55.Relabeling
import Init.Data.List.OfFn
import Init.Data.List.Nat.Sum

namespace Ramsey55

/-- The sum of `n` odd natural numbers is an even number plus `n`.  This is
the arithmetic half of the odd-order handshake argument. -/
theorem sum_ofFn_of_all_odd {n : Nat} (values : Fin n → Nat)
    (odd : ∀ i : Fin n, ∃ half : Nat, values i = 2 * half + 1) :
    ∃ half : Nat, (List.ofFn values).sum = 2 * half + n := by
  induction n with
  | zero =>
      exact ⟨0, by simp [List.ofFn_zero]⟩
  | succ n ih =>
      have headOdd := odd (0 : Fin (n + 1))
      have tailOdd : ∀ i : Fin n, ∃ half : Nat,
          values i.succ = 2 * half + 1 := by
        intro i
        exact odd i.succ
      rcases headOdd with ⟨headHalf, headValue⟩
      rcases ih (fun i : Fin n => values i.succ) tailOdd with
        ⟨tailHalf, tailSum⟩
      refine ⟨headHalf + tailHalf, ?_⟩
      rw [List.ofFn_succ]
      simp [headValue, tailSum]
      omega

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

/-- The sum of the degrees of all labelled vertices. -/
def coloringDegreeSum {n : Nat} (color : Coloring n) : Nat :=
  (List.ofFn fun v : Fin n => coloringDegree color v).sum

/-- Turn one Boolean adjacency-matrix entry into its contribution to a
degree. -/
def edgeWeight (edge : Bool) : Nat := if edge then 1 else 0

/-- A list-based presentation of one row degree, used for the finite-matrix
double-counting proof below. -/
def listColoringDegree {n : Nat} (color : Coloring n) (v : Fin n) : Nat :=
  (List.ofFn fun u : Fin n => edgeWeight (color v u)).sum

theorem coloringDegreeUpTo_eq_listPrefix {n : Nat} (color : Coloring n)
    (v : Fin n) : ∀ (m : Nat) (within : m ≤ n),
    coloringDegreeUpTo color v m within =
      (List.ofFn fun i : Fin m =>
        edgeWeight (color v ⟨i.val, Nat.lt_of_lt_of_le i.isLt within⟩)).sum := by
  intro m
  induction m with
  | zero =>
      intro within
      simp [coloringDegreeUpTo]
  | succ m ih =>
      intro within
      have previous : m ≤ n := Nat.le_trans (Nat.le_succ m) within
      rw [coloringDegreeUpTo, List.ofFn_succ_last, ih previous]
      simp only [List.sum_append, List.sum_singleton]
      congr 2

theorem coloringDegree_eq_listColoringDegree {n : Nat}
    (color : Coloring n) (v : Fin n) :
    coloringDegree color v = listColoringDegree color v := by
  exact coloringDegreeUpTo_eq_listPrefix color v n (Nat.le_refl n)

/-- A finite vertex relabeling preserves the degree of the corresponding old
vertex.  The proof maps the explicit permutation of all labels through one
adjacency row and uses permutation-invariance of natural-number sums. -/
theorem coloringDegree_relabel {n : Nat} (color : Coloring n)
    (vertexMap : Fin n → Fin n) (relabeling : IsVertexRelabeling vertexMap)
    (v : Fin n) :
    coloringDegree (relabelColoring color vertexMap) v =
      coloringDegree color (vertexMap v) := by
  rw [coloringDegree_eq_listColoringDegree,
    coloringDegree_eq_listColoringDegree]
  have mapped := relabeling.2.map
    (fun u => edgeWeight (color (vertexMap v) u))
  simpa [listColoringDegree, relabelColoring, Function.comp_def] using
    mapped.sum_nat

theorem sum_map_edgeWeight_eq_countP {alpha : Type}
    (predicate : alpha → Bool) : ∀ values : List alpha,
    (values.map fun value => edgeWeight (predicate value)).sum =
      values.countP predicate := by
  intro values
  induction values with
  | nil => simp
  | cons head tail ih =>
      rw [List.map_cons, List.sum_cons, List.countP_cons, ih]
      cases condition : predicate head <;> simp [edgeWeight]
      all_goals omega

theorem listColoringDegree_eq_countP_allVertices {n : Nat}
    (color : Coloring n) (v : Fin n) :
    listColoringDegree color v =
      (allVertices n).countP (fun u => color v u) := by
  rw [← sum_map_edgeWeight_eq_countP (fun u => color v u) (allVertices n)]
  simp [listColoringDegree, allVertices, Function.comp_def]

/-- The neighbour segment in the deterministic star order has exactly the
degree measured by the project's bounded scan. -/
theorem starNeighborCount {n : Nat} (color : Coloring n) (v : Fin n)
    (simple : IsSimpleColoring color) :
    (((allVertices n).erase v).filter fun u => color v u).length =
      coloringDegree color v := by
  rw [← List.countP_eq_length_filter,
    coloringDegree_eq_listColoringDegree,
    listColoringDegree_eq_countP_allVertices]
  have member : v ∈ allVertices n := by
    exact List.mem_ofFn.mpr ⟨v, rfl⟩
  have counts := (List.perm_cons_erase member).countP_eq (fun u => color v u)
  simpa [simple.1 v] using counts.symm

theorem starVertexMap_edge_of_le_degree {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1))
    (simple : IsSimpleColoring color) (i : Fin (n + 1))
    (positive : 0 < i.val) (bounded : i.val ≤ coloringDegree color v) :
    color v (starVertexMap color v i) = true := by
  revert positive bounded
  refine Fin.cases ?_ (fun j => ?_) i
  · intro positive bounded
    change 0 < 0 at positive
    omega
  · intro positive bounded
    let rest := (allVertices (n + 1)).erase v
    let neighbors := rest.filter (fun u => color v u)
    let nonneighbors := rest.filter (fun u => !color v u)
    have neighborLength : neighbors.length = coloringDegree color v := by
      exact starNeighborCount color v simple
    have index_lt : j.val < neighbors.length := by
      change j.val + 1 ≤ coloringDegree color v at bounded
      omega
    have member : neighbors[j.val] ∈ neighbors :=
      List.getElem_mem index_lt
    have edge : color v neighbors[j.val] = true := by
      exact (List.mem_filter.mp member).2
    simpa [starVertexMap, starVertexOrder, rest, neighbors, nonneighbors,
      index_lt] using edge

theorem starVertexMap_nonedge_of_degree_lt {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1))
    (simple : IsSimpleColoring color) (i : Fin (n + 1))
    (beyond : coloringDegree color v < i.val) :
    color v (starVertexMap color v i) = false := by
  revert beyond
  refine Fin.cases ?_ (fun j => ?_) i
  · intro beyond
    change coloringDegree color v < 0 at beyond
    omega
  · intro beyond
    let rest := (allVertices (n + 1)).erase v
    let neighbors := rest.filter (fun u => color v u)
    let nonneighbors := rest.filter (fun u => !color v u)
    have neighborLength : neighbors.length = coloringDegree color v := by
      exact starNeighborCount color v simple
    have memberV : v ∈ allVertices (n + 1) := by
      exact List.mem_ofFn.mpr ⟨v, rfl⟩
    have restLength : rest.length = n := by
      rw [show rest = (allVertices (n + 1)).erase v by rfl,
        List.length_erase_of_mem memberV]
      simp [allVertices]
    have partitionLength : neighbors.length + nonneighbors.length = n := by
      have partition :=
        (List.filter_append_perm (fun u => color v u) rest).length_eq
      simpa [neighbors, nonneighbors, restLength] using partition
    have neighbor_le : neighbors.length ≤ j.val := by
      change coloringDegree color v < j.val + 1 at beyond
      omega
    have offset_lt : j.val - neighbors.length < nonneighbors.length := by
      have j_lt : j.val < n := j.isLt
      omega
    have member : nonneighbors[j.val - neighbors.length] ∈ nonneighbors :=
      List.getElem_mem offset_lt
    have nonedge :
        color v nonneighbors[j.val - neighbors.length] = false := by
      have negated := (List.mem_filter.mp member).2
      simpa using negated
    simpa [starVertexMap, starVertexOrder, rest, neighbors, nonneighbors,
      neighbor_le, offset_lt] using nonedge

/-- Vertex zero is adjacent exactly to labels `1, ..., degree`. -/
def HasFixedStar {n : Nat} (color : Coloring (n + 1)) (degree : Nat) : Prop :=
  (∀ i : Fin (n + 1),
    0 < i.val → i.val ≤ degree → color 0 i = true) ∧
    (∀ i : Fin (n + 1), degree < i.val → color 0 i = false)

theorem relabelColoring_starVertexMap_hasFixedStar {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1))
    (simple : IsSimpleColoring color) :
    HasFixedStar (relabelColoring color (starVertexMap color v))
      (coloringDegree color v) := by
  constructor
  · intro i positive bounded
    change color (starVertexMap color v 0) (starVertexMap color v i) = true
    rw [starVertexMap_zero]
    exact starVertexMap_edge_of_le_degree color v simple i positive bounded
  · intro i beyond
    change color (starVertexMap color v 0) (starVertexMap color v i) = false
    rw [starVertexMap_zero]
    exact starVertexMap_nonedge_of_degree_lt color v simple i beyond

theorem coloringDegree_starVertexMap_zero {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1)) :
    coloringDegree (relabelColoring color (starVertexMap color v)) 0 =
      coloringDegree color v := by
  rw [coloringDegree_relabel color (starVertexMap color v)
    (starVertexMap_isVertexRelabeling color v), starVertexMap_zero]

/-- Deterministic fixed-star normalization under the order-independent
Ramsey-free predicate; `Relabeling.lean` supplies the checked equivalence with
the historical increasing-tuple predicate used below. -/
theorem starRelabeling_normalizes_unordered {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1))
    (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55Unordered color) :
    IsSimpleColoring (relabelColoring color (starVertexMap color v)) ∧
      IsRamseyFree55Unordered
        (relabelColoring color (starVertexMap color v)) ∧
      HasFixedStar (relabelColoring color (starVertexMap color v))
        (coloringDegree color v) ∧
      coloringDegree (relabelColoring color (starVertexMap color v)) 0 =
        coloringDegree color v := by
  exact ⟨relabelColoring_isSimple color (starVertexMap color v) simple,
    ramseyFree55Unordered_relabel color (starVertexMap color v)
      (starVertexMap_isVertexRelabeling color v).1 ramseyFree,
    relabelColoring_starVertexMap_hasFixedStar color v simple,
    coloringDegree_starVertexMap_zero color v⟩

/-- Deterministic fixed-star normalization stated using the project's
historical increasing-tuple Ramsey-free predicate. -/
theorem starRelabeling_normalizes {n : Nat}
    (color : Coloring (n + 1)) (v : Fin (n + 1))
    (simple : IsSimpleColoring color) (ramseyFree : IsRamseyFree55 color) :
    IsSimpleColoring (relabelColoring color (starVertexMap color v)) ∧
      IsRamseyFree55 (relabelColoring color (starVertexMap color v)) ∧
      HasFixedStar (relabelColoring color (starVertexMap color v))
        (coloringDegree color v) ∧
      coloringDegree (relabelColoring color (starVertexMap color v)) 0 =
        coloringDegree color v := by
  exact ⟨relabelColoring_isSimple color (starVertexMap color v) simple,
    ramseyFree55_relabel color (starVertexMap color v)
      (starVertexMap_isVertexRelabeling color v).1 simple ramseyFree,
    relabelColoring_starVertexMap_hasFixedStar color v simple,
    coloringDegree_starVertexMap_zero color v⟩

/-- Delete label zero from both axes of a colouring. -/
def tailColoring {n : Nat} (color : Coloring (n + 1)) : Coloring n :=
  fun u v => color u.succ v.succ

theorem tailColoring_isSimple {n : Nat} (color : Coloring (n + 1))
    (simple : IsSimpleColoring color) : IsSimpleColoring (tailColoring color) := by
  constructor
  · intro v
    exact simple.1 v.succ
  · intro u v
    exact simple.2 u.succ v.succ

theorem listColoringDegree_zero_succ {n : Nat}
    (color : Coloring (n + 1)) (simple : IsSimpleColoring color) :
    listColoringDegree color 0 =
      (List.ofFn fun i : Fin n => edgeWeight (color 0 i.succ)).sum := by
  simp [listColoringDegree, List.ofFn_succ, edgeWeight, simple.1]

theorem listColoringDegree_succ {n : Nat} (color : Coloring (n + 1))
    (i : Fin n) :
    listColoringDegree color i.succ =
      edgeWeight (color i.succ 0) +
        listColoringDegree (tailColoring color) i := by
  simp [listColoringDegree, List.ofFn_succ, tailColoring]

theorem sum_ofFn_add {n : Nat} (left right : Fin n → Nat) :
    (List.ofFn fun i => left i + right i).sum =
      (List.ofFn left).sum + (List.ofFn right).sum := by
  induction n with
  | zero => simp
  | succ n ih =>
      rw [List.ofFn_succ, List.ofFn_succ, List.ofFn_succ]
      simp only [List.sum_cons]
      rw [ih (fun i => left i.succ) (fun i => right i.succ)]
      omega

def listColoringDegreeSum {n : Nat} (color : Coloring n) : Nat :=
  (List.ofFn fun v : Fin n => listColoringDegree color v).sum

theorem listColoringDegreeSum_succ {n : Nat} (color : Coloring (n + 1)) :
    listColoringDegreeSum color = listColoringDegree color 0 +
      (List.ofFn fun i : Fin n => listColoringDegree color i.succ).sum := by
  simp [listColoringDegreeSum, List.ofFn_succ]

theorem listColoringDegree_tail_rows {n : Nat}
    (color : Coloring (n + 1)) :
    (List.ofFn fun i : Fin n => listColoringDegree color i.succ).sum =
      (List.ofFn fun i : Fin n => edgeWeight (color i.succ 0)).sum +
        listColoringDegreeSum (tailColoring color) := by
  calc
    (List.ofFn fun i : Fin n => listColoringDegree color i.succ).sum =
        (List.ofFn fun i : Fin n => edgeWeight (color i.succ 0) +
          listColoringDegree (tailColoring color) i).sum := by
      apply congrArg List.sum
      apply congrArg List.ofFn
      funext i
      exact listColoringDegree_succ color i
    _ = (List.ofFn fun i : Fin n => edgeWeight (color i.succ 0)).sum +
        (List.ofFn fun i : Fin n =>
          listColoringDegree (tailColoring color) i).sum :=
      sum_ofFn_add _ _
    _ = (List.ofFn fun i : Fin n => edgeWeight (color i.succ 0)).sum +
        listColoringDegreeSum (tailColoring color) := rfl

theorem coloring_cross_sum_eq {n : Nat} (color : Coloring (n + 1))
    (simple : IsSimpleColoring color) :
    (List.ofFn fun i : Fin n => edgeWeight (color i.succ 0)).sum =
      (List.ofFn fun i : Fin n => edgeWeight (color 0 i.succ)).sum := by
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext i
  apply congrArg edgeWeight
  exact simple.2 i.succ 0

/-- Handshake double counting for the list presentation of the adjacency
matrix.  Removing vertex zero leaves an even tail sum, while symmetry pairs
the deleted row with the deleted column. -/
theorem listColoringDegreeSum_even : ∀ (n : Nat) (color : Coloring n),
    IsSimpleColoring color →
      ∃ edges : Nat, listColoringDegreeSum color = 2 * edges := by
  intro n
  induction n with
  | zero =>
      intro color simple
      exact ⟨0, by simp [listColoringDegreeSum]⟩
  | succ n ih =>
      intro color simple
      have tailSimple := tailColoring_isSimple color simple
      rcases ih (tailColoring color) tailSimple with ⟨tailEdges, tailSum⟩
      let crossEdges :=
        (List.ofFn fun i : Fin n => edgeWeight (color 0 i.succ)).sum
      refine ⟨tailEdges + crossEdges, ?_⟩
      rw [listColoringDegreeSum_succ color,
        listColoringDegree_zero_succ color simple,
        listColoringDegree_tail_rows color,
        coloring_cross_sum_eq color simple,
        tailSum]
      dsimp [crossEdges]
      omega

theorem coloringDegreeSum_eq_listColoringDegreeSum {n : Nat}
    (color : Coloring n) :
    coloringDegreeSum color = listColoringDegreeSum color := by
  apply congrArg List.sum
  apply congrArg List.ofFn
  funext v
  exact coloringDegree_eq_listColoringDegree color v

/-- The handshake lemma for the project's concrete degree definition: the
sum of all degrees in a finite simple colouring is twice a natural number. -/
theorem coloringDegreeSum_even {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) :
    ∃ edges : Nat, coloringDegreeSum color = 2 * edges := by
  rcases listColoringDegreeSum_even n color simple with ⟨edges, even⟩
  exact ⟨edges, (coloringDegreeSum_eq_listColoringDegreeSum color).trans even⟩

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

/-- The degree-24 branch of a hypothetical order-45 counterexample reduces
in one checked step to a degree-20 counterexample by swapping edge colours. -/
theorem order45_ramseyFree_degree24_complement
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (v : Fin 45)
    (degree24 : coloringDegree color v = 24) :
    IsSimpleColoring (complementColoring color) ∧
      IsRamseyFree55 (complementColoring color) ∧
      coloringDegree (complementColoring color) v = 20 := by
  exact ⟨complementColoring_isSimple color simple,
    (ramseyFree55_complement_iff color).2 ramseyFree,
    order45_complement_degree24 color simple v degree24⟩

/-- Once an order-45 counterexample supplies a vertex of even degree in its
20--24 degree window, colour complementation reduces it to one of the two
degree branches used by the SAT calculation. -/
theorem order45_normalize_degree20_or22
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (candidate : ∃ v : Fin 45,
      coloringDegree color v = 20 ∨ coloringDegree color v = 22 ∨
        coloringDegree color v = 24) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        (coloringDegree normalized v = 20 ∨
          coloringDegree normalized v = 22) := by
  rcases candidate with ⟨v, degree20 | degree22 | degree24⟩
  · exact ⟨color, v, simple, ramseyFree, Or.inl degree20⟩
  · exact ⟨color, v, simple, ramseyFree, Or.inr degree22⟩
  · have reduced := order45_ramseyFree_degree24_complement color simple
        ramseyFree v degree24
    exact ⟨complementColoring color, v, reduced.1, reduced.2.1,
      Or.inl reduced.2.2⟩

/-- The graph-theoretic degree window plus the even vertex supplied by the
handshake lemma yields exactly the candidate expected by the normalization
theorem. -/
theorem order45_degree_candidate_of_window_and_even
    (color : Coloring 45)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (evenVertex : ∃ v : Fin 45, ∃ half : Nat,
      coloringDegree color v = 2 * half) :
    ∃ v : Fin 45,
      coloringDegree color v = 20 ∨ coloringDegree color v = 22 ∨
        coloringDegree color v = 24 := by
  rcases evenVertex with ⟨v, half, even⟩
  have bounds := window v
  refine ⟨v, ?_⟩
  omega

/-- A degree window and a handshake-lemma witness reduce a hypothetical
order-45 counterexample to the degree-20 or degree-22 SAT branch. -/
theorem order45_normalize_of_window_and_even
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (evenVertex : ∃ v : Fin 45, ∃ half : Nat,
      coloringDegree color v = 2 * half) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        (coloringDegree normalized v = 20 ∨
          coloringDegree normalized v = 22) := by
  exact order45_normalize_degree20_or22 color simple ramseyFree
    (order45_degree_candidate_of_window_and_even color window evenVertex)

/-- On 45 vertices in the 20--24 degree window, an even total degree forces a
degree-20, degree-22, or degree-24 vertex.  The proof excludes the alternative
that all 45 degrees are 21 or 23 by the preceding odd-sum theorem. -/
theorem order45_degree_candidate_of_window_and_even_sum
    (color : Coloring 45)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (evenSum : ∃ half : Nat, coloringDegreeSum color = 2 * half) :
    ∃ v : Fin 45,
      coloringDegree color v = 20 ∨ coloringDegree color v = 22 ∨
        coloringDegree color v = 24 := by
  letI : Decidable (∃ v : Fin 45,
      coloringDegree color v = 20 ∨ coloringDegree color v = 22 ∨
        coloringDegree color v = 24) := inferInstance
  by_cases candidate : ∃ v : Fin 45,
      coloringDegree color v = 20 ∨ coloringDegree color v = 22 ∨
        coloringDegree color v = 24
  · exact candidate
  · have allOdd : ∀ v : Fin 45, ∃ half : Nat,
        coloringDegree color v = 2 * half + 1 := by
      intro v
      have bounds := window v
      have not20 : coloringDegree color v ≠ 20 := by
        intro degree20
        exact candidate ⟨v, Or.inl degree20⟩
      have not22 : coloringDegree color v ≠ 22 := by
        intro degree22
        exact candidate ⟨v, Or.inr (Or.inl degree22)⟩
      have not24 : coloringDegree color v ≠ 24 := by
        intro degree24
        exact candidate ⟨v, Or.inr (Or.inr degree24)⟩
      have alternatives : coloringDegree color v = 21 ∨
          coloringDegree color v = 23 := by
        omega
      rcases alternatives with degree21 | degree23
      · exact ⟨10, by omega⟩
      · exact ⟨11, by omega⟩
    rcases sum_ofFn_of_all_odd
        (fun v : Fin 45 => coloringDegree color v) allOdd with
      ⟨oddHalf, oddSum⟩
    rcases evenSum with ⟨evenHalf, evenSum⟩
    change (List.ofFn fun v : Fin 45 => coloringDegree color v).sum =
      2 * evenHalf at evenSum
    omega

/-- Equivalently, the preceding candidate supplies an even-degree vertex. -/
theorem order45_even_degree_of_window_and_even_sum
    (color : Coloring 45)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (evenSum : ∃ half : Nat, coloringDegreeSum color = 2 * half) :
    ∃ v : Fin 45, ∃ half : Nat, coloringDegree color v = 2 * half := by
  rcases order45_degree_candidate_of_window_and_even_sum color window evenSum
    with ⟨v, degree20 | degree22 | degree24⟩
  · exact ⟨v, 10, by omega⟩
  · exact ⟨v, 11, by omega⟩
  · exact ⟨v, 12, by omega⟩

/-- The degree window and even degree-sum conclusion of the handshake lemma
are sufficient to reach the two SAT branches. -/
theorem order45_normalize_of_window_and_even_sum
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24)
    (evenSum : ∃ half : Nat, coloringDegreeSum color = 2 * half) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        (coloringDegree normalized v = 20 ∨
          coloringDegree normalized v = 22) := by
  exact order45_normalize_degree20_or22 color simple ramseyFree
    (order45_degree_candidate_of_window_and_even_sum color window evenSum)

/-- The checked handshake lemma removes the parity hypothesis entirely: the
20--24 degree window alone reduces a simple order-45 counterexample to one of
the two SAT degree branches. -/
theorem order45_normalize_of_window
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ normalized : Coloring 45, ∃ v : Fin 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        (coloringDegree normalized v = 20 ∨
          coloringDegree normalized v = 22) := by
  exact order45_normalize_of_window_and_even_sum color simple ramseyFree window
    (coloringDegreeSum_even color simple)

/-- Complete graph-side normalization to the two fixed-star SAT inputs.
After the degree-window and handshake reductions, a deterministic vertex
relabeling moves the selected vertex to zero, its neighbours to the next
20 or 22 labels, and its nonneighbours to the remaining labels. -/
theorem order45_fixedStar_normalize_of_window
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color)
    (window : ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24) :
    ∃ normalized : Coloring 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        ((HasFixedStar normalized 20 ∧
            coloringDegree normalized 0 = 20) ∨
          (HasFixedStar normalized 22 ∧
            coloringDegree normalized 0 = 22)) := by
  rcases order45_normalize_of_window color simple ramseyFree window with
    ⟨base, v, baseSimple, baseRamseyFree, degree20 | degree22⟩
  · let normalized := relabelColoring base (starVertexMap base v)
    have facts := starRelabeling_normalizes base v baseSimple baseRamseyFree
    refine ⟨normalized, facts.1, facts.2.1, Or.inl ?_⟩
    constructor
    · simpa [normalized, degree20] using facts.2.2.1
    · exact facts.2.2.2.trans degree20
  · let normalized := relabelColoring base (starVertexMap base v)
    have facts := starRelabeling_normalizes base v baseSimple baseRamseyFree
    refine ⟨normalized, facts.1, facts.2.1, Or.inr ?_⟩
    constructor
    · simpa [normalized, degree22] using facts.2.2.1
    · exact facts.2.2.2.trans degree22

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
#print axioms order45_ramseyFree_degree24_complement
#print axioms order45_normalize_degree20_or22
#print axioms order45_degree_candidate_of_window_and_even
#print axioms order45_normalize_of_window_and_even
#print axioms sum_ofFn_of_all_odd
#print axioms order45_degree_candidate_of_window_and_even_sum
#print axioms order45_even_degree_of_window_and_even_sum
#print axioms order45_normalize_of_window_and_even_sum
#print axioms coloringDegreeUpTo_eq_listPrefix
#print axioms coloringDegree_relabel
#print axioms starNeighborCount
#print axioms relabelColoring_starVertexMap_hasFixedStar
#print axioms coloringDegree_starVertexMap_zero
#print axioms starRelabeling_normalizes_unordered
#print axioms starRelabeling_normalizes
#print axioms listColoringDegreeSum_even
#print axioms coloringDegreeSum_even
#print axioms order45_normalize_of_window
#print axioms order45_fixedStar_normalize_of_window

end Ramsey55
