import Ramsey55.Ramsey45Target

namespace Ramsey55

/-! ## Reducing the two small gluing inputs to `R(3,4) ≤ 9` -/

def ForcesRed3OrBlue4 (n : Nat) : Prop :=
  ∀ color : Coloring n, IsSimpleColoring color →
    (∃ a b c : Fin n, Distinct3 a b c ∧ RedClique3 color a b c) ∨
      (∃ a b c d : Fin n,
        Distinct4 a b c d ∧ BlueClique4 color a b c d)

theorem Distinct3.map {source target : Nat}
    (vertexMap : Fin target → Fin source)
    (injective : Function.Injective vertexMap)
    {a b c : Fin target} (distinct : Distinct3 a b c) :
    Distinct3 (vertexMap a) (vertexMap b) (vertexMap c) := by
  rcases distinct with ⟨ab, ac, bc⟩
  exact ⟨fun equal => ab (injective equal),
    fun equal => ac (injective equal),
    fun equal => bc (injective equal)⟩

def ramsey35FirstNeighborMap : Fin 5 → Fin 14 :=
  fun i => ⟨i.val + 1, by omega⟩

def ramsey35FirstNonneighborMap (degree : Nat) (small : degree ≤ 4) :
    Fin 9 → Fin 14 := fun i => ⟨degree + i.val + 1, by omega⟩

def ramsey44FirstNeighborMap : Fin 9 → Fin 18 :=
  fun i => ⟨i.val + 1, by omega⟩

def ramsey44FirstNonneighborMap (degree : Nat) (small : degree ≤ 8) :
    Fin 9 → Fin 18 := fun i => ⟨degree + i.val + 1, by omega⟩

theorem ramsey35FirstNeighborMap_injective :
    Function.Injective ramsey35FirstNeighborMap := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey35FirstNeighborMap] at values
  omega

theorem ramsey35FirstNonneighborMap_injective (degree : Nat)
    (small : degree ≤ 4) :
    Function.Injective (ramsey35FirstNonneighborMap degree small) := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey35FirstNonneighborMap] at values
  omega

theorem ramsey44FirstNeighborMap_injective :
    Function.Injective ramsey44FirstNeighborMap := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey44FirstNeighborMap] at values
  omega

theorem ramsey44FirstNonneighborMap_injective (degree : Nat)
    (small : degree ≤ 8) :
    Function.Injective (ramsey44FirstNonneighborMap degree small) := by
  intro left right equal
  apply Fin.ext
  have values := congrArg Fin.val equal
  simp [ramsey44FirstNonneighborMap] at values
  omega

