import Ramsey55.Checker

namespace Ramsey55

/-- A complete decision tree covering all ways to attach one new vertex.
At a leaf, the four named old vertices and their four apex edges have the
given colour. -/
inductive ExtensionCover where
  | leaf (color : Bool) (a b c d : Nat)
  | branch (vertex : Nat) (whenTrue whenFalse : ExtensionCover)
deriving Repr

/-- A stronger cover whose leaves exhibit two distinct monochromatic
five-sets through the new apex. -/
inductive ExtensionCover2 where
  | leaf (firstColor : Bool) (a b c d : Nat)
      (secondColor : Bool) (p q r s : Nat)
  | branch (vertex : Nat) (whenTrue whenFalse : ExtensionCover2)
deriving Repr

/-- Six old edges on four vertices have one colour. -/
def Monochromatic4Raw (base : RawColoring) (a b c d : Nat) : Prop :=
  base a c = base a b ∧
  base a d = base a b ∧
  base b c = base a b ∧
  base b d = base a b ∧
  base c d = base a b

/-- Executable counterpart of `Monochromatic4Raw`. -/
def monochromatic4RawBool (base : RawColoring) (a b c d : Nat) : Bool :=
  base a c == base a b &&
  base a d == base a b &&
  base b c == base a b &&
  base b d == base a b &&
  base c d == base a b

/-- The four old vertices together with the new apex make a monochromatic
five-set. `apex v` is the colour of the new edge to old vertex `v`. -/
def ExtensionCreatesMonochromatic5 (base : RawColoring)
    (apex : Nat → Bool) (a b c d : Nat) : Prop :=
  Monochromatic4Raw base a b c d ∧
  apex a = base a b ∧
  apex b = base a b ∧
  apex c = base a b ∧
  apex d = base a b

/-- An apex attachment avoids every monochromatic five-set that contains the
apex. If the base graph is already Ramsey-free, this is precisely the
condition for its one-vertex extension to remain Ramsey-free. -/
def AttachmentAvoidsMonochromatic5 (n : Nat) (base : RawColoring)
    (apex : Nat → Bool) : Prop :=
  ∀ a b c d : Nat,
    a < b → b < c → c < d → d < n →
    ¬ ExtensionCreatesMonochromatic5 base apex a b c d

/-- Every assignment of the new edges creates a monochromatic K5 through the
new vertex. -/
def HasNoRamseyFreeOneVertexExtension (n : Nat)
    (base : RawColoring) : Prop :=
  ∀ apex : Nat → Bool, ¬ AttachmentAvoidsMonochromatic5 n base apex

/-- Every attachment creates two different monochromatic five-sets through
the apex. The two old four-sets distinguish the resulting five-sets. -/
def ExtensionCreatesAtLeastTwoMonochromatic5 (n : Nat)
    (base : RawColoring) (apex : Nat → Bool) : Prop :=
  ∃ a b c d p q r s : Nat,
    a < b ∧ b < c ∧ c < d ∧ d < n ∧
    p < q ∧ q < r ∧ r < s ∧ s < n ∧
    [a, b, c, d] ≠ [p, q, r, s] ∧
    ExtensionCreatesMonochromatic5 base apex a b c d ∧
    ExtensionCreatesMonochromatic5 base apex p q r s

def EveryExtensionCreatesAtLeastTwoMonochromatic5 (n : Nat)
    (base : RawColoring) : Prop :=
  ∀ apex : Nat → Bool,
    ExtensionCreatesAtLeastTwoMonochromatic5 n base apex

/-- Executable certificate predicate. `assignedTrue` and `assignedFalse`
record the branch decisions on the path from the root. -/
def checkExtensionLeaf (n : Nat) (base : RawColoring) (color : Bool)
    (a b c d : Nat) (assignedTrue assignedFalse : List Nat) : Bool :=
  decide (a < b) && decide (b < c) && decide (c < d) && decide (d < n) &&
  monochromatic4RawBool base a b c d && base a b == color &&
  let assigned := if color then assignedTrue else assignedFalse
  assigned.contains a && assigned.contains b &&
  assigned.contains c && assigned.contains d

private theorem checkExtensionLeaf_eq_true_iff
    {n : Nat} {base : RawColoring} {color : Bool}
    {a b c d : Nat} {assignedTrue assignedFalse : List Nat} :
    checkExtensionLeaf n base color a b c d assignedTrue assignedFalse = true ↔
      a < b ∧ b < c ∧ c < d ∧ d < n ∧
      Monochromatic4Raw base a b c d ∧ base a b = color ∧
      let assigned := if color then assignedTrue else assignedFalse
      a ∈ assigned ∧ b ∈ assigned ∧ c ∈ assigned ∧ d ∈ assigned := by
  simp [checkExtensionLeaf, monochromatic4RawBool, Monochromatic4Raw, and_assoc]

