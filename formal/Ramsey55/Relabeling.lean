import Ramsey55.Definitions
import Init.Data.List.OfFn
import Init.Data.List.Perm
import Init.Data.List.Sort

namespace Ramsey55

/-- Pull a colouring back along a map of vertex labels.  Bijections give graph
relabelings; injections give induced labelled subcolourings. -/
def relabelColoring {source target : Nat} (color : Coloring source)
    (vertexMap : Fin target → Fin source) : Coloring target :=
  fun u v => color (vertexMap u) (vertexMap v)

/-- A finite relabeling lists every old label exactly once.  The explicit
injectivity field is convenient for transporting distinct tuples, while the
list permutation is convenient for transporting row counts. -/
def IsVertexRelabeling {n : Nat} (vertexMap : Fin n → Fin n) : Prop :=
  Function.Injective vertexMap ∧
    (List.ofFn vertexMap).Perm (List.ofFn fun v : Fin n => v)

def allVertices (n : Nat) : List (Fin n) :=
  List.ofFn fun v : Fin n => v

/-- Deterministic old-label order used to move `v` to zero: `v`, then all of
its neighbours, then all of its nonneighbours. -/
def starVertexOrder {n : Nat} (color : Coloring n) (v : Fin n) :
    List (Fin n) :=
  let rest := (allVertices n).erase v
  v :: (rest.filter (fun u => color v u) ++
    rest.filter (fun u => !color v u))

theorem starVertexOrder_perm {n : Nat} (color : Coloring n) (v : Fin n) :
    (starVertexOrder color v).Perm (allVertices n) := by
  have member : v ∈ allVertices n := by
    exact List.mem_ofFn.mpr ⟨v, rfl⟩
  let rest := (allVertices n).erase v
  have partition := List.filter_append_perm (fun u => color v u) rest
  exact (partition.cons v).trans (List.perm_cons_erase member).symm

theorem starVertexOrder_length {n : Nat} (color : Coloring n) (v : Fin n) :
    (starVertexOrder color v).length = n := by
  calc
    (starVertexOrder color v).length = (allVertices n).length :=
      (starVertexOrder_perm color v).length_eq
    _ = n := by simp [allVertices]

def starVertexMap {n : Nat} (color : Coloring n) (v : Fin n) :
    Fin n → Fin n := fun i =>
  (starVertexOrder color v)[i.val]'(by
    rw [starVertexOrder_length]
    exact i.isLt)

theorem ofFn_starVertexMap {n : Nat} (color : Coloring n) (v : Fin n) :
    List.ofFn (starVertexMap color v) = starVertexOrder color v := by
  apply List.ext_getElem
  · simp [starVertexOrder_length]
  · intro i left right
    simp [starVertexMap]

theorem nodup_ofFn_of_injective {alpha : Type} :
    ∀ (n : Nat) (f : Fin n → alpha),
      Function.Injective f → (List.ofFn f).Nodup := by
  intro n
  induction n with
  | zero =>
      intro f injective
      simp
  | succ n ih =>
      intro f injective
      rw [List.ofFn_succ]
      simp only [List.nodup_cons]
      constructor
      · intro member
        rw [List.mem_ofFn] at member
        rcases member with ⟨i, equal⟩
        have indexEqual : (0 : Fin (n + 1)) = i.succ := injective equal.symm
        have impossible : 0 = i.val + 1 := by
          simpa using congrArg Fin.val indexEqual
        omega
      · apply ih (fun i => f i.succ)
        intro left right equal
        have mapped : left.succ = right.succ := injective equal
        exact Fin.ext (by
          have := congrArg Fin.val mapped
          simpa using this)

theorem allVertices_nodup (n : Nat) : (allVertices n).Nodup := by
  exact nodup_ofFn_of_injective n (fun v => v) fun _ _ equal => equal

theorem starVertexOrder_nodup {n : Nat} (color : Coloring n) (v : Fin n) :
    (starVertexOrder color v).Nodup := by
  exact (starVertexOrder_perm color v).nodup_iff.mpr (allVertices_nodup n)

