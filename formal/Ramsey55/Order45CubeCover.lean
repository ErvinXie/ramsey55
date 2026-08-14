import Ramsey55.CubeCover
import Ramsey55.Order45

namespace Ramsey55

/-- Natural numbers in the closed interval `[lower, upper]`. The caller-side
proofs below use only nonempty intervals. -/
def inclusiveNatRange (lower upper : Nat) : List Nat :=
  List.range' lower (upper + 1 - lower)

theorem mem_inclusiveNatRange_iff {lower upper value : Nat}
    (nonempty : lower ≤ upper) :
    value ∈ inclusiveNatRange lower upper ↔ lower ≤ value ∧ value ≤ upper := by
  simp only [inclusiveNatRange, List.mem_range']
  constructor
  · rintro ⟨offset, offsetBound, rfl⟩
    omega
  · rintro ⟨lowerBound, upperBound⟩
    refine ⟨value - lower, ?_, ?_⟩ <;> omega

/-- The exact `(e(H), e(J))` pairs emitted by the edge-stratum generator:
lexicographic closed ranges, filtered by the local-excess lower bound. -/
def admissibleEdgePairs
    (lowerH upperH lowerJ upperJ threshold : Nat) : List (Nat × Nat) :=
  ((inclusiveNatRange lowerH upperH).flatMap fun edgesH =>
    (inclusiveNatRange lowerJ upperJ).map fun edgesJ => (edgesH, edgesJ)).filter
      fun pair => decide (threshold ≤ pair.1 + pair.2)

theorem mem_admissibleEdgePairs_iff
    {lowerH upperH lowerJ upperJ threshold edgesH edgesJ : Nat}
    (hNonempty : lowerH ≤ upperH) (jNonempty : lowerJ ≤ upperJ) :
    (edgesH, edgesJ) ∈
        admissibleEdgePairs lowerH upperH lowerJ upperJ threshold ↔
      lowerH ≤ edgesH ∧ edgesH ≤ upperH ∧
      lowerJ ≤ edgesJ ∧ edgesJ ≤ upperJ ∧
      threshold ≤ edgesH + edgesJ := by
  simp only [admissibleEdgePairs, List.mem_filter, decide_eq_true_eq,
    List.mem_flatMap, List.mem_map,
    mem_inclusiveNatRange_iff hNonempty,
    mem_inclusiveNatRange_iff jNonempty]
  constructor
  · rintro ⟨⟨sourceH, sourceHBounds,
      ⟨sourceJ, sourceJMembership, pairEquality⟩⟩, thresholdBound⟩
    cases pairEquality
    exact ⟨sourceHBounds.1, sourceHBounds.2,
      sourceJMembership.1, sourceJMembership.2, thresholdBound⟩
  · rintro ⟨hLower, hUpper, jLower, jUpper, thresholdBound⟩
    refine ⟨⟨edgesH, ⟨hLower, hUpper⟩, edgesJ, ?_, rfl⟩, thresholdBound⟩
    exact ⟨jLower, jUpper⟩

def order45Degree20EdgePairs : List (Nat × Nat) :=
  admissibleEdgePairs 68 100 116 132 226

def order45Degree21EdgePairs : List (Nat × Nat) :=
  admissibleEdgePairs 77 107 101 122 222

def order45Degree22EdgePairs : List (Nat × Nat) :=
  admissibleEdgePairs 88 114 88 114 220

/-- Abstract semantic contract for the observable outputs of an at-least
counter: output `k` is true exactly when the represented count is at least
`k + 1`. The next formal bridge must derive this contract from the concrete
sequential-counter CNF clauses. -/
def ExactAtLeastCounterOutputs {variables : Nat}
    (assignment : CnfAssignment variables)
    (outputs : Nat → CnfLiteral variables) (count : Nat) : Prop :=
  ∀ k, (outputs k).Holds assignment ↔ k + 1 ≤ count

/-- The four-literal exact-count cube emitted for one `(e(H), e(J))` pair. -/
def exactEdgePairCube {variables : Nat}
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (pair : Nat × Nat) : CnfCube variables :=
  [hOutputs (pair.1 - 1), (hOutputs pair.1).negate,
    jOutputs (pair.2 - 1), (jOutputs pair.2).negate]

theorem satisfies_exactEdgePairCube {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat) (hPositive : 0 < edgesH) (jPositive : 0 < edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs edgesJ) :
    SatisfiesCnfCube assignment
      (exactEdgePairCube hOutputs jOutputs (edgesH, edgesJ)) := by
  intro literal membership
  simp only [exactEdgePairCube, List.mem_cons, List.not_mem_nil,
    or_false] at membership
  rcases membership with rfl | rfl | rfl | rfl
  · exact (hExact (edgesH - 1)).mpr (by omega)
  · rw [CnfLiteral.negate_holds_iff_not_holds]
    intro holds
    have tooMany := (hExact edgesH).mp holds
    omega
  · exact (jExact (edgesJ - 1)).mpr (by omega)
  · rw [CnfLiteral.negate_holds_iff_not_holds]
    intro holds
    have tooMany := (jExact edgesJ).mp holds
    omega

theorem exists_satisfied_exactEdgePairCube {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (pairs : List (Nat × Nat)) (edgesH edgesJ : Nat)
    (pairMember : (edgesH, edgesJ) ∈ pairs)
    (hPositive : 0 < edgesH) (jPositive : 0 < edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs edgesJ) :
    ∃ cube ∈ pairs.map (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  refine ⟨exactEdgePairCube hOutputs jOutputs (edgesH, edgesJ), ?_, ?_⟩
  · exact List.mem_map.mpr ⟨(edgesH, edgesJ), pairMember, rfl⟩
  · exact satisfies_exactEdgePairCube assignment hOutputs jOutputs
      edgesH edgesJ hPositive jPositive hExact jExact

set_option maxRecDepth 100000 in
theorem order45EdgePairCounts :
    order45Degree20EdgePairs.length = 28 ∧
    order45Degree21EdgePairs.length = 36 ∧
    order45Degree22EdgePairs.length = 45 := by
  decide

theorem order45Degree20EdgePairs_cover (edgesH edgesJ : Nat)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ) :
    (edgesH, edgesJ) ∈ order45Degree20EdgePairs := by
  rw [order45Degree20EdgePairs, mem_admissibleEdgePairs_iff (by omega) (by omega)]
  exact ⟨hLower, hUpper, jLower, jUpper, dense⟩

theorem order45Degree21EdgePairs_cover (edgesH edgesJ : Nat)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ) :
    (edgesH, edgesJ) ∈ order45Degree21EdgePairs := by
  rw [order45Degree21EdgePairs, mem_admissibleEdgePairs_iff (by omega) (by omega)]
  exact ⟨hLower, hUpper, jLower, jUpper, dense⟩

theorem order45Degree22EdgePairs_cover (edgesH edgesJ : Nat)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ) :
    (edgesH, edgesJ) ∈ order45Degree22EdgePairs := by
  rw [order45Degree22EdgePairs, mem_admissibleEdgePairs_iff (by omega) (by omega)]
  exact ⟨hLower, hUpper, jLower, jUpper, dense⟩

