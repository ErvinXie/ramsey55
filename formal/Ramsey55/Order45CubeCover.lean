import Ramsey55.CnfCardinality
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

/-- The four-literal exact-count cube emitted for one `(e(H), e(J))` pair. -/
def exactEdgePairCube {variables : Nat}
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (pair : Nat × Nat) : CnfCube variables :=
  [hOutputs (pair.1 - 1), (hOutputs pair.1).negate,
    jOutputs (pair.2 - 1), (jOutputs pair.2).negate]

theorem satisfies_exactEdgePairCube {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (hWidth jWidth edgesH edgesJ : Nat)
    (hPositive : 0 < edgesH) (jPositive : 0 < edgesJ)
    (hInside : edgesH < hWidth) (jInside : edgesJ < jWidth)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs hWidth edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs jWidth edgesJ) :
    SatisfiesCnfCube assignment
      (exactEdgePairCube hOutputs jOutputs (edgesH, edgesJ)) := by
  intro literal membership
  simp only [exactEdgePairCube, List.mem_cons, List.not_mem_nil,
    or_false] at membership
  rcases membership with rfl | rfl | rfl | rfl
  · exact (hExact (edgesH - 1) (by omega)).mpr (by omega)
  · rw [CnfLiteral.negate_holds_iff_not_holds]
    intro holds
    have tooMany := (hExact edgesH hInside).mp holds
    omega
  · exact (jExact (edgesJ - 1) (by omega)).mpr (by omega)
  · rw [CnfLiteral.negate_holds_iff_not_holds]
    intro holds
    have tooMany := (jExact edgesJ jInside).mp holds
    omega

theorem exists_satisfied_exactEdgePairCube {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (pairs : List (Nat × Nat)) (hWidth jWidth edgesH edgesJ : Nat)
    (pairMember : (edgesH, edgesJ) ∈ pairs)
    (hPositive : 0 < edgesH) (jPositive : 0 < edgesJ)
    (hInside : edgesH < hWidth) (jInside : edgesJ < jWidth)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs hWidth edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs jWidth edgesJ) :
    ∃ cube ∈ pairs.map (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  refine ⟨exactEdgePairCube hOutputs jOutputs (edgesH, edgesJ), ?_, ?_⟩
  · exact List.mem_map.mpr ⟨(edgesH, edgesJ), pairMember, rfl⟩
  · exact satisfies_exactEdgePairCube assignment hOutputs jOutputs
      hWidth jWidth edgesH edgesJ hPositive jPositive hInside jInside
      hExact jExact

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
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs 101 edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs 133 edgesJ) :
    ∃ cube ∈ order45Degree20EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree20EdgePairs 101 133 edgesH edgesJ
    (order45Degree20EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) (by omega) (by omega) hExact jExact

theorem order45Degree21CounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat)
    (hLower : 77 ≤ edgesH) (hUpper : edgesH ≤ 107)
    (jLower : 101 ≤ edgesJ) (jUpper : edgesJ ≤ 122)
    (dense : 222 ≤ edgesH + edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs 108 edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs 123 edgesJ) :
    ∃ cube ∈ order45Degree21EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree21EdgePairs 108 123 edgesH edgesJ
    (order45Degree21EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) (by omega) (by omega) hExact jExact

theorem order45Degree22CounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hOutputs jOutputs : Nat → CnfLiteral variables)
    (edgesH edgesJ : Nat)
    (hLower : 88 ≤ edgesH) (hUpper : edgesH ≤ 114)
    (jLower : 88 ≤ edgesJ) (jUpper : edgesJ ≤ 114)
    (dense : 220 ≤ edgesH + edgesJ)
    (hExact : ExactAtLeastCounterOutputs assignment hOutputs 115 edgesH)
    (jExact : ExactAtLeastCounterOutputs assignment jOutputs 115 edgesJ) :
    ∃ cube ∈ order45Degree22EdgePairs.map
        (exactEdgePairCube hOutputs jOutputs),
      SatisfiesCnfCube assignment cube := by
  exact exists_satisfied_exactEdgePairCube assignment hOutputs jOutputs
    order45Degree22EdgePairs 115 115 edgesH edgesJ
    (order45Degree22EdgePairs_cover edgesH edgesJ
      hLower hUpper jLower jUpper dense)
    (by omega) (by omega) (by omega) (by omega) hExact jExact

