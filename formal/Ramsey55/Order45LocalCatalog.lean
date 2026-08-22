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

/-- Add a block of isolated labels before a colouring.  This generic
construction lets the catalog graphs be compared with the 45-label local
graphs without expanding a concrete 45-by-45 matrix. -/
def prependIsolatedColoring {order : Nat} (leading : Nat)
    (color : Coloring order) : Coloring (leading + order) := fun x y =>
  Fin.addCases (fun _ => false)
    (fun i => Fin.addCases (fun _ => false) (fun j => color i j) y) x

/-- Add a block of isolated labels after a colouring. -/
def appendIsolatedColoring {order : Nat} (suffix : Nat)
    (color : Coloring order) : Coloring (order + suffix) := fun x y =>
  Fin.addCases
    (fun i => Fin.addCases (fun j => color i j) (fun _ => false) y)
    (fun _ => false) x

@[simp] theorem fin_addCases_false (left right : Nat)
    (i : Fin (left + right)) :
    Fin.addCases (fun _ : Fin left => false) (fun _ : Fin right => false) i =
      false := by
  refine Fin.addCases (fun j => ?_) (fun j => ?_) i
  · exact Fin.addCases_left j
  · exact Fin.addCases_right j

@[simp] theorem prependIsolatedColoring_leading {order : Nat}
    (leading : Nat) (color : Coloring order) (i : Fin leading)
    (y : Fin (leading + order)) :
    prependIsolatedColoring leading color
      (Fin.castLE (Nat.le_add_right leading order) i) y = false := by
  unfold prependIsolatedColoring
  rw [show Fin.castLE (Nat.le_add_right leading order) i =
    Fin.castAdd order i by rfl]
  exact Fin.addCases_left i

@[simp] theorem prependIsolatedColoring_leading_castAdd {order : Nat}
    (leading : Nat) (color : Coloring order) (i : Fin leading)
    (y : Fin (leading + order)) :
    prependIsolatedColoring leading color (Fin.castAdd order i) y = false := by
  exact Fin.addCases_left i

@[simp] theorem prependIsolatedColoring_active_leading {order : Nat}
    (leading : Nat) (color : Coloring order) (i : Fin order)
    (j : Fin leading) :
    prependIsolatedColoring leading color (Fin.natAdd leading i)
      (Fin.castLE (Nat.le_add_right leading order) j) = false := by
  unfold prependIsolatedColoring
  rw [Fin.addCases_right]
  rw [show Fin.castLE (Nat.le_add_right leading order) j =
    Fin.castAdd order j by rfl]
  exact Fin.addCases_left j

@[simp] theorem prependIsolatedColoring_active_leading_castAdd {order : Nat}
    (leading : Nat) (color : Coloring order) (i : Fin order)
    (j : Fin leading) :
    prependIsolatedColoring leading color (Fin.natAdd leading i)
      (Fin.castAdd order j) = false := by
  simp [prependIsolatedColoring]

@[simp] theorem prependIsolatedColoring_active {order : Nat}
    (leading : Nat) (color : Coloring order) (i j : Fin order) :
    prependIsolatedColoring leading color (Fin.natAdd leading i)
      (Fin.natAdd leading j) = color i j := by
  simp [prependIsolatedColoring]

@[simp] theorem appendIsolatedColoring_active {order : Nat}
    (suffix : Nat) (color : Coloring order) (i j : Fin order) :
    appendIsolatedColoring suffix color
      (Fin.castLE (Nat.le_add_right order suffix) i)
      (Fin.castLE (Nat.le_add_right order suffix) j) = color i j := by
  unfold appendIsolatedColoring
  rw [show Fin.castLE (Nat.le_add_right order suffix) i =
    Fin.castAdd suffix i by rfl]
  rw [show Fin.castLE (Nat.le_add_right order suffix) j =
    Fin.castAdd suffix j by rfl]
  simp

