import Ramsey55.Order45Excess

namespace Ramsey55

/-- A labelled `R(4,5,n)` graph: no true four-clique and no false
five-clique. -/
def IsRamsey45Coloring {n : Nat} (color : Coloring n) : Prop :=
  IsSimpleColoring color ∧
    (∀ a b c d : Fin n, Distinct4 a b c d →
      ¬ RedClique4 color a b c d) ∧
    (∀ a b c d e : Fin n, Distinct5 a b c d e →
      ¬ BlueClique5 color a b c d e)

/-- Any injectively labelled set of neighbours of one vertex in a Ramsey-free
colouring induces an `R(4,5)` graph. -/
theorem neighborInduced_isRamsey45Coloring
    {ambient localOrder : Nat} (color : Coloring ambient)
    (simple : IsSimpleColoring color) (ramseyFree : IsRamseyFree55 color)
    (apex : Fin ambient) (vertexMap : Fin localOrder → Fin ambient)
    (injective : Function.Injective vertexMap)
    (neighbor : ∀ i : Fin localOrder, color apex (vertexMap i) = true)
    (notApex : ∀ i : Fin localOrder, apex ≠ vertexMap i) :
    IsRamsey45Coloring (relabelColoring color vertexMap) := by
  have unorderedFree := ramseyFree55Unordered_of_ordered color simple ramseyFree
  refine ⟨relabelColoring_isSimple color vertexMap simple, ?_, ?_⟩
  · intro a b c d distinct red4
    have mappedDistinct := Distinct4.map vertexMap injective distinct
    have mappedRed : RedClique4 color (vertexMap a) (vertexMap b)
        (vertexMap c) (vertexMap d) := by
      simpa [relabelColoring, RedClique4] using red4
    rcases mappedDistinct with ⟨ab, ac, ad, bc, bd, cd⟩
    rcases mappedRed with ⟨abRed, acRed, adRed, bcRed, bdRed, cdRed⟩
    have distinct5 : Distinct5 apex (vertexMap a) (vertexMap b)
        (vertexMap c) (vertexMap d) :=
      ⟨notApex a, notApex b, notApex c, notApex d,
        ab, ac, ad, bc, bd, cd⟩
    have monochromatic : Monochromatic5 color apex (vertexMap a)
        (vertexMap b) (vertexMap c) (vertexMap d) := by
      simp [Monochromatic5, neighbor, abRed, acRed, adRed,
        bcRed, bdRed, cdRed]
    exact unorderedFree apex (vertexMap a) (vertexMap b) (vertexMap c)
      (vertexMap d) distinct5 monochromatic
  · intro a b c d e distinct blue5
    have mappedDistinct := Distinct5.map vertexMap injective distinct
    have mappedMonochromatic : Monochromatic5 color (vertexMap a)
        (vertexMap b) (vertexMap c) (vertexMap d) (vertexMap e) := by
      simpa [relabelColoring, Monochromatic5] using blue5.1
    exact unorderedFree (vertexMap a) (vertexMap b) (vertexMap c)
      (vertexMap d) (vertexMap e) mappedDistinct mappedMonochromatic

/-- The first `degree` labels after zero. -/
def order45NeighborBlockMap (degree : Nat) (bounded : degree ≤ 44) :
    Fin degree → Fin 45 := fun i => ⟨i.val + 1, by omega⟩

theorem order45NeighborBlockMap_injective (degree : Nat)
    (bounded : degree ≤ 44) :
    Function.Injective (order45NeighborBlockMap degree bounded) := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [order45NeighborBlockMap] at values
  omega

/-- The `44 - degree` labels after the neighbour block. -/
def order45NonneighborBlockMap (degree : Nat) (bounded : degree ≤ 44) :
    Fin (44 - degree) → Fin 45 := fun i =>
  ⟨degree + i.val + 1, by omega⟩

theorem order45NonneighborBlockMap_injective (degree : Nat)
    (bounded : degree ≤ 44) :
    Function.Injective (order45NonneighborBlockMap degree bounded) := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [order45NonneighborBlockMap] at values
  omega

/-- The H block of a fixed-star Ramsey-free colouring is a concrete labelled
`R(4,5,degree)` graph. -/
theorem fixedStarNeighborhood_isRamsey45Coloring
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (degree : Nat)
    (bounded : degree ≤ 44) (fixed : HasFixedStar color degree) :
    IsRamsey45Coloring
      (relabelColoring color (order45NeighborBlockMap degree bounded)) := by
  apply neighborInduced_isRamsey45Coloring color simple ramseyFree 0
    (order45NeighborBlockMap degree bounded)
    (order45NeighborBlockMap_injective degree bounded)
  · intro i
    apply fixed.1
    · simp [order45NeighborBlockMap]
    · simp [order45NeighborBlockMap]
      omega
  · intro i equal
    have values := congrArg Fin.val equal
    simp [order45NeighborBlockMap] at values

/-- After colour complementation, the nonneighbour block is the neighbour
block of the same apex.  Hence it is the concrete J-side
`R(4,5,44-degree)` graph. -/
theorem fixedStarDual_isRamsey45Coloring
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (degree : Nat)
    (bounded : degree ≤ 44) (fixed : HasFixedStar color degree) :
    IsRamsey45Coloring
      (relabelColoring (complementColoring color)
        (order45NonneighborBlockMap degree bounded)) := by
  have complementSimple := complementColoring_isSimple color simple
  have complementFree := (ramseyFree55_complement_iff color).2 ramseyFree
  apply neighborInduced_isRamsey45Coloring (complementColoring color)
    complementSimple complementFree 0
    (order45NonneighborBlockMap degree bounded)
    (order45NonneighborBlockMap_injective degree bounded)
  · intro i
    have beyond : degree < (order45NonneighborBlockMap degree bounded i).val := by
      simp [order45NonneighborBlockMap]
      omega
    have nonedge := fixed.2 (order45NonneighborBlockMap degree bounded i) beyond
    have nonzero : (0 : Fin 45) ≠ order45NonneighborBlockMap degree bounded i := by
      intro equal
      have values := congrArg Fin.val equal
      simp [order45NonneighborBlockMap] at values
    simp [complementColoring, nonzero, nonedge]
  · intro i equal
    have values := congrArg Fin.val equal
    simp [order45NonneighborBlockMap] at values