theorem order45Degree20SequentialCounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hCells : SatisfiesSequentialCounterCells assignment hInput hState 190 101)
    (jCells : SatisfiesSequentialCounterCells assignment jInput jState 276 133)
    (hLower : 68 ≤ sequentialCounterInputCount assignment hInput 190)
    (hUpper : sequentialCounterInputCount assignment hInput 190 ≤ 100)
    (jLower : 116 ≤ sequentialCounterInputCount assignment jInput 276)
    (jUpper : sequentialCounterInputCount assignment jInput 276 ≤ 132)
    (dense : 226 ≤ sequentialCounterInputCount assignment hInput 190 +
      sequentialCounterInputCount assignment jInput 276) :
    ∃ cube ∈ order45Degree20EdgePairs.map
        (exactEdgePairCube (hState (190 - 1)) (jState (276 - 1))),
      SatisfiesCnfCube assignment cube := by
  have hExact := satisfiesSequentialCounterCells_outputs_exact assignment
    hInput hState 190 101 (by omega) (by omega) hCells
  have jExact := satisfiesSequentialCounterCells_outputs_exact assignment
    jInput jState 276 133 (by omega) (by omega) jCells
  exact order45Degree20CounterCubes_cover assignment
    (hState (190 - 1)) (jState (276 - 1))
    (sequentialCounterInputCount assignment hInput 190)
    (sequentialCounterInputCount assignment jInput 276)
    hLower hUpper jLower jUpper dense hExact jExact

theorem order45Degree21SequentialCounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hCells : SatisfiesSequentialCounterCells assignment hInput hState 210 108)
    (jCells : SatisfiesSequentialCounterCells assignment jInput jState 253 123)
    (hLower : 77 ≤ sequentialCounterInputCount assignment hInput 210)
    (hUpper : sequentialCounterInputCount assignment hInput 210 ≤ 107)
    (jLower : 101 ≤ sequentialCounterInputCount assignment jInput 253)
    (jUpper : sequentialCounterInputCount assignment jInput 253 ≤ 122)
    (dense : 222 ≤ sequentialCounterInputCount assignment hInput 210 +
      sequentialCounterInputCount assignment jInput 253) :
    ∃ cube ∈ order45Degree21EdgePairs.map
        (exactEdgePairCube (hState (210 - 1)) (jState (253 - 1))),
      SatisfiesCnfCube assignment cube := by
  have hExact := satisfiesSequentialCounterCells_outputs_exact assignment
    hInput hState 210 108 (by omega) (by omega) hCells
  have jExact := satisfiesSequentialCounterCells_outputs_exact assignment
    jInput jState 253 123 (by omega) (by omega) jCells
  exact order45Degree21CounterCubes_cover assignment
    (hState (210 - 1)) (jState (253 - 1))
    (sequentialCounterInputCount assignment hInput 210)
    (sequentialCounterInputCount assignment jInput 253)
    hLower hUpper jLower jUpper dense hExact jExact

theorem order45Degree22SequentialCounterCubes_cover {variables : Nat}
    (assignment : CnfAssignment variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hCells : SatisfiesSequentialCounterCells assignment hInput hState 231 115)
    (jCells : SatisfiesSequentialCounterCells assignment jInput jState 231 115)
    (hLower : 88 ≤ sequentialCounterInputCount assignment hInput 231)
    (hUpper : sequentialCounterInputCount assignment hInput 231 ≤ 114)
    (jLower : 88 ≤ sequentialCounterInputCount assignment jInput 231)
    (jUpper : sequentialCounterInputCount assignment jInput 231 ≤ 114)
    (dense : 220 ≤ sequentialCounterInputCount assignment hInput 231 +
      sequentialCounterInputCount assignment jInput 231) :
    ∃ cube ∈ order45Degree22EdgePairs.map
        (exactEdgePairCube (hState (231 - 1)) (jState (231 - 1))),
      SatisfiesCnfCube assignment cube := by
  have hExact := satisfiesSequentialCounterCells_outputs_exact assignment
    hInput hState 231 115 (by omega) (by omega) hCells
  have jExact := satisfiesSequentialCounterCells_outputs_exact assignment
    jInput jState 231 115 (by omega) (by omega) jCells
  exact order45Degree22CounterCubes_cover assignment
    (hState (231 - 1)) (jState (231 - 1))
    (sequentialCounterInputCount assignment hInput 231)
    (sequentialCounterInputCount assignment jInput 231)
    hLower hUpper jLower jUpper dense hExact jExact

/-- If a mother formula contains both emitted counter streams and entails the
four catalog bounds plus the excess inequality, its concrete degree-20 cube
family covers every satisfying assignment. -/
theorem order45Degree20CounterSubformulas_cover {variables : Nat}
    (formula : CnfFormula variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hIncluded : ∀ clause ∈
      sequentialCounterCellFormula hInput hState 190 101, clause ∈ formula)
    (jIncluded : ∀ clause ∈
      sequentialCounterCellFormula jInput jState 276 133, clause ∈ formula)
    (bounds : ∀ assignment, SatisfiesCnfFormula assignment formula →
      68 ≤ sequentialCounterInputCount assignment hInput 190 ∧
      sequentialCounterInputCount assignment hInput 190 ≤ 100 ∧
      116 ≤ sequentialCounterInputCount assignment jInput 276 ∧
      sequentialCounterInputCount assignment jInput 276 ≤ 132 ∧
      226 ≤ sequentialCounterInputCount assignment hInput 190 +
        sequentialCounterInputCount assignment jInput 276) :
    CnfCubeFamilyCoversFormula formula
      (order45Degree20EdgePairs.map
        (exactEdgePairCube (hState (190 - 1)) (jState (276 - 1)))) := by
  intro assignment formulaSatisfied
  have hCells := satisfiesSequentialCounterSubformula_cells assignment formula
    hInput hState 190 101 (by omega) (by omega) formulaSatisfied hIncluded
  have jCells := satisfiesSequentialCounterSubformula_cells assignment formula
    jInput jState 276 133 (by omega) (by omega) formulaSatisfied jIncluded
  rcases bounds assignment formulaSatisfied with
    ⟨hLower, hUpper, jLower, jUpper, dense⟩
  exact order45Degree20SequentialCounterCubes_cover assignment
    hInput jInput hState jState hCells jCells
    hLower hUpper jLower jUpper dense