@[simp] theorem appendIsolatedColoring_active_castAdd {order : Nat}
    (suffix : Nat) (color : Coloring order) (i j : Fin order) :
    appendIsolatedColoring suffix color (Fin.castAdd suffix i)
      (Fin.castAdd suffix j) = color i j := by
  simp [appendIsolatedColoring]

@[simp] theorem appendIsolatedColoring_active_trailing {order : Nat}
    (suffix : Nat) (color : Coloring order) (i : Fin order)
    (j : Fin suffix) :
    appendIsolatedColoring suffix color
      (Fin.castLE (Nat.le_add_right order suffix) i) (Fin.natAdd order j) =
        false := by
  unfold appendIsolatedColoring
  rw [show Fin.castLE (Nat.le_add_right order suffix) i =
    Fin.castAdd suffix i by rfl]
  simp

@[simp] theorem appendIsolatedColoring_active_trailing_castAdd {order : Nat}
    (suffix : Nat) (color : Coloring order) (i : Fin order)
    (j : Fin suffix) :
    appendIsolatedColoring suffix color (Fin.castAdd suffix i)
      (Fin.natAdd order j) = false := by
  simp [appendIsolatedColoring]

@[simp] theorem appendIsolatedColoring_trailing {order : Nat}
    (suffix : Nat) (color : Coloring order) (i : Fin suffix)
    (y : Fin (order + suffix)) :
    appendIsolatedColoring suffix color (Fin.natAdd order i) y = false := by
  simp [appendIsolatedColoring]

theorem sumFin2_intEdgeWeight_prependIsolatedColoring {order : Nat}
    (leading : Nat) (color : Coloring order) :
    sumFin2 (fun x y =>
      intEdgeWeight (prependIsolatedColoring leading color x y)) =
      sumFin2 (fun x y => intEdgeWeight (color x y)) := by
  unfold sumFin2
  rw [List.ofFn_add]
  simp [List.ofFn_add, intEdgeWeight, sum_ofFn_zero_int]

theorem sumFin2_intEdgeWeight_appendIsolatedColoring {order : Nat}
    (suffix : Nat) (color : Coloring order) :
    sumFin2 (fun x y =>
      intEdgeWeight (appendIsolatedColoring suffix color x y)) =
      sumFin2 (fun x y => intEdgeWeight (color x y)) := by
  unfold sumFin2
  rw [List.ofFn_add]
  simp [List.ofFn_add, intEdgeWeight, sum_ofFn_zero_int]

theorem coloringDegreeSum_prependIsolatedColoring {order : Nat}
    (leading : Nat) (color : Coloring order) :
    coloringDegreeSum (prependIsolatedColoring leading color) =
      coloringDegreeSum color := by
  have equality :=
    sumFin2_intEdgeWeight_prependIsolatedColoring leading color
  rw [sumFin2_intEdgeWeight_eq_degreeSum,
    sumFin2_intEdgeWeight_eq_degreeSum] at equality
  exact_mod_cast equality

theorem coloringDegreeSum_appendIsolatedColoring {order : Nat}
    (suffix : Nat) (color : Coloring order) :
    coloringDegreeSum (appendIsolatedColoring suffix color) =
      coloringDegreeSum color := by
  have equality :=
    sumFin2_intEdgeWeight_appendIsolatedColoring suffix color
  rw [sumFin2_intEdgeWeight_eq_degreeSum,
    sumFin2_intEdgeWeight_eq_degreeSum] at equality
  exact_mod_cast equality

@[simp] theorem appendIsolatedColoring_zero {order : Nat}
    (color : Coloring order) : appendIsolatedColoring 0 color = color := by
  funext x y
  refine Fin.addCases ?_ ?_ x
  · intro i
    refine Fin.addCases ?_ ?_ y
    · intro j
      exact appendIsolatedColoring_active_castAdd 0 color i j
    · intro impossible
      exact Fin.elim0 impossible
  · intro impossible
    exact Fin.elim0 impossible