theorem starVertexMap_injective {n : Nat} (color : Coloring n) (v : Fin n) :
    Function.Injective (starVertexMap color v) := by
  intro left right equal
  apply Fin.ext
  apply (List.getElem_inj (starVertexOrder_nodup color v)).mp
  exact equal

theorem starVertexMap_isVertexRelabeling {n : Nat}
    (color : Coloring n) (v : Fin n) :
    IsVertexRelabeling (starVertexMap color v) := by
  constructor
  · exact starVertexMap_injective color v
  · rw [ofFn_starVertexMap]
    exact starVertexOrder_perm color v

theorem starVertexMap_zero {n : Nat} (color : Coloring (n + 1))
    (v : Fin (n + 1)) :
    starVertexMap color v 0 = v := by
  simp [starVertexMap, starVertexOrder]

theorem relabelColoring_isSimple {source target : Nat}
    (color : Coloring source) (vertexMap : Fin target → Fin source)
    (simple : IsSimpleColoring color) :
    IsSimpleColoring (relabelColoring color vertexMap) := by
  constructor
  · intro v
    exact simple.1 (vertexMap v)
  · intro u v
    exact simple.2 (vertexMap u) (vertexMap v)

/-- The ten pairwise inequalities on five labelled vertices. -/
def Distinct5 {n : Nat} (a b c d e : Fin n) : Prop :=
  a ≠ b ∧ a ≠ c ∧ a ≠ d ∧ a ≠ e ∧
    b ≠ c ∧ b ≠ d ∧ b ≠ e ∧
    c ≠ d ∧ c ≠ e ∧ d ≠ e