def checkExtensionCover (n : Nat) (base : RawColoring)
    (cover : ExtensionCover)
    (assignedTrue assignedFalse : List Nat := []) : Bool :=
  match cover with
  | .leaf color a b c d =>
      checkExtensionLeaf n base color a b c d assignedTrue assignedFalse
  | .branch vertex whenTrue whenFalse =>
      decide (vertex < n) && (
        checkExtensionCover n base whenTrue (vertex :: assignedTrue) assignedFalse &&
        checkExtensionCover n base whenFalse assignedTrue (vertex :: assignedFalse))

/-- Executable checker for a two-violation cover. -/
def checkExtensionCover2 (n : Nat) (base : RawColoring)
    (cover : ExtensionCover2)
    (assignedTrue assignedFalse : List Nat := []) : Bool :=
  match cover with
  | .leaf firstColor a b c d secondColor p q r s =>
      checkExtensionLeaf n base firstColor a b c d
        assignedTrue assignedFalse &&
      checkExtensionLeaf n base secondColor p q r s
        assignedTrue assignedFalse &&
      decide ([a, b, c, d] ≠ [p, q, r, s])
  | .branch vertex whenTrue whenFalse =>
      decide (vertex < n) && (
        checkExtensionCover2 n base whenTrue
          (vertex :: assignedTrue) assignedFalse &&
        checkExtensionCover2 n base whenFalse
          assignedTrue (vertex :: assignedFalse))

private def AgreesWith (apex : Nat → Bool) (color : Bool)
    (assigned : List Nat) : Prop :=
  ∀ vertex ∈ assigned, apex vertex = color

private theorem checkExtensionLeaf_sound
    {n : Nat} {base : RawColoring} {color : Bool}
    {a b c d : Nat} {assignedTrue assignedFalse : List Nat}
    (checked : checkExtensionLeaf n base color a b c d
      assignedTrue assignedFalse = true)
    {apex : Nat → Bool}
    (agreesTrue : AgreesWith apex true assignedTrue)
    (agreesFalse : AgreesWith apex false assignedFalse) :
    a < b ∧ b < c ∧ c < d ∧ d < n ∧
      ExtensionCreatesMonochromatic5 base apex a b c d := by
  have leafFacts := checkExtensionLeaf_eq_true_iff.mp checked
  cases color with
  | false =>
      rcases leafFacts with
        ⟨hab, hbc, hcd, hdn, mono, baseColor, ha, hb, hc, hd⟩
      refine ⟨hab, hbc, hcd, hdn, mono, ?_, ?_, ?_, ?_⟩
      · exact (agreesFalse a ha).trans baseColor.symm
      · exact (agreesFalse b hb).trans baseColor.symm
      · exact (agreesFalse c hc).trans baseColor.symm
      · exact (agreesFalse d hd).trans baseColor.symm
  | true =>
      simp only [↓reduceIte] at leafFacts
      rcases leafFacts with
        ⟨hab, hbc, hcd, hdn, mono, baseColor, ha, hb, hc, hd⟩
      refine ⟨hab, hbc, hcd, hdn, mono, ?_, ?_, ?_, ?_⟩
      · exact (agreesTrue a ha).trans baseColor.symm
      · exact (agreesTrue b hb).trans baseColor.symm
      · exact (agreesTrue c hc).trans baseColor.symm
      · exact (agreesTrue d hd).trans baseColor.symm