/-- Pad both sides of the active catalog block by isolated labels. -/
def sandwichIsolatedColoring {order : Nat} (leading trailing : Nat)
    (color : Coloring order) : Coloring ((leading + order) + trailing) :=
  appendIsolatedColoring trailing (prependIsolatedColoring leading color)

theorem coloringDegreeSum_sandwichIsolatedColoring {order : Nat}
    (leading trailing : Nat) (color : Coloring order) :
    coloringDegreeSum (sandwichIsolatedColoring leading trailing color) =
      coloringDegreeSum color := by
  rw [sandwichIsolatedColoring,
    coloringDegreeSum_appendIsolatedColoring,
    coloringDegreeSum_prependIsolatedColoring]

/-- Reindexing solely by a type-size equality preserves the concrete degree
sum. -/
theorem coloringDegreeSum_relabel_finCast {left right : Nat}
    (size : left = right) (color : Coloring right) :
    coloringDegreeSum (relabelColoring color (Fin.cast size)) =
      coloringDegreeSum color := by
  subst right
  rfl

theorem order45NeighborhoodPaddingSize (degree : Nat)
    (bounded : degree ≤ 44) : (1 + degree) + (44 - degree) = 45 := by
  omega

theorem order45DualPaddingSize (degree : Nat) (bounded : degree ≤ 44) :
    (degree + 1 + (44 - degree)) + 0 = 45 := by
  omega

theorem order45NeighborhoodPadding_activeMap (degree : Nat)
    (bounded : degree ≤ 44) (i : Fin degree) :
    Fin.cast (order45NeighborhoodPaddingSize degree bounded)
      (Fin.castAdd (44 - degree) (Fin.natAdd 1 i)) =
        order45NeighborBlockMap degree bounded i := by
  apply Fin.ext
  simp [order45NeighborBlockMap]
  omega

theorem order45NeighborhoodPadding_trailingMap (degree : Nat)
    (bounded : degree ≤ 44) (i : Fin (44 - degree)) :
    Fin.cast (order45NeighborhoodPaddingSize degree bounded)
      (Fin.natAdd (1 + degree) i) =
        order45NonneighborBlockMap degree bounded i := by
  apply Fin.ext
  simp [order45NonneighborBlockMap]
  omega

theorem localNeighborhoodColoring_fixedStar_active
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (i j : Fin degree) :
    localNeighborhoodColoring color 0
      (order45NeighborBlockMap degree bounded i)
      (order45NeighborBlockMap degree bounded j) =
        order45NeighborhoodInduced color degree bounded i j := by
  by_cases equal : i = j
  · subst j
    simp [localNeighborhoodColoring, order45NeighborhoodInduced,
      relabelColoring, simple.1]
  · have mappedNe : order45NeighborBlockMap degree bounded i ≠
        order45NeighborBlockMap degree bounded j := fun mapped =>
      equal (order45NeighborBlockMap_injective degree bounded mapped)
    have iNonzero : (order45NeighborBlockMap degree bounded i) ≠ 0 := by
      intro mapped
      have values := congrArg Fin.val mapped
      simp [order45NeighborBlockMap] at values
    have jNonzero : (order45NeighborBlockMap degree bounded j) ≠ 0 := by
      intro mapped
      have values := congrArg Fin.val mapped
      simp [order45NeighborBlockMap] at values
    have iEdge : color 0 (order45NeighborBlockMap degree bounded i) = true :=
      fixed.1 _ (by simp [order45NeighborBlockMap]) (by
        simp [order45NeighborBlockMap]
        omega)
    have jEdge : color 0 (order45NeighborBlockMap degree bounded j) = true :=
      fixed.1 _ (by simp [order45NeighborBlockMap]) (by
        simp [order45NeighborBlockMap]
        omega)
    simp [localNeighborhoodColoring, order45NeighborhoodInduced,
      relabelColoring, iNonzero, jNonzero, mappedNe, iEdge, jEdge]