theorem Distinct5.map {source target : Nat}
    (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    {a b c d e : Fin target} (distinct : Distinct5 a b c d e) :
    Distinct5 (vertexMap a) (vertexMap b) (vertexMap c)
      (vertexMap d) (vertexMap e) := by
  rcases distinct with
    ⟨ab, ac, ad, ae, bc, bd, be, cd, ce, de⟩
  exact ⟨fun equal => ab (injective equal),
    fun equal => ac (injective equal),
    fun equal => ad (injective equal),
    fun equal => ae (injective equal),
    fun equal => bc (injective equal),
    fun equal => bd (injective equal),
    fun equal => be (injective equal),
    fun equal => cd (injective equal),
    fun equal => ce (injective equal),
    fun equal => de (injective equal)⟩

/-- Order-independent presentation of a monochromatic clique on a finite
vertex list.  It lets the proof sort a five-set without enumerating all 120
orders of its ten edges. -/
def MonochromaticList {n : Nat} (color : Coloring n)
    (vertices : List (Fin n)) : Prop :=
  ∃ common : Bool, ∀ u ∈ vertices, ∀ v ∈ vertices,
    u ≠ v → color u v = common

theorem monochromaticList_of_monochromatic5 {n : Nat}
    (color : Coloring n) (simple : IsSimpleColoring color)
    (a b c d e : Fin n) (distinct : Distinct5 a b c d e)
    (monochromatic : Monochromatic5 color a b c d e) :
    MonochromaticList color [a, b, c, d, e] := by
  refine ⟨color a b, ?_⟩
  intro u hu v hv ne
  simp at hu hv
  rcases hu with rfl | rfl | rfl | rfl | rfl <;>
    rcases hv with rfl | rfl | rfl | rfl | rfl
  all_goals simp_all [Monochromatic5, Distinct5]
  all_goals rw [simple.2]
  all_goals simp_all

theorem monochromatic5_of_monochromaticList {n : Nat}
    (color : Coloring n) (a b c d e : Fin n)
    (distinct : Distinct5 a b c d e)
    (monochromatic : MonochromaticList color [a, b, c, d, e]) :
    Monochromatic5 color a b c d e := by
  rcases distinct with ⟨abNe, acNe, adNe, aeNe, bcNe, bdNe, beNe,
    cdNe, ceNe, deNe⟩
  rcases monochromatic with ⟨common, all⟩
  have ab := all a (by simp) b (by simp) abNe
  have ac := all a (by simp) c (by simp) acNe
  have ad := all a (by simp) d (by simp) adNe
  have ae := all a (by simp) e (by simp) aeNe
  have bc := all b (by simp) c (by simp) bcNe
  have bd := all b (by simp) d (by simp) bdNe
  have be := all b (by simp) e (by simp) beNe
  have cd := all c (by simp) d (by simp) cdNe
  have ce := all c (by simp) e (by simp) ceNe
  have de := all d (by simp) e (by simp) deNe
  simp [Monochromatic5, ab, ac, ad, ae, bc, bd, be, cd, ce, de]

theorem MonochromaticList.perm {n : Nat} {color : Coloring n}
    {left right : List (Fin n)} (permutation : left.Perm right)
    (monochromatic : MonochromaticList color left) :
    MonochromaticList color right := by
  rcases monochromatic with ⟨common, all⟩
  refine ⟨common, ?_⟩
  intro u hu v hv ne
  exact all u (permutation.mem_iff.mpr hu) v
    (permutation.mem_iff.mpr hv) ne

theorem list_eq_five_of_length {alpha : Type} {values : List alpha}
    (length : values.length = 5) :
    ∃ a b c d e : alpha, values = [a, b, c, d, e] := by
  rcases values with _ | ⟨a, values⟩
  · simp at length
  rcases values with _ | ⟨b, values⟩
  · simp at length
  rcases values with _ | ⟨c, values⟩
  · simp at length
  rcases values with _ | ⟨d, values⟩
  · simp at length
  rcases values with _ | ⟨e, values⟩
  · simp at length
  rcases values with _ | ⟨f, values⟩
  · exact ⟨a, b, c, d, e, rfl⟩
  · simp at length

/-- An order-independent form of Ramsey-freeness.  This is the natural
predicate for graph relabeling; the bridge from the existing increasing-tuple
predicate is kept explicit below. -/
def IsRamseyFree55Unordered {n : Nat} (color : Coloring n) : Prop :=
  ∀ a b c d e : Fin n,
    Distinct5 a b c d e → ¬ Monochromatic5 color a b c d e

theorem ramseyFree55Unordered_relabel {source target : Nat}
    (color : Coloring source) (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    (ramseyFree : IsRamseyFree55Unordered color) :
    IsRamseyFree55Unordered (relabelColoring color vertexMap) := by
  intro a b c d e distinct monochromatic
  have mappedDistinct := Distinct5.map vertexMap injective distinct
  have mappedMonochromatic : Monochromatic5 color
      (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d)
      (vertexMap e) := by
    simpa [relabelColoring, Monochromatic5] using monochromatic
  exact ramseyFree (vertexMap a) (vertexMap b) (vertexMap c)
    (vertexMap d) (vertexMap e) mappedDistinct mappedMonochromatic

/-- The unordered predicate immediately implies the original predicate on
the unique increasing enumeration of a five-set. -/
theorem ramseyFree55_of_unordered {n : Nat} (color : Coloring n)
    (ramseyFree : IsRamseyFree55Unordered color) : IsRamseyFree55 color := by
  intro a b c d e ab bc cd de monochromatic
  have neOfValLt : ∀ {left right : Fin n},
      left.val < right.val → left ≠ right := by
    intro left right less equal
    subst right
    omega
  have distinct : Distinct5 a b c d e := by
    exact ⟨neOfValLt ab,
      neOfValLt (by omega), neOfValLt (by omega), neOfValLt (by omega),
      neOfValLt bc, neOfValLt (by omega), neOfValLt (by omega),
      neOfValLt cd, neOfValLt (by omega), neOfValLt de⟩
  exact ramseyFree a b c d e distinct monochromatic

/-- The historical increasing-tuple predicate also excludes an arbitrary
ordered tuple of five distinct vertices.  Sort the tuple, preserve its
monochromatic edge set through the list permutation, and invoke the unique
increasing enumeration covered by `IsRamseyFree55`. -/
theorem ramseyFree55Unordered_of_ordered {n : Nat} (color : Coloring n)
    (simple : IsSimpleColoring color) (ramseyFree : IsRamseyFree55 color) :
    IsRamseyFree55Unordered color := by
  intro a b c d e distinct monochromatic
  let original : List (Fin n) := [a, b, c, d, e]
  let le : Fin n → Fin n → Bool :=
    fun left right => decide (left.val ≤ right.val)
  let sorted := original.mergeSort le
  have permutation : sorted.Perm original := by
    exact List.mergeSort_perm original le
  have sortedLength : sorted.length = 5 := by
    simpa [original] using permutation.length_eq
  have originalNodup : original.Nodup := by
    rcases distinct with
      ⟨ab, ac, ad, ae, bc, bd, be, cd, ce, de⟩
    simp [original, ab, ac, ad, ae, bc, bd, be, cd, ce, de]
  have sortedNodup : sorted.Nodup :=
    permutation.nodup_iff.mpr originalNodup
  have sortedPairwise : sorted.Pairwise
      (fun left right => le left right = true) := by
    apply List.pairwise_mergeSort
    · intro left middle right leftMiddle middleRight
      simp [le] at leftMiddle middleRight ⊢
      omega
    · intro left right
      simp [le]
      omega
  rcases list_eq_five_of_length sortedLength with
    ⟨p, q, r, s, t, sortedEq⟩
  have sortedDistinct : Distinct5 p q r s t := by
    rw [sortedEq] at sortedNodup
    simp at sortedNodup
    rcases sortedNodup with ⟨pRest, qRest, rRest, st⟩
    rcases pRest with ⟨pq, pr, ps, pt⟩
    rcases qRest with ⟨qr, qs, qt⟩
    rcases rRest with ⟨rs, rt⟩
    exact ⟨pq, pr, ps, pt, qr, qs, qt, rs, rt, st⟩
  have increasing : p.val < q.val ∧ q.val < r.val ∧
      r.val < s.val ∧ s.val < t.val := by
    rw [sortedEq] at sortedPairwise
    simp [le] at sortedPairwise
    rcases sortedDistinct with
      ⟨pq, pr, ps, pt, qr, qs, qt, rs, rt, st⟩
    exact ⟨by omega, by omega, by omega, by omega⟩
  have originalMonochromatic : MonochromaticList color original := by
    exact monochromaticList_of_monochromatic5 color simple a b c d e
      distinct monochromatic
  have sortedMonochromatic : MonochromaticList color sorted :=
    originalMonochromatic.perm permutation.symm
  rw [sortedEq] at sortedMonochromatic
  have monochromaticSorted : Monochromatic5 color p q r s t :=
    monochromatic5_of_monochromaticList color p q r s t sortedDistinct
      sortedMonochromatic
  exact ramseyFree p q r s t increasing.1 increasing.2.1
    increasing.2.2.1 increasing.2.2.2 monochromaticSorted

/-- A finite injective relabeling preserves the project's original ordered
Ramsey-free predicate. -/
theorem ramseyFree55_relabel {source target : Nat}
    (color : Coloring source) (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    (simple : IsSimpleColoring color) (ramseyFree : IsRamseyFree55 color) :
    IsRamseyFree55 (relabelColoring color vertexMap) := by
  apply ramseyFree55_of_unordered
  exact ramseyFree55Unordered_relabel color vertexMap injective
    (ramseyFree55Unordered_of_ordered color simple ramseyFree)

#print axioms relabelColoring_isSimple
#print axioms IsVertexRelabeling
#print axioms starVertexOrder_perm
#print axioms starVertexMap_isVertexRelabeling
#print axioms starVertexMap_zero
#print axioms Distinct5.map
#print axioms ramseyFree55Unordered_relabel
#print axioms ramseyFree55_of_unordered
#print axioms ramseyFree55Unordered_of_ordered
#print axioms ramseyFree55_relabel

end Ramsey55