theorem order45Degree20CounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat)
    (hLower : 68 ≤ edgesH) (hUpper : edgesH ≤ 100)
    (jLower : 116 ≤ edgesJ) (jUpper : edgesJ ≤ 132)
    (dense : 226 ≤ edgesH + edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs edgesJ) :
    ∃ cube ∈ order45Degree20EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree20EdgePairs edgesH edgesJ
    (order45Degree20EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) hExact jExact

theorem order45Degree21CounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs edgesJ) :
    ∃ cube ∈ order45Degree21EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree21EdgePairs edgesH edgesJ
    (order45Degree21EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) hExact jExact

theorem order45Degree22CounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs edgesJ) :
    ∃ cube ∈ order45Degree22EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree22EdgePairs edgesH edgesJ
    (order45Degree22EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) hExact jExact

#print axioms mem_admissibleEdgePairs_iff
#print axioms order45EdgePairCounts
#print axioms order45Degree20EdgePairs_cover
#print axioms order45Degree21EdgePairs_cover
#print axioms order45Degree22EdgePairs_cover
#print axioms satisfies_exactEdgePairCube
#print axioms order45Degree20CounterCubes_cover
#print axioms order45Degree21CounterCubes_cover
#print axioms order45Degree22CounterCubes_cover

end Ramsey55