theorem localNeighborhoodColoring_fixedStar_trailing
    (color : Coloring 45) (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (i : Fin (44 - degree))
    (y : Fin 45) :
    localNeighborhoodColoring color 0
      (order45NonneighborBlockMap degree bounded i) y = false := by
  have beyond : degree < (order45NonneighborBlockMap degree bounded i).val := by
    simp [order45NonneighborBlockMap]
    omega
  have nonedge := fixed.2 (order45NonneighborBlockMap degree bounded i) beyond
  by_cases atApex : order45NonneighborBlockMap degree bounded i = 0 <;>
    by_cases yApex : y = 0 <;>
    by_cases equal : order45NonneighborBlockMap degree bounded i = y <;>
    simp [localNeighborhoodColoring, atApex, yApex, equal, nonedge]

theorem localNeighborhoodColoring_fixedStar_trailing_right
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (x : Fin 45)
    (i : Fin (44 - degree)) :
    localNeighborhoodColoring color 0 x
      (order45NonneighborBlockMap degree bounded i) = false := by
  rw [(localNeighborhoodColoring_isSimple color simple 0).2]
  exact localNeighborhoodColoring_fixedStar_trailing color degree bounded
    fixed i x

theorem localNeighborhoodColoring_fixedStar_eq_padding
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) :
    relabelColoring (localNeighborhoodColoring color 0)
        (Fin.cast (order45NeighborhoodPaddingSize degree bounded)) =
      sandwichIsolatedColoring 1 (44 - degree)
        (order45NeighborhoodInduced color degree bounded) := by
  funext x y
  refine Fin.addCases ?_ ?_ x
  · intro xFront
    refine Fin.addCases ?_ ?_ xFront
    · intro xApex
      have mappedApex :
          Fin.cast (order45NeighborhoodPaddingSize degree bounded)
            (Fin.castAdd (44 - degree) (Fin.castAdd degree xApex)) = 0 := by
        apply Fin.ext
        simp
      simp [relabelColoring, sandwichIsolatedColoring,
        appendIsolatedColoring, mappedApex, localNeighborhoodColoring]
    · intro i
      refine Fin.addCases ?_ ?_ y
      · intro yFront
        refine Fin.addCases ?_ ?_ yFront
        · intro yApex
          have mappedApex :
              Fin.cast (order45NeighborhoodPaddingSize degree bounded)
                (Fin.castAdd (44 - degree) (Fin.castAdd degree yApex)) = 0 := by
            apply Fin.ext
            simp
          simp [relabelColoring, sandwichIsolatedColoring,
            appendIsolatedColoring, prependIsolatedColoring, mappedApex,
            localNeighborhoodColoring]
        · intro j
          simp only [relabelColoring]
          rw [show Fin.cast (order45NeighborhoodPaddingSize degree bounded)
              (Fin.castAdd (44 - degree) (Fin.natAdd 1 i)) =
                order45NeighborBlockMap degree bounded i by
              exact order45NeighborhoodPadding_activeMap degree bounded i]
          rw [show Fin.cast (order45NeighborhoodPaddingSize degree bounded)
              (Fin.castAdd (44 - degree) (Fin.natAdd 1 j)) =
                order45NeighborBlockMap degree bounded j by
              exact order45NeighborhoodPadding_activeMap degree bounded j]
          simpa [relabelColoring, sandwichIsolatedColoring] using
            localNeighborhoodColoring_fixedStar_active color simple degree
              bounded fixed i j
      · intro j
        simp only [relabelColoring]
        rw [show Fin.cast (order45NeighborhoodPaddingSize degree bounded)
            (Fin.castAdd (44 - degree) (Fin.natAdd 1 i)) =
              order45NeighborBlockMap degree bounded i by
            exact order45NeighborhoodPadding_activeMap degree bounded i]
        rw [show Fin.cast (order45NeighborhoodPaddingSize degree bounded)
            (Fin.natAdd (1 + degree) j) =
              order45NonneighborBlockMap degree bounded j by
            exact order45NeighborhoodPadding_trailingMap degree bounded j]
        simpa [relabelColoring, sandwichIsolatedColoring] using
          localNeighborhoodColoring_fixedStar_trailing_right color simple
            degree bounded fixed (order45NeighborBlockMap degree bounded i) j
  · intro i
    simp only [relabelColoring]
    rw [show Fin.cast (order45NeighborhoodPaddingSize degree bounded)
        (Fin.natAdd (1 + degree) i) =
          order45NonneighborBlockMap degree bounded i by
        exact order45NeighborhoodPadding_trailingMap degree bounded i]
    simp [sandwichIsolatedColoring,
      localNeighborhoodColoring_fixedStar_trailing color degree bounded
        fixed i]

