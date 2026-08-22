import Ramsey55.Order45

namespace Ramsey55

/-- The six pairwise inequalities on four labelled vertices. -/
def Distinct4 {n : Nat} (a b c d : Fin n) : Prop :=
  a ≠ b ∧ a ≠ c ∧ a ≠ d ∧ b ≠ c ∧ b ≠ d ∧ c ≠ d

theorem Distinct4.map {source target : Nat}
    (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    {a b c d : Fin target} (distinct : Distinct4 a b c d) :
    Distinct4 (vertexMap a) (vertexMap b) (vertexMap c) (vertexMap d) := by
  rcases distinct with ⟨ab, ac, ad, bc, bd, cd⟩
  exact ⟨fun equal => ab (injective equal),
    fun equal => ac (injective equal),
    fun equal => ad (injective equal),
    fun equal => bc (injective equal),
    fun equal => bd (injective equal),
    fun equal => cd (injective equal)⟩

/-- A four-clique in the `true` colour. -/
def RedClique4 {n : Nat} (color : Coloring n) (a b c d : Fin n) : Prop :=
  color a b = true ∧ color a c = true ∧ color a d = true ∧
    color b c = true ∧ color b d = true ∧ color c d = true

/-- A five-clique in the `false` colour. -/
def BlueClique5 {n : Nat} (color : Coloring n)
    (a b c d e : Fin n) : Prop :=
  Monochromatic5 color a b c d e ∧ color a b = false

/-- The finite graph statement whose order-25 instance is the upper-bound
half of `R(4,5) = 25`: every simple colouring contains a true four-clique or
a false five-clique.  Its independently checked proof is deliberately kept
as an explicit input to the order-45 reduction. -/
def ForcesRed4OrBlue5 (n : Nat) : Prop :=
  ∀ color : Coloring n, IsSimpleColoring color →
    (∃ a b c d : Fin n, Distinct4 a b c d ∧ RedClique4 color a b c d) ∨
      (∃ a b c d e : Fin n,
        Distinct5 a b c d e ∧ BlueClique5 color a b c d e)

/-- The first 25 vertices after zero in the fixed-star order.  When the
selected vertex has degree at least 25, all of them are neighbours. -/
def order45FirstNeighbors (color : Coloring 45) (v : Fin 45) :
    Fin 25 → Fin 45 := fun i =>
  starVertexMap color v ⟨i.val + 1, by omega⟩

theorem order45FirstNeighbors_injective (color : Coloring 45) (v : Fin 45) :
    Function.Injective (order45FirstNeighbors color v) := by
  intro left right equal
  have positions : (⟨left.val + 1, by omega⟩ : Fin 45) =
      ⟨right.val + 1, by omega⟩ :=
    starVertexMap_injective color v equal
  apply Fin.ext
  have values := congrArg Fin.val positions
  simpa using values

theorem order45FirstNeighbors_edge (color : Coloring 45) (v : Fin 45)
    (simple : IsSimpleColoring color)
    (degree : 25 ≤ coloringDegree color v) (i : Fin 25) :
    color v (order45FirstNeighbors color v i) = true := by
  have iBound : i.val < 25 := i.isLt
  let position : Fin 45 := ⟨i.val + 1, by omega⟩
  have positive : 0 < position.val := by
    simp [position]
  have bounded : position.val ≤ coloringDegree color v := by
    simp [position]
    omega
  exact starVertexMap_edge_of_le_degree color v simple position
    positive bounded

/-- The order-25 `R(4,5)` upper bound forces every vertex of a hypothetical
order-45 Ramsey-free colouring to have degree at most 24. -/
theorem order45_degree_le24_of_r45 (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (v : Fin 45) :
    coloringDegree color v ≤ 24 := by
  by_cases bounded : coloringDegree color v ≤ 24
  · exact bounded
  exfalso
  have degree : 25 ≤ coloringDegree color v := by omega
  let vertexMap := order45FirstNeighbors color v
  let induced := relabelColoring color vertexMap
  have injective : Function.Injective vertexMap :=
    order45FirstNeighbors_injective color v
  have neighbor : ∀ i : Fin 25, color v (vertexMap i) = true := by
    intro i
    exact order45FirstNeighbors_edge color v simple degree i
  have vertexNe : ∀ i : Fin 25, v ≠ vertexMap i := by
    intro i equal
    have edge := neighbor i
    rw [← equal] at edge
    simp [simple.1] at edge
  have inducedSimple : IsSimpleColoring induced :=
    relabelColoring_isSimple color vertexMap simple
  have unorderedFree :=
    ramseyFree55Unordered_of_ordered color simple ramseyFree
  rcases r45 induced inducedSimple with red | blue
  · rcases red with ⟨a, b, c, d, distinct, clique⟩
    have mappedDistinct := Distinct4.map vertexMap injective distinct
    have mappedClique : RedClique4 color (vertexMap a) (vertexMap b)
        (vertexMap c) (vertexMap d) := by
      simpa [induced, relabelColoring, RedClique4] using clique
    rcases mappedDistinct with ⟨abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
    rcases mappedClique with ⟨ab, ac, ad, bc, bd, cd⟩
    have distinct5 : Distinct5 v (vertexMap a) (vertexMap b)
        (vertexMap c) (vertexMap d) :=
      ⟨vertexNe a, vertexNe b, vertexNe c, vertexNe d,
        abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
    have monochromatic : Monochromatic5 color v (vertexMap a)
        (vertexMap b) (vertexMap c) (vertexMap d) := by
      simp [Monochromatic5, neighbor, ab, ac, ad, bc, bd, cd]
    exact unorderedFree v (vertexMap a) (vertexMap b) (vertexMap c)
      (vertexMap d) distinct5 monochromatic
  · rcases blue with ⟨a, b, c, d, e, distinct, clique⟩
    have mappedDistinct := Distinct5.map vertexMap injective distinct
    have mappedMonochromatic : Monochromatic5 color (vertexMap a)
        (vertexMap b) (vertexMap c) (vertexMap d) (vertexMap e) := by
      simpa [induced, relabelColoring, Monochromatic5] using clique.1
    exact unorderedFree (vertexMap a) (vertexMap b) (vertexMap c)
      (vertexMap d) (vertexMap e) mappedDistinct mappedMonochromatic

/-- Applying the same upper bound after colour complementation supplies the
lower degree bound, hence the complete 20--24 window. -/
theorem order45_degree_window_of_r45 (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    ∀ v : Fin 45,
      20 ≤ coloringDegree color v ∧ coloringDegree color v ≤ 24 := by
  intro v
  have upper := order45_degree_le24_of_r45 r45 color simple ramseyFree v
  have complementSimple := complementColoring_isSimple color simple
  have complementFree := (ramseyFree55_complement_iff color).2 ramseyFree
  have complementUpper := order45_degree_le24_of_r45 r45
    (complementColoring color) complementSimple complementFree v
  have total := coloringDegree_complement_add color simple v
  exact ⟨by omega, upper⟩

/-- With the checked order-25 `R(4,5)` statement as its sole external graph
input, a hypothetical order-45 counterexample reaches exactly one of the two
fixed-star SAT branches. -/
theorem order45_fixedStar_normalize_of_r45
    (r45 : ForcesRed4OrBlue5 25)
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) :
    ∃ normalized : Coloring 45,
      IsSimpleColoring normalized ∧ IsRamseyFree55 normalized ∧
        ((HasFixedStar normalized 20 ∧
            coloringDegree normalized 0 = 20) ∨
          (HasFixedStar normalized 22 ∧
            coloringDegree normalized 0 = 22)) := by
  exact order45_fixedStar_normalize_of_window color simple ramseyFree
    (order45_degree_window_of_r45 r45 color simple ramseyFree)

#print axioms order45_degree_le24_of_r45
#print axioms order45_degree_window_of_r45
#print axioms order45_fixedStar_normalize_of_r45

end Ramsey55
