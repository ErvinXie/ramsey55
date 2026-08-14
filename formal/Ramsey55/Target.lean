import Ramsey55.LowerBound42
import Ramsey55.Reduction

namespace Ramsey55

/-- The exact `R(5,5) = 43` target, stated without assuming monotonicity facts
about other orders: 42 vertices admit a Ramsey-free colouring, while 43 do
not. -/
def Ramsey55Is43 : Prop :=
  ¬ ForcesMonochromatic5 42 ∧ ForcesMonochromatic5 43

/-- The exact target follows once all Ramsey-free 42-vertex colourings have
been proved nonextendable.  The first conjunct is the checked lower-bound
witness; the hypothesis is the remaining classification obligation. -/
theorem ramsey55_is_43_of_all_42_nonextendable
    (allNonextendable :
      ∀ base : Coloring 42,
        IsSimpleColoring base → IsRamseyFree55 base →
        HasNoRamseyFreeOneVertexExtension 42 (coloringToRaw base)) :
    Ramsey55Is43 := by
  exact ⟨not_forcesMonochromatic5_42,
    forcesMonochromatic5_43_of_all_42_nonextendable allNonextendable⟩

theorem ramsey55_is_43_of_all_42_atLeastTwo
    (allAtLeastTwo :
      ∀ base : Coloring 42,
        IsSimpleColoring base → IsRamseyFree55 base →
        EveryExtensionCreatesAtLeastTwoMonochromatic5 42
          (coloringToRaw base)) :
    Ramsey55Is43 := by
  exact ⟨not_forcesMonochromatic5_42,
    forcesMonochromatic5_43_of_all_42_atLeastTwo allAtLeastTwo⟩

#print axioms ramsey55_is_43_of_all_42_nonextendable
#print axioms ramsey55_is_43_of_all_42_atLeastTwo

end Ramsey55