theorem localNeighborhoodColoring_fixedStar_degreeSum_eq_catalog
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) :
    coloringDegreeSum (localNeighborhoodColoring color 0) =
      coloringDegreeSum (order45NeighborhoodInduced color degree bounded) := by
  have equality := congrArg coloringDegreeSum
    (localNeighborhoodColoring_fixedStar_eq_padding color simple degree
      bounded fixed)
  rw [coloringDegreeSum_relabel_finCast,
    coloringDegreeSum_sandwichIsolatedColoring] at equality
  exact equality

/-- The labels at or before the fixed-star boundary, viewed inside the
ambient order 45. -/
def order45DualLeadingMap (degree : Nat) (bounded : degree ≤ 44) :
    Fin (degree + 1) → Fin 45 := fun i => ⟨i.val, by omega⟩

theorem order45DualPadding_leadingMap (degree : Nat)
    (bounded : degree ≤ 44) (i : Fin (degree + 1)) :
    Fin.cast (order45DualPaddingSize degree bounded)
      (Fin.castAdd 0 (Fin.castAdd (44 - degree) i)) =
        order45DualLeadingMap degree bounded i := by
  apply Fin.ext
  simp [order45DualLeadingMap]

theorem order45DualPadding_activeMap (degree : Nat)
    (bounded : degree ≤ 44) (i : Fin (44 - degree)) :
    Fin.cast (order45DualPaddingSize degree bounded)
      (Fin.castAdd 0 (Fin.natAdd (degree + 1) i)) =
        order45NonneighborBlockMap degree bounded i := by
  apply Fin.ext
  simp [order45NonneighborBlockMap]
  omega