theorem forcesRed3OrBlue5_fixedStar_of_r34
    (r34 : ForcesRed3OrBlue4 9)
    (color : Coloring 14) (simple : IsSimpleColoring color)
    (degree : Nat) (fixed : HasFixedStar color degree) :
    (∃ a b c : Fin 14, Distinct3 a b c ∧ RedClique3 color a b c) ∨
      (∃ a b c d e : Fin 14,
        Distinct5 a b c d e ∧ BlueClique5 color a b c d e) := by
  by_cases red : ∃ a b c : Fin 14,
      Distinct3 a b c ∧ RedClique3 color a b c
  · exact Or.inl red
  right
  by_cases large : 5 ≤ degree
  · have neighbor (i : Fin 5) :
        color 0 (ramsey35FirstNeighborMap i) = true := by
      apply fixed.1
      · simp [ramsey35FirstNeighborMap]
      · simp [ramsey35FirstNeighborMap]
        omega
    have nonzero (i : Fin 5) :
        (0 : Fin 14) ≠ ramsey35FirstNeighborMap i := by
      intro equal
      have values := congrArg Fin.val equal
      simp [ramsey35FirstNeighborMap] at values
    have blueEdge (i j : Fin 5) (distinct : i ≠ j) :
        color (ramsey35FirstNeighborMap i)
            (ramsey35FirstNeighborMap j) = false := by
      by_cases edge : color (ramsey35FirstNeighborMap i)
          (ramsey35FirstNeighborMap j) = true
      · exfalso
        apply red
        refine ⟨0, ramsey35FirstNeighborMap i,
          ramsey35FirstNeighborMap j, ?_, ?_⟩
        · exact ⟨nonzero i, nonzero j,
            fun equal => distinct (ramsey35FirstNeighborMap_injective equal)⟩
        · exact ⟨neighbor i, neighbor j, edge⟩
      · cases value : color (ramsey35FirstNeighborMap i)
            (ramsey35FirstNeighborMap j) <;> simp_all
    let a := ramsey35FirstNeighborMap (0 : Fin 5)
    let b := ramsey35FirstNeighborMap (1 : Fin 5)
    let c := ramsey35FirstNeighborMap (2 : Fin 5)
    let d := ramsey35FirstNeighborMap (3 : Fin 5)
    let e := ramsey35FirstNeighborMap (4 : Fin 5)
    have ab : color a b = false := blueEdge 0 1 (by decide)
    have ac : color a c = false := blueEdge 0 2 (by decide)
    have ad : color a d = false := blueEdge 0 3 (by decide)
    have ae : color a e = false := blueEdge 0 4 (by decide)
    have bc : color b c = false := blueEdge 1 2 (by decide)
    have bd : color b d = false := blueEdge 1 3 (by decide)
    have be : color b e = false := blueEdge 1 4 (by decide)
    have cd : color c d = false := blueEdge 2 3 (by decide)
    have ce : color c e = false := blueEdge 2 4 (by decide)
    have de : color d e = false := blueEdge 3 4 (by decide)
    refine ⟨a, b, c, d, e, ?_, ?_⟩
    · exact Distinct5.map ramsey35FirstNeighborMap
        ramsey35FirstNeighborMap_injective (by simp [Distinct5])
    · exact ⟨by simp [Monochromatic5, ab, ac, ad, ae, bc, bd, be, cd,
        ce, de], ab⟩
  · have small : degree ≤ 4 := by omega
    let vertexMap := ramsey35FirstNonneighborMap degree small
    let induced := relabelColoring color vertexMap
    have inducedSimple : IsSimpleColoring induced :=
      relabelColoring_isSimple color vertexMap simple
    have nonneighbor (i : Fin 9) : color 0 (vertexMap i) = false := by
      apply fixed.2
      simp [vertexMap, ramsey35FirstNonneighborMap]
      omega
    have nonzero (i : Fin 9) : (0 : Fin 14) ≠ vertexMap i := by
      intro equal
      have values := congrArg Fin.val equal
      simp [vertexMap, ramsey35FirstNonneighborMap] at values
    rcases r34 induced inducedSimple with triangle | blue
    · rcases triangle with ⟨a, b, c, distinct, clique⟩
      exfalso
      apply red
      exact ⟨vertexMap a, vertexMap b, vertexMap c,
        Distinct3.map vertexMap
          (ramsey35FirstNonneighborMap_injective degree small) distinct,
        by simpa [induced, relabelColoring, RedClique3] using clique⟩
    · rcases blue with ⟨a, b, c, d, distinct, clique⟩
      have mappedDistinct := Distinct4.map vertexMap
        (ramsey35FirstNonneighborMap_injective degree small) distinct
      have mappedBlue : BlueClique4 color (vertexMap a) (vertexMap b)
          (vertexMap c) (vertexMap d) := by
        simpa [induced, relabelColoring, BlueClique4] using clique
      rcases mappedDistinct with ⟨abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
      rcases mappedBlue with ⟨ab, ac, ad, bc, bd, cd⟩
      exact ⟨0, vertexMap a, vertexMap b, vertexMap c, vertexMap d,
        ⟨nonzero a, nonzero b, nonzero c, nonzero d,
          abNe, acNe, adNe, bcNe, bdNe, cdNe⟩,
        ⟨by simp [Monochromatic5, nonneighbor, ab, ac, ad, bc, bd, cd],
          nonneighbor a⟩⟩