private theorem checkExtensionCover_sound_aux
    {n : Nat} {base : RawColoring} {cover : ExtensionCover}
    {assignedTrue assignedFalse : List Nat}
    (checked : checkExtensionCover n base cover assignedTrue assignedFalse = true) :
    ∀ apex : Nat → Bool,
      AgreesWith apex true assignedTrue →
      AgreesWith apex false assignedFalse →
      ¬ AttachmentAvoidsMonochromatic5 n base apex := by
  induction cover generalizing assignedTrue assignedFalse with
  | leaf color a b c d =>
      intro apex agreesTrue agreesFalse avoids
      have leafFacts := checkExtensionLeaf_eq_true_iff.mp checked
      cases color with
      | false =>
          rcases leafFacts with
            ⟨hab, hbc, hcd, hdn, mono, baseColor, ha, hb, hc, hd⟩
          apply avoids a b c d hab hbc hcd hdn
          refine ⟨mono, ?_, ?_, ?_, ?_⟩
          · exact (agreesFalse a ha).trans baseColor.symm
          · exact (agreesFalse b hb).trans baseColor.symm
          · exact (agreesFalse c hc).trans baseColor.symm
          · exact (agreesFalse d hd).trans baseColor.symm
      | true =>
          simp only [↓reduceIte] at leafFacts
          rcases leafFacts with
            ⟨hab, hbc, hcd, hdn, mono, baseColor, ha, hb, hc, hd⟩
          apply avoids a b c d hab hbc hcd hdn
          refine ⟨mono, ?_, ?_, ?_, ?_⟩
          · exact (agreesTrue a ha).trans baseColor.symm
          · exact (agreesTrue b hb).trans baseColor.symm
          · exact (agreesTrue c hc).trans baseColor.symm
          · exact (agreesTrue d hd).trans baseColor.symm
  | branch vertex whenTrue whenFalse trueSound falseSound =>
      intro apex agreesTrue agreesFalse
      simp only [checkExtensionCover, Bool.and_eq_true,
        decide_eq_true_eq] at checked
      rcases checked with ⟨_, trueChecked, falseChecked⟩
      cases apexColor : apex vertex with
      | false =>
          apply falseSound falseChecked apex agreesTrue
          intro v member
          simp only [List.mem_cons] at member
          rcases member with rfl | member
          · exact apexColor
          · exact agreesFalse v member
      | true =>
          apply trueSound trueChecked apex
          · intro v member
            simp only [List.mem_cons] at member
            rcases member with rfl | member
            · exact apexColor
            · exact agreesTrue v member
          · exact agreesFalse

/-- Generic soundness theorem for a checked one-vertex cover tree. -/
theorem checkExtensionCover_sound {n : Nat} {base : RawColoring}
    {cover : ExtensionCover}
    (checked : checkExtensionCover n base cover = true) :
    HasNoRamseyFreeOneVertexExtension n base := by
  intro apex
  exact checkExtensionCover_sound_aux checked apex
    (by simp [AgreesWith]) (by simp [AgreesWith])

private theorem checkExtensionCover2_sound_aux
    {n : Nat} {base : RawColoring} {cover : ExtensionCover2}
    {assignedTrue assignedFalse : List Nat}
    (checked : checkExtensionCover2 n base cover
      assignedTrue assignedFalse = true) :
    ∀ apex : Nat → Bool,
      AgreesWith apex true assignedTrue →
      AgreesWith apex false assignedFalse →
      ExtensionCreatesAtLeastTwoMonochromatic5 n base apex := by
  induction cover generalizing assignedTrue assignedFalse with
  | leaf firstColor a b c d secondColor p q r s =>
      intro apex agreesTrue agreesFalse
      simp only [checkExtensionCover2, Bool.and_eq_true,
        decide_eq_true_eq] at checked
      rcases checked with ⟨⟨firstChecked, secondChecked⟩, distinct⟩
      rcases checkExtensionLeaf_sound firstChecked agreesTrue agreesFalse with
        ⟨hab, hbc, hcd, hdn, firstCreates⟩
      rcases checkExtensionLeaf_sound secondChecked agreesTrue agreesFalse with
        ⟨hpq, hqr, hrs, hsn, secondCreates⟩
      exact ⟨a, b, c, d, p, q, r, s,
        hab, hbc, hcd, hdn, hpq, hqr, hrs, hsn,
        distinct, firstCreates, secondCreates⟩
  | branch vertex whenTrue whenFalse trueSound falseSound =>
      intro apex agreesTrue agreesFalse
      simp only [checkExtensionCover2, Bool.and_eq_true,
        decide_eq_true_eq] at checked
      rcases checked with ⟨_, trueChecked, falseChecked⟩
      cases apexColor : apex vertex with
      | false =>
          apply falseSound falseChecked apex agreesTrue
          intro v member
          simp only [List.mem_cons] at member
          rcases member with rfl | member
          · exact apexColor
          · exact agreesFalse v member
      | true =>
          apply trueSound trueChecked apex
          · intro v member
            simp only [List.mem_cons] at member
            rcases member with rfl | member
            · exact apexColor
            · exact agreesTrue v member
          · exact agreesFalse

/-- Generic soundness theorem for a checked two-violation cover tree. -/
theorem checkExtensionCover2_sound {n : Nat} {base : RawColoring}
    {cover : ExtensionCover2}
    (checked : checkExtensionCover2 n base cover = true) :
    EveryExtensionCreatesAtLeastTwoMonochromatic5 n base := by
  intro apex
  exact checkExtensionCover2_sound_aux checked apex
    (by simp [AgreesWith]) (by simp [AgreesWith])