theorem localDualColoring_fixedStar_leading
    (color : Coloring 45) (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (i : Fin (degree + 1))
    (y : Fin 45) :
    localDualColoring color 0 (order45DualLeadingMap degree bounded i) y =
      false := by
  by_cases zero : i.val = 0
  · have atApex : order45DualLeadingMap degree bounded i = 0 := by
      apply Fin.ext
      simp [order45DualLeadingMap, zero]
    simp [localDualColoring, atApex]
  · have positive : 0 < i.val := by omega
    have within : i.val ≤ degree := by omega
    have edge : color 0 (order45DualLeadingMap degree bounded i) = true := by
      apply fixed.1
      · simpa [order45DualLeadingMap] using positive
      · simpa [order45DualLeadingMap] using within
    by_cases atApex : order45DualLeadingMap degree bounded i = 0 <;>
      by_cases yApex : y = 0 <;>
      by_cases equal : order45DualLeadingMap degree bounded i = y <;>
      simp [localDualColoring, atApex, yApex, equal, edge]

theorem localDualColoring_fixedStar_leading_right
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (x : Fin 45)
    (i : Fin (degree + 1)) :
    localDualColoring color 0 x (order45DualLeadingMap degree bounded i) =
      false := by
  rw [(localDualColoring_isSimple color simple 0).2]
  exact localDualColoring_fixedStar_leading color degree bounded fixed i x

theorem localDualColoring_fixedStar_active
    (color : Coloring 45) (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) (i j : Fin (44 - degree)) :
    localDualColoring color 0
      (order45NonneighborBlockMap degree bounded i)
      (order45NonneighborBlockMap degree bounded j) =
        order45DualInduced color degree bounded i j := by
  by_cases equal : i = j
  · subst j
    simp [localDualColoring, order45DualInduced, relabelColoring,
      complementColoring]
  · have mappedNe : order45NonneighborBlockMap degree bounded i ≠
        order45NonneighborBlockMap degree bounded j := fun mapped =>
      equal (order45NonneighborBlockMap_injective degree bounded mapped)
    have iNonzero : (order45NonneighborBlockMap degree bounded i) ≠ 0 := by
      intro mapped
      have values := congrArg Fin.val mapped
      simp [order45NonneighborBlockMap] at values
    have jNonzero : (order45NonneighborBlockMap degree bounded j) ≠ 0 := by
      intro mapped
      have values := congrArg Fin.val mapped
      simp [order45NonneighborBlockMap] at values
    have iBeyond : degree <
        (order45NonneighborBlockMap degree bounded i).val := by
      simp [order45NonneighborBlockMap]
      omega
    have jBeyond : degree <
        (order45NonneighborBlockMap degree bounded j).val := by
      simp [order45NonneighborBlockMap]
      omega
    have iNonedge := fixed.2 _ iBeyond
    have jNonedge := fixed.2 _ jBeyond
    simp [localDualColoring, order45DualInduced, relabelColoring,
      complementColoring, iNonzero, jNonzero, mappedNe, iNonedge, jNonedge]

theorem localDualColoring_fixedStar_eq_padding
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) :
    relabelColoring (localDualColoring color 0)
        (Fin.cast (order45DualPaddingSize degree bounded)) =
      sandwichIsolatedColoring (degree + 1) 0
        (order45DualInduced color degree bounded) := by
  funext x y
  refine Fin.addCases ?_ ?_ x
  · intro xCore
    refine Fin.addCases ?_ ?_ xCore
    · intro i
      simp only [relabelColoring]
      rw [show Fin.cast (order45DualPaddingSize degree bounded)
          (Fin.castAdd 0 (Fin.castAdd (44 - degree) i)) =
            order45DualLeadingMap degree bounded i by
          exact order45DualPadding_leadingMap degree bounded i]
      simp [sandwichIsolatedColoring,
        localDualColoring_fixedStar_leading color degree bounded fixed i]
    · intro i
      refine Fin.addCases ?_ ?_ y
      · intro yCore
        refine Fin.addCases ?_ ?_ yCore
        · intro j
          simp only [relabelColoring]
          rw [show Fin.cast (order45DualPaddingSize degree bounded)
              (Fin.castAdd 0 (Fin.natAdd (degree + 1) i)) =
                order45NonneighborBlockMap degree bounded i by
              exact order45DualPadding_activeMap degree bounded i]
          rw [show Fin.cast (order45DualPaddingSize degree bounded)
              (Fin.castAdd 0 (Fin.castAdd (44 - degree) j)) =
                order45DualLeadingMap degree bounded j by
              exact order45DualPadding_leadingMap degree bounded j]
          simpa [sandwichIsolatedColoring] using
            localDualColoring_fixedStar_leading_right color simple degree
              bounded fixed (order45NonneighborBlockMap degree bounded i) j
        · intro j
          simp only [relabelColoring]
          rw [show Fin.cast (order45DualPaddingSize degree bounded)
              (Fin.castAdd 0 (Fin.natAdd (degree + 1) i)) =
                order45NonneighborBlockMap degree bounded i by
              exact order45DualPadding_activeMap degree bounded i]
          rw [show Fin.cast (order45DualPaddingSize degree bounded)
              (Fin.castAdd 0 (Fin.natAdd (degree + 1) j)) =
                order45NonneighborBlockMap degree bounded j by
              exact order45DualPadding_activeMap degree bounded j]
          simpa [sandwichIsolatedColoring] using
            localDualColoring_fixedStar_active color degree bounded fixed i j
      · intro impossible
        exact Fin.elim0 impossible
  · intro impossible
    exact Fin.elim0 impossible