theorem forcesRed3OrBlue5_14_of_r34
    (r34 : ForcesRed3OrBlue4 9) : ForcesRed3OrBlue5 14 := by
  intro color simple
  let vertexMap := starVertexMap color 0
  let normalized := relabelColoring color vertexMap
  have injective : Function.Injective vertexMap :=
    (starVertexMap_isVertexRelabeling color 0).1
  have normalizedSimple : IsSimpleColoring normalized :=
    relabelColoring_isSimple color vertexMap simple
  have fixed : HasFixedStar normalized (coloringDegree color 0) :=
    relabelColoring_starVertexMap_hasFixedStar color 0 simple
  rcases forcesRed3OrBlue5_fixedStar_of_r34 r34 normalized normalizedSimple
      (coloringDegree color 0) fixed with red | blue
  · rcases red with ⟨a, b, c, distinct, clique⟩
    exact Or.inl ⟨vertexMap a, vertexMap b, vertexMap c,
      Distinct3.map vertexMap injective distinct,
      by simpa [normalized, relabelColoring, RedClique3] using clique⟩
  · rcases blue with ⟨a, b, c, d, e, distinct, clique⟩
    exact Or.inr ⟨vertexMap a, vertexMap b, vertexMap c, vertexMap d,
      vertexMap e, Distinct5.map vertexMap injective distinct,
      by simpa [normalized, relabelColoring, BlueClique5, Monochromatic5]
        using clique⟩

theorem forcesRed4OrBlue4_fixedStar_of_r34
    (r34 : ForcesRed3OrBlue4 9)
    (color : Coloring 18) (simple : IsSimpleColoring color)
    (degree : Nat) (fixed : HasFixedStar color degree) :
    (∃ a b c d : Fin 18,
      Distinct4 a b c d ∧ RedClique4 color a b c d) ∨
      (∃ a b c d : Fin 18,
        Distinct4 a b c d ∧ BlueClique4 color a b c d) := by
  by_cases large : 9 ≤ degree
  · let vertexMap := ramsey44FirstNeighborMap
    let induced := relabelColoring color vertexMap
    have inducedSimple : IsSimpleColoring induced :=
      relabelColoring_isSimple color vertexMap simple
    have neighbor (i : Fin 9) : color 0 (vertexMap i) = true := by
      apply fixed.1
      · simp [vertexMap, ramsey44FirstNeighborMap]
      · simp [vertexMap, ramsey44FirstNeighborMap]
        omega
    have nonzero (i : Fin 9) : (0 : Fin 18) ≠ vertexMap i := by
      intro equal
      have values := congrArg Fin.val equal
      simp [vertexMap, ramsey44FirstNeighborMap] at values
    rcases r34 induced inducedSimple with triangle | blue
    · rcases triangle with ⟨a, b, c, distinct, clique⟩
      have mappedDistinct := Distinct3.map vertexMap
        ramsey44FirstNeighborMap_injective distinct
      have mappedClique : RedClique3 color (vertexMap a) (vertexMap b)
          (vertexMap c) := by
        simpa [induced, relabelColoring, RedClique3] using clique
      exact Or.inl ⟨0, vertexMap a, vertexMap b, vertexMap c,
        ⟨nonzero a, nonzero b, nonzero c, mappedDistinct.1,
          mappedDistinct.2.1, mappedDistinct.2.2⟩,
        ⟨neighbor a, neighbor b, neighbor c, mappedClique.1,
          mappedClique.2.1, mappedClique.2.2⟩⟩
    · rcases blue with ⟨a, b, c, d, distinct, clique⟩
      exact Or.inr ⟨vertexMap a, vertexMap b, vertexMap c, vertexMap d,
        Distinct4.map vertexMap ramsey44FirstNeighborMap_injective distinct,
        by simpa [induced, relabelColoring, BlueClique4] using clique⟩
  · have small : degree ≤ 8 := by omega
    let vertexMap := ramsey44FirstNonneighborMap degree small
    let complemented := complementColoring color
    let induced := relabelColoring complemented vertexMap
    have inducedSimple : IsSimpleColoring induced :=
      relabelColoring_isSimple complemented vertexMap
        (complementColoring_isSimple color simple)
    have nonneighbor (i : Fin 9) : color 0 (vertexMap i) = false := by
      apply fixed.2
      simp [vertexMap, ramsey44FirstNonneighborMap]
      omega
    have nonzero (i : Fin 9) : (0 : Fin 18) ≠ vertexMap i := by
      intro equal
      have values := congrArg Fin.val equal
      simp [vertexMap, ramsey44FirstNonneighborMap] at values
    rcases r34 induced inducedSimple with triangle | blue
    · rcases triangle with ⟨a, b, c, distinct, clique⟩
      have mappedDistinct := Distinct3.map vertexMap
        (ramsey44FirstNonneighborMap_injective degree small) distinct
      rcases mappedDistinct with ⟨abNe, acNe, bcNe⟩
      have ab : color (vertexMap a) (vertexMap b) = false := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          abNe] using clique.1
      have ac : color (vertexMap a) (vertexMap c) = false := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          acNe] using clique.2.1
      have bc : color (vertexMap b) (vertexMap c) = false := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          bcNe] using clique.2.2
      exact Or.inr ⟨0, vertexMap a, vertexMap b, vertexMap c,
        ⟨nonzero a, nonzero b, nonzero c, abNe, acNe, bcNe⟩,
        ⟨nonneighbor a, nonneighbor b, nonneighbor c, ab, ac, bc⟩⟩
    · rcases blue with ⟨a, b, c, d, distinct, clique⟩
      have mappedDistinct := Distinct4.map vertexMap
        (ramsey44FirstNonneighborMap_injective degree small) distinct
      rcases mappedDistinct with ⟨abNe, acNe, adNe, bcNe, bdNe, cdNe⟩
      have ab : color (vertexMap a) (vertexMap b) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          abNe] using clique.1
      have ac : color (vertexMap a) (vertexMap c) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          acNe] using clique.2.1
      have ad : color (vertexMap a) (vertexMap d) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          adNe] using clique.2.2.1
      have bc : color (vertexMap b) (vertexMap c) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          bcNe] using clique.2.2.2.1
      have bd : color (vertexMap b) (vertexMap d) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          bdNe] using clique.2.2.2.2.1
      have cd : color (vertexMap c) (vertexMap d) = true := by
        simpa [induced, relabelColoring, complemented, complementColoring,
          cdNe] using clique.2.2.2.2.2
      exact Or.inl ⟨vertexMap a, vertexMap b, vertexMap c, vertexMap d,
        ⟨abNe, acNe, adNe, bcNe, bdNe, cdNe⟩,
        ⟨ab, ac, ad, bc, bd, cd⟩⟩

