import Ramsey55.Extension

namespace Ramsey55

/-- Delete the last vertex of a finite colouring. -/
def dropLastColoring {n : Nat} (color : Coloring (n + 1)) : Coloring n :=
  fun u v => color u.castSucc v.castSucc

/-- View a finite colouring through the natural-number interface used by the
certificate checker. Values outside the finite range are irrelevant. -/
def coloringToRaw {n : Nat} (color : Coloring n) : RawColoring :=
  fun u v =>
    if hu : u < n then
      if hv : v < n then color ⟨u, hu⟩ ⟨v, hv⟩ else false
    else false

/-- Colours of the edges from the last vertex to the preceding vertices. -/
def lastApexRaw {n : Nat} (color : Coloring (n + 1)) : Nat → Bool :=
  fun vertex =>
    if h : vertex < n then color ⟨vertex, Nat.lt_succ_of_lt h⟩ (Fin.last n)
    else false

private theorem dropLast_simple {n : Nat} {color : Coloring (n + 1)}
    (simple : IsSimpleColoring color) :
    IsSimpleColoring (dropLastColoring color) := by
  rcases simple with ⟨diagonal, symmetric⟩
  constructor
  · intro vertex
    exact diagonal vertex.castSucc
  · intro u v
    exact symmetric u.castSucc v.castSucc

private theorem dropLast_ramseyFree {n : Nat} {color : Coloring (n + 1)}
    (ramseyFree : IsRamseyFree55 color) :
    IsRamseyFree55 (dropLastColoring color) := by
  intro a b c d e hab hbc hcd hde mono
  apply ramseyFree a.castSucc b.castSucc c.castSucc d.castSucc e.castSucc
    hab hbc hcd hde
  simpa [dropLastColoring, Monochromatic5] using mono

private theorem lastApex_avoids {n : Nat} {color : Coloring (n + 1)}
    (ramseyFree : IsRamseyFree55 color) :
    AttachmentAvoidsMonochromatic5 n
      (coloringToRaw (dropLastColoring color)) (lastApexRaw color) := by
  intro a b c d hab hbc hcd hdn creates
  have ha : a < n := by omega
  have hb : b < n := by omega
  have hc : c < n := by omega
  let aFin : Fin (n + 1) := ⟨a, Nat.lt_succ_of_lt ha⟩
  let bFin : Fin (n + 1) := ⟨b, Nat.lt_succ_of_lt hb⟩
  let cFin : Fin (n + 1) := ⟨c, Nat.lt_succ_of_lt hc⟩
  let dFin : Fin (n + 1) := ⟨d, Nat.lt_succ_of_lt hdn⟩
  simp [ExtensionCreatesMonochromatic5, Monochromatic4Raw,
    coloringToRaw, dropLastColoring, lastApexRaw,
    ha, hb, hc, hdn] at creates
  rcases creates with
    ⟨⟨edgeAC, edgeAD, edgeBC, edgeBD, edgeCD⟩,
      apexA, apexB, apexC, apexD⟩
  apply ramseyFree aFin bFin cFin dFin (Fin.last n) hab hbc hcd
    (by simpa [dFin] using hdn)
  exact ⟨edgeAC, edgeAD, apexA, edgeBC, edgeBD, apexB,
    edgeCD, apexC, apexD⟩

/-- General one-vertex reduction: if every Ramsey-free colouring on `n`
vertices has a checked nonextension proof, then `n+1` vertices force a
monochromatic K5. -/
theorem forcesMonochromatic5_succ_of_all_nonextendable (n : Nat)
    (allNonextendable :
      ∀ base : Coloring n,
        IsSimpleColoring base → IsRamseyFree55 base →
        HasNoRamseyFreeOneVertexExtension n (coloringToRaw base)) :
    ForcesMonochromatic5 (n + 1) := by
  intro color simple ramseyFree
  let base := dropLastColoring color
  have noExtension := allNonextendable base
    (dropLast_simple simple) (dropLast_ramseyFree ramseyFree)
  exact noExtension (lastApexRaw color) (lastApex_avoids ramseyFree)

/-- The exact upper-bound obligation is reduced to a finite classification of
the Ramsey-free 42-vertex colourings plus their nonextension certificates. -/
theorem forcesMonochromatic5_43_of_all_42_nonextendable
    (allNonextendable :
      ∀ base : Coloring 42,
        IsSimpleColoring base → IsRamseyFree55 base →
        HasNoRamseyFreeOneVertexExtension 42 (coloringToRaw base)) :
    ForcesMonochromatic5 43 := by
  simpa using forcesMonochromatic5_succ_of_all_nonextendable 42 allNonextendable

/-- A stronger multiplicity hypothesis immediately supplies the
nonextendability hypothesis used by the one-vertex reduction. -/
theorem forcesMonochromatic5_43_of_all_42_atLeastTwo
    (allAtLeastTwo :
      ∀ base : Coloring 42,
        IsSimpleColoring base → IsRamseyFree55 base →
        EveryExtensionCreatesAtLeastTwoMonochromatic5 42
          (coloringToRaw base)) :
    ForcesMonochromatic5 43 := by
  apply forcesMonochromatic5_43_of_all_42_nonextendable
  intro base simple ramseyFree
  exact atLeastTwoExtensions_imply_noRamseyFreeExtension
    (allAtLeastTwo base simple ramseyFree)

end Ramsey55