theorem localDualColoring_fixedStar_degreeSum_eq_catalog
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (degree : Nat) (bounded : degree ≤ 44)
    (fixed : HasFixedStar color degree) :
    coloringDegreeSum (localDualColoring color 0) =
      coloringDegreeSum (order45DualInduced color degree bounded) := by
  have equality := congrArg coloringDegreeSum
    (localDualColoring_fixedStar_eq_padding color simple degree bounded fixed)
  rw [coloringDegreeSum_relabel_finCast,
    coloringDegreeSum_sandwichIsolatedColoring] at equality
  exact equality

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

/-- Exact count-binding contract between the graph-side excess identity and
the published local-catalog ranges. -/
def Order45LocalCatalogCountBinding (degree : Nat)
    (bounded : degree ≤ 44) : Prop :=
  ∀ color : Coloring 45, ∀ localH localJ catalogH catalogJ : Nat,
    IsSimpleColoring color →
    HasFixedStar color degree →
    HasOrder45LocalEdgeCounts color 0 localH localJ →
    HasOrder45CatalogEdgeCounts color degree bounded catalogH catalogJ →
    localH = catalogH ∧ localJ = catalogJ

/-- Isolated-label padding changes neither edge count.  Consequently the
catalog H/J counts are exactly the counts appearing in the local excess
identity. -/
theorem order45LocalCatalogCountBinding (degree : Nat)
    (bounded : degree ≤ 44) :
    Order45LocalCatalogCountBinding degree bounded := by
  intro color localH localJ catalogH catalogJ simple fixed localCounts
    catalogCounts
  have hDegreeSum := localNeighborhoodColoring_fixedStar_degreeSum_eq_catalog
    color simple degree bounded fixed
  have jDegreeSum := localDualColoring_fixedStar_degreeSum_eq_catalog
    color simple degree bounded fixed
  rcases localCounts with ⟨hLocal, jLocal, score⟩
  rcases catalogCounts with ⟨hCatalog, jCatalog⟩
  constructor <;> omega

theorem order45LocalEdgeCounts_bounds_of_catalog
    (color : Coloring 45) (simple : IsSimpleColoring color)
    (ramseyFree : IsRamseyFree55 color) (degree : Nat)
    (bounded : degree ≤ 44) (fixed : HasFixedStar color degree)
    (lowerH upperH lowerJ upperJ : Nat)
    (rangeH : Ramsey45EdgeRange degree lowerH upperH)
    (rangeJ : Ramsey45EdgeRange (44 - degree) lowerJ upperJ)
    (edgesH edgesJ : Nat)
    (counts : HasOrder45LocalEdgeCounts color 0 edgesH edgesJ) :
    lowerH ≤ edgesH ∧ edgesH ≤ upperH ∧
      lowerJ ≤ edgesJ ∧ edgesJ ≤ upperJ := by
  rcases exists_fixedStar_catalogEdgeCounts color simple ramseyFree degree
      bounded fixed lowerH upperH lowerJ upperJ rangeH rangeJ with
    ⟨catalogH, catalogJ, catalogCounts, hLower, hUpper, jLower, jUpper⟩
  rcases order45LocalCatalogCountBinding degree bounded color edgesH edgesJ
      catalogH catalogJ simple fixed counts catalogCounts with ⟨rfl, rfl⟩
  exact ⟨hLower, hUpper, jLower, jUpper⟩

#print axioms neighborInduced_isRamsey45Coloring
#print axioms fixedStarNeighborhood_isRamsey45Coloring
#print axioms fixedStarDual_isRamsey45Coloring
#print axioms exists_fixedStar_catalogEdgeCounts
#print axioms order45LocalCatalogCountBinding
#print axioms order45LocalEdgeCounts_bounds_of_catalog

end Ramsey55