/-- External edge-range theorem schema.  Instantiations for orders 20--24 are
the published finite `R(4,5,n)` classification inputs still to be imported or
equivalently audited. -/
def Ramsey45EdgeRange (order lower upper : Nat) : Prop :=
  ∀ color : Coloring order, IsRamsey45Coloring color →
    ∀ edges : Nat, coloringDegreeSum color = 2 * edges →
      lower ≤ edges ∧ edges ≤ upper

def order45NeighborhoodInduced (color : Coloring 45) (degree : Nat)
    (bounded : degree ≤ 44) : Coloring degree :=
  relabelColoring color (order45NeighborBlockMap degree bounded)

def order45DualInduced (color : Coloring 45) (degree : Nat)
    (bounded : degree ≤ 44) : Coloring (44 - degree) :=
  relabelColoring (complementColoring color)
    (order45NonneighborBlockMap degree bounded)

/-- Catalog-facing H/J edge counts, defined on the exact induced local
orders rather than on their isolated 45-label padding. -/
def HasOrder45CatalogEdgeCounts (color : Coloring 45) (degree : Nat)
    (bounded : degree ≤ 44) (edgesH edgesJ : Nat) : Prop :=
  coloringDegreeSum (order45NeighborhoodInduced color degree bounded) =
      2 * edgesH ∧
    coloringDegreeSum (order45DualInduced color degree bounded) = 2 * edgesJ

/-- Published edge-range inputs bound the two exact local graph counts. -/
theorem exists_fixedStar_catalogEdgeCounts
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (degree : Nat)
    (bounded : degree ≤ 44) (fixed : HasFixedStar color degree)
    (lowerH upperH lowerJ upperJ : Nat)
    (rangeH : Ramsey45EdgeRange degree lowerH upperH)
    (rangeJ : Ramsey45EdgeRange (44 - degree) lowerJ upperJ) :
    ∃ edgesH edgesJ : Nat,
      HasOrder45CatalogEdgeCounts color degree bounded edgesH edgesJ ∧
      lowerH ≤ edgesH ∧ edgesH ≤ upperH ∧
      lowerJ ≤ edgesJ ∧ edgesJ ≤ upperJ := by
  have hRamsey := fixedStarNeighborhood_isRamsey45Coloring color simple
    ramseyFree degree bounded fixed
  have jRamsey := fixedStarDual_isRamsey45Coloring color simple ramseyFree
    degree bounded fixed
  rcases coloringDegreeSum_even
      (order45NeighborhoodInduced color degree bounded) hRamsey.1 with
    ⟨edgesH, hCount⟩
  rcases coloringDegreeSum_even
      (order45DualInduced color degree bounded) jRamsey.1 with
    ⟨edgesJ, jCount⟩
  have hBounds := rangeH
    (order45NeighborhoodInduced color degree bounded) hRamsey edgesH hCount
  have jBounds := rangeJ
    (order45DualInduced color degree bounded) jRamsey edgesJ jCount
  exact ⟨edgesH, edgesJ, ⟨hCount, jCount⟩,
    hBounds.1, hBounds.2, jBounds.1, jBounds.2⟩

/-- Exact remaining count-binding obligation between the graph-side excess
identity and the published local-catalog ranges. -/
def Order45LocalCatalogCountBinding (degree : Nat)
    (bounded : degree ≤ 44) : Prop :=
  ∀ color : Coloring 45, ∀ localH localJ catalogH catalogJ : Nat,
    HasOrder45LocalEdgeCounts color 0 localH localJ →
    HasOrder45CatalogEdgeCounts color degree bounded catalogH catalogJ →
    localH = catalogH ∧ localJ = catalogJ

theorem order45LocalEdgeCounts_bounds_of_catalog
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (degree : Nat)
    (bounded : degree ≤ 44) (fixed : HasFixedStar color degree)
    (lowerH upperH lowerJ upperJ : Nat)
    (rangeH : Ramsey45EdgeRange degree lowerH upperH)
    (rangeJ : Ramsey45EdgeRange (44 - degree) lowerJ upperJ)
    (binding : Order45LocalCatalogCountBinding degree bounded)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    lowerH ≤ edgesH ∧ edgesH ≤ upperH ∧
      lowerJ ≤ edgesJ ∧ edgesJ ≤ upperJ := by
  rcases exists_fixedStar_catalogEdgeCounts color simple ramseyFree degree
      bounded fixed lowerH upperH lowerJ upperJ rangeH rangeJ with
    ⟨catalogH, catalogJ, catalogCounts, hLower, hUpper, jLower, jUpper⟩
  rcases binding color edgesH edgesJ catalogH catalogJ counts catalogCounts with
    ⟨rfl, rfl⟩
  exact ⟨hLower, hUpper, jLower, jUpper⟩

#print axioms neighborInduced_isRamsey45Coloring
#print axioms fixedStarNeighborhood_isRamsey45Coloring
#print axioms fixedStarDual_isRamsey45Coloring
#print axioms exists_fixedStar_catalogEdgeCounts
#print axioms order45LocalEdgeCounts_bounds_of_catalog

end Ramsey55