theorem forcesRed4OrBlue4_18_of_r34
    (r34 : ForcesRed3OrBlue4 9) : ForcesRed4OrBlue4 18 := by
  intro color simple
  let vertexMap := starVertexMap color 0
  let normalized := relabelColoring color vertexMap
  have injective : Function.Injective vertexMap :=
    (starVertexMap_isVertexRelabeling color 0).1
  have normalizedSimple : IsSimpleColoring normalized :=
    relabelColoring_isSimple color vertexMap simple
  have fixed : HasFixedStar normalized (coloringDegree color 0) :=
    relabelColoring_starVertexMap_hasFixedStar color 0 simple
  rcases forcesRed4OrBlue4_fixedStar_of_r34 r34 normalized normalizedSimple
      (coloringDegree color 0) fixed with red | blue
  · rcases red with ⟨a, b, c, d, distinct, clique⟩
    exact Or.inl ⟨vertexMap a, vertexMap b, vertexMap c, vertexMap d,
      Distinct4.map vertexMap injective distinct,
      by simpa [normalized, relabelColoring, RedClique4] using clique⟩
  · rcases blue with ⟨a, b, c, d, distinct, clique⟩
    exact Or.inr ⟨vertexMap a, vertexMap b, vertexMap c, vertexMap d,
      Distinct4.map vertexMap injective distinct,
      by simpa [normalized, relabelColoring, BlueClique4] using clique⟩

theorem forcesRed4OrBlue5_of_r34_and_threeExactFixedStarUnsat
    (r34 : ForcesRed3OrBlue4 9)
    (unsat8 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 8))
    (unsat10 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 10))
    (unsat12 : CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 12)) :
    ForcesRed4OrBlue5 25 := by
  exact forcesRed4OrBlue5_of_threeExactFixedStarUnsat
    (forcesRed3OrBlue5_14_of_r34 r34)
    (forcesRed4OrBlue4_18_of_r34 r34) unsat8 unsat10 unsat12

#print axioms forcesRed3OrBlue5_14_of_r34
#print axioms forcesRed4OrBlue4_18_of_r34
#print axioms forcesRed4OrBlue5_of_r34_and_threeExactFixedStarUnsat

end Ramsey55
