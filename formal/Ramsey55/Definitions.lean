namespace Ramsey55

/-- A Boolean two-colouring of the pairs of n labelled vertices. -/
abbrev Coloring (n : Nat) := Fin n → Fin n → Bool

/-- The colouring represents an undirected complete graph: diagonal values are
ignored as edges and every off-diagonal pair has the same colour in both
orders. -/
def IsSimpleColoring {n : Nat} (color : Coloring n) : Prop :=
  (∀ v, color v v = false) ∧
  (∀ u v, color u v = color v u)

/-- The ten pairs on five vertices all have the same colour. -/
def Monochromatic5 {n : Nat} (color : Coloring n)
    (a b c d e : Fin n) : Prop :=
  color a c = color a b ∧
  color a d = color a b ∧
  color a e = color a b ∧
  color b c = color a b ∧
  color b d = color a b ∧
  color b e = color a b ∧
  color c d = color a b ∧
  color c e = color a b ∧
  color d e = color a b

/-- No increasing five-tuple is monochromatic. Every five-element vertex set
has exactly one increasing enumeration, so this is the finite Ramsey-free
predicate without quotienting by permutations. -/
def IsRamseyFree55 {n : Nat} (color : Coloring n) : Prop :=
  ∀ a b c d e : Fin n,
    a.val < b.val →
    b.val < c.val →
    c.val < d.val →
    d.val < e.val →
    ¬ Monochromatic5 color a b c d e

/-- Every valid two-colouring of K_n contains a monochromatic K_5. -/
def ForcesMonochromatic5 (n : Nat) : Prop :=
  ∀ color : Coloring n, IsSimpleColoring color → ¬ IsRamseyFree55 color

end Ramsey55