theorem order45Degree21CounterSubformulas_cover {variables : Nat}
    (formula : CnfFormula variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hIncluded : ∀ clause ∈
      sequentialCounterCellFormula hInput hState 210 108, clause ∈ formula)
    (jIncluded : ∀ clause ∈
      sequentialCounterCellFormula jInput jState 253 123, clause ∈ formula)
    (bounds : ∀ assignment, SatisfiesCnfFormula assignment formula →
      77 ≤ sequentialCounterInputCount assignment hInput 210 ∧
      sequentialCounterInputCount assignment hInput 210 ≤ 107 ∧
      101 ≤ sequentialCounterInputCount assignment jInput 253 ∧
      sequentialCounterInputCount assignment jInput 253 ≤ 122 ∧
      222 ≤ sequentialCounterInputCount assignment hInput 210 +
        sequentialCounterInputCount assignment jInput 253) :
    CnfCubeFamilyCoversFormula formula
      (order45Degree21EdgePairs.map
        (exactEdgePairCube (hState (210 - 1)) (jState (253 - 1)))) := by
  intro assignment formulaSatisfied
  have hCells := satisfiesSequentialCounterSubformula_cells assignment formula
    hInput hState 210 108 (by omega) (by omega) formulaSatisfied hIncluded
  have jCells := satisfiesSequentialCounterSubformula_cells assignment formula
    jInput jState 253 123 (by omega) (by omega) formulaSatisfied jIncluded
  rcases bounds assignment formulaSatisfied with
    ⟨hLower, hUpper, jLower, jUpper, dense⟩
  exact order45Degree21SequentialCounterCubes_cover assignment
    hInput jInput hState jState hCells jCells
    hLower hUpper jLower jUpper dense

theorem order45Degree22CounterSubformulas_cover {variables : Nat}
    (formula : CnfFormula variables)
    (hInput jInput : Nat → CnfLiteral variables)
    (hState jState : Nat → Nat → CnfLiteral variables)
    (hIncluded : ∀ clause ∈
      sequentialCounterCellFormula hInput hState 231 115, clause ∈ formula)
    (jIncluded : ∀ clause ∈
      sequentialCounterCellFormula jInput jState 231 115, clause ∈ formula)
    (bounds : ∀ assignment, SatisfiesCnfFormula assignment formula →
      88 ≤ sequentialCounterInputCount assignment hInput 231 ∧
      sequentialCounterInputCount assignment hInput 231 ≤ 114 ∧
      88 ≤ sequentialCounterInputCount assignment jInput 231 ∧
      sequentialCounterInputCount assignment jInput 231 ≤ 114 ∧
      220 ≤ sequentialCounterInputCount assignment hInput 231 +
        sequentialCounterInputCount assignment jInput 231) :
    CnfCubeFamilyCoversFormula formula
      (order45Degree22EdgePairs.map
        (exactEdgePairCube (hState (231 - 1)) (jState (231 - 1)))) := by
  intro assignment formulaSatisfied
  have hCells := satisfiesSequentialCounterSubformula_cells assignment formula
    hInput hState 231 115 (by omega) (by omega) formulaSatisfied hIncluded
  have jCells := satisfiesSequentialCounterSubformula_cells assignment formula
    jInput jState 231 115 (by omega) (by omega) formulaSatisfied jIncluded
  rcases bounds assignment formulaSatisfied with
    ⟨hLower, hUpper, jLower, jUpper, dense⟩
  exact order45Degree22SequentialCounterCubes_cover assignment
    hInput jInput hState jState hCells jCells
    hLower hUpper jLower jUpper dense

#print axioms mem_admissibleEdgePairs_iff
#print axioms order45EdgePairCounts
#print axioms order45Degree20EdgePairs_cover
#print axioms order45Degree21EdgePairs_cover
#print axioms order45Degree22EdgePairs_cover
#print axioms satisfies_exactEdgePairCube
#print axioms order45Degree20CounterCubes_cover
#print axioms order45Degree21CounterCubes_cover
#print axioms order45Degree22CounterCubes_cover
#print axioms order45Degree20SequentialCounterCubes_cover
#print axioms order45Degree21SequentialCounterCubes_cover
#print axioms order45Degree22SequentialCounterCubes_cover
#print axioms order45Degree20CounterSubformulas_cover
#print axioms order45Degree21CounterSubformulas_cover
#print axioms order45Degree22CounterSubformulas_cover

end Ramsey55