theorem atLeastTwoExtensions_imply_noRamseyFreeExtension
    {n : Nat} {base : RawColoring}
    (atLeastTwo : EveryExtensionCreatesAtLeastTwoMonochromatic5 n base) :
    HasNoRamseyFreeOneVertexExtension n base := by
  intro apex avoids
  rcases atLeastTwo apex with
    ⟨a, b, c, d, _, _, _, _, hab, hbc, hcd, hdn, _, _, _, _, _,
      firstCreates, _⟩
  exact avoids a b c d hab hbc hcd hdn firstCreates

/-- Swap the two edge colours of a raw colouring. -/
def complementRawColoring (base : RawColoring) : RawColoring :=
  fun u v => !(base u v)

private theorem extensionCreatesMonochromatic5_complement_iff
    (base : RawColoring) (apex : Nat → Bool) (a b c d : Nat) :
    ExtensionCreatesMonochromatic5 (complementRawColoring base)
        (fun vertex => !(apex vertex)) a b c d ↔
      ExtensionCreatesMonochromatic5 base apex a b c d := by
  simp [ExtensionCreatesMonochromatic5, Monochromatic4Raw,
    complementRawColoring]

/-- Nonextendability is invariant under swapping the two colours. -/
theorem hasNoRamseyFreeOneVertexExtension_complement
    {n : Nat} {base : RawColoring}
    (noExtension : HasNoRamseyFreeOneVertexExtension n base) :
    HasNoRamseyFreeOneVertexExtension n (complementRawColoring base) := by
  intro apex complementAvoids
  apply noExtension (fun vertex => !(apex vertex))
  intro a b c d hab hbc hcd hdn createsBase
  apply complementAvoids a b c d hab hbc hcd hdn
  have := (extensionCreatesMonochromatic5_complement_iff
    base (fun vertex => !(apex vertex)) a b c d).mpr createsBase
  simpa [complementRawColoring] using this

/-- The two-violation extension property is invariant under swapping the two
edge colours. -/
theorem everyExtensionCreatesAtLeastTwoMonochromatic5_complement
    {n : Nat} {base : RawColoring}
    (atLeastTwo : EveryExtensionCreatesAtLeastTwoMonochromatic5 n base) :
    EveryExtensionCreatesAtLeastTwoMonochromatic5 n
      (complementRawColoring base) := by
  intro apex
  rcases atLeastTwo (fun vertex => !(apex vertex)) with
    ⟨a, b, c, d, p, q, r, s,
      hab, hbc, hcd, hdn, hpq, hqr, hrs, hsn,
      distinct, firstCreates, secondCreates⟩
  refine ⟨a, b, c, d, p, q, r, s,
    hab, hbc, hcd, hdn, hpq, hqr, hrs, hsn, distinct, ?_, ?_⟩
  · have := (extensionCreatesMonochromatic5_complement_iff
      base (fun vertex => !(apex vertex)) a b c d).mpr firstCreates
    simpa [complementRawColoring] using this
  · have := (extensionCreatesMonochromatic5_complement_iff
      base (fun vertex => !(apex vertex)) p q r s).mpr secondCreates
    simpa [complementRawColoring] using this

/-- A raw labelled graph bundled with a checked proof that no apex attachment
can extend it. -/
structure CertifiedNonextendableGraph (n : Nat) where
  base : RawColoring
  noExtension : HasNoRamseyFreeOneVertexExtension n base

/-- Colour duality turns a certified graph into another certified graph. -/
def CertifiedNonextendableGraph.complement {n : Nat}
    (graph : CertifiedNonextendableGraph n) : CertifiedNonextendableGraph n where
  base := complementRawColoring graph.base
  noExtension := hasNoRamseyFreeOneVertexExtension_complement graph.noExtension

/-- A labelled graph bundled with a proof that every apex attachment creates
at least two distinct monochromatic five-sets. -/
structure CertifiedTwoViolationGraph (n : Nat) where
  base : RawColoring
  atLeastTwo : EveryExtensionCreatesAtLeastTwoMonochromatic5 n base

def CertifiedTwoViolationGraph.noExtension {n : Nat}
    (graph : CertifiedTwoViolationGraph n) :
    HasNoRamseyFreeOneVertexExtension n graph.base :=
  atLeastTwoExtensions_imply_noRamseyFreeExtension graph.atLeastTwo

def CertifiedTwoViolationGraph.complement {n : Nat}
    (graph : CertifiedTwoViolationGraph n) : CertifiedTwoViolationGraph n where
  base := complementRawColoring graph.base
  atLeastTwo :=
    everyExtensionCreatesAtLeastTwoMonochromatic5_complement graph.atLeastTwo

end Ramsey55
