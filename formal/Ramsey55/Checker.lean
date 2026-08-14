import Init.Data.List.Lemmas
import Init.Data.List.Nat.Range
import Lean.Elab.Tactic.Omega
import Ramsey55.Definitions

namespace Ramsey55

/-- Natural-number view of a colouring, used by the executable certificate
checker. Only values below the supplied order are inspected. -/
abbrev RawColoring := Nat → Nat → Bool

/-- Boolean version of the ten-edge monochromatic predicate. -/
def monochromatic5Bool (color : RawColoring)
    (a b c d e : Nat) : Bool :=
  color a c == color a b &&
  color a d == color a b &&
  color a e == color a b &&
  color b c == color a b &&
  color b d == color a b &&
  color b e == color a b &&
  color c d == color a b &&
  color c e == color a b &&
  color d e == color a b

/-- The natural numbers strictly above start and below n. -/
def successors (n start : Nat) : List Nat :=
  List.range' (start + 1) (n - (start + 1))

theorem mem_successors {n start value : Nat} :
    value ∈ successors n start ↔ start < value ∧ value < n := by
  simp [successors, List.mem_range'_1]
  omega

/-- Check every increasing five-tuple whose first vertex is a. -/
def checkRamseyFree55At (n : Nat) (color : RawColoring) (a : Nat) : Bool :=
  (successors n a).all fun b =>
    (successors n b).all fun c =>
      (successors n c).all fun d =>
        (successors n d).all fun e =>
          !monochromatic5Bool color a b c d e

/-- Check a consecutive range of possible first vertices. Splitting a large
certificate into these ranges keeps kernel-reduction memory bounded. -/
def checkRamseyFree55Range (n : Nat) (color : RawColoring)
    (start count : Nat) : Bool :=
  (List.range' start count).all (checkRamseyFree55At n color)

/-- Exhaustively check the C(n,5) increasing five-tuples. -/
def checkRamseyFree55 (n : Nat) (color : RawColoring) : Bool :=
  checkRamseyFree55Range n color 0 n

theorem monochromatic5Bool_eq_true_iff {n : Nat} (color : RawColoring)
    (a b c d e : Fin n) :
    monochromatic5Bool color a.val b.val c.val d.val e.val = true ↔
      Monochromatic5
        (fun u v : Fin n => color u.val v.val)
        a b c d e := by
  simp [monochromatic5Bool, Monochromatic5, and_assoc]

/-- Extract the check for one first vertex from a checked range. -/
theorem checkRamseyFree55Range_at {n start count a : Nat}
    {color : RawColoring}
    (checked : checkRamseyFree55Range n color start count = true)
    (member : a ∈ List.range' start count) :
    checkRamseyFree55At n color a = true := by
  exact List.all_eq_true.mp checked a member

/-- Soundness of one first-vertex block. This theorem is generic; witness data
do not occur in its proof. -/
theorem checkRamseyFree55At_sound {n : Nat} {color : RawColoring}
    (a : Fin n)
    (checked : checkRamseyFree55At n color a.val = true) :
    ∀ b c d e : Fin n,
      a.val < b.val →
      b.val < c.val →
      c.val < d.val →
      d.val < e.val →
      ¬ Monochromatic5
        (fun u v : Fin n => color u.val v.val)
        a b c d e := by
  intro b c d e hab hbc hcd hde
  simp only [checkRamseyFree55At, List.all_eq_true] at checked
  have checkedB := checked b.val (mem_successors.mpr ⟨hab, b.isLt⟩)
  have checkedC := checkedB c.val (mem_successors.mpr ⟨hbc, c.isLt⟩)
  have checkedD := checkedC d.val (mem_successors.mpr ⟨hcd, d.isLt⟩)
  have checkedE := checkedD e.val (mem_successors.mpr ⟨hde, e.isLt⟩)
  intro mono
  have monoTrue :
      monochromatic5Bool color a.val b.val c.val d.val e.val = true :=
    (monochromatic5Bool_eq_true_iff color a b c d e).mpr mono
  simp [monoTrue] at checkedE

/-- Soundness of the complete finite checker. -/
theorem checkRamseyFree55_sound {n : Nat} {color : RawColoring}
    (checked : checkRamseyFree55 n color = true) :
    IsRamseyFree55 (fun u v : Fin n => color u.val v.val) := by
  intro a
  apply checkRamseyFree55At_sound a
  apply checkRamseyFree55Range_at checked
  simp [List.mem_range'_1]

end Ramsey55
