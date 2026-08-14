import Ramsey55.Order45CubeCover

namespace Ramsey55

/-- Number of row-major sequential-counter cells before zero-based `row`. -/
def counterCellsBefore (width : Nat) : Nat → Nat
  | 0 => 0
  | row + 1 => counterCellsBefore width row + min (row + 1) width

/-- One-based DIMACS variable allocated at a counter cell. `base` is the
largest variable before the counter, while row and column are zero-based. -/
def counterStateDimacsVariable
    (base width row column : Nat) : Nat :=
  base + counterCellsBefore width row + column + 1

def counterOutputDimacsVariable
    (base rows width thresholdIndex : Nat) : Nat :=
  counterStateDimacsVariable base width (rows - 1) thresholdIndex

/-- Embed one-based DIMACS identifiers directly into a finite assignment by
reserving index zero as an unused dummy. For every generated formula the
maximum identifier is strictly below the `Fin (maximum + 1)` modulus. -/
def dimacsLiteral (maximum identifier : Nat) (positive : Bool) :
    CnfLiteral (maximum + 1) :=
  { index := Fin.ofNat (maximum + 1) identifier, positive := positive }

def counterStateDimacsLiteral
    (maximum base width row column : Nat) : CnfLiteral (maximum + 1) :=
  dimacsLiteral maximum
    (counterStateDimacsVariable base width row column) true

/-- Pairs in the exact order produced by
`itertools.combinations(range(start, start + count), 2)`. -/
def orderedPairsFrom (start count : Nat) : List (Nat × Nat) :=
  (List.range count).flatMap fun leftOffset =>
    (List.range (count - leftOffset - 1)).map fun rightOffset =>
      (start + leftOffset, start + leftOffset + rightOffset + 1)

def orderedEdgeDimacsVariable (pair : Nat × Nat) : Nat :=
  pair.2 * (pair.2 - 1) / 2 + pair.1 + 1

def order45HInputIdentifiers (degree : Nat) : List Nat :=
  (orderedPairsFrom 1 degree).map orderedEdgeDimacsVariable

def order45JInputIdentifiers (degree : Nat) : List Nat :=
  (orderedPairsFrom (degree + 1) (44 - degree)).map
    orderedEdgeDimacsVariable

def counterInputDimacsLiteral (maximum : Nat) (identifiers : List Nat)
    (positive : Bool) (row : Nat) : CnfLiteral (maximum + 1) :=
  (identifiers.map fun identifier =>
    dimacsLiteral maximum identifier positive).getD row
      (dimacsLiteral maximum 0 positive)

def CnfLiteral.toDimacsInteger {variables : Nat}
    (literal : CnfLiteral variables) : Int :=
  if literal.positive then Int.ofNat literal.index.val
  else -Int.ofNat literal.index.val

def CnfCube.toDimacsIntegers {variables : Nat}
    (cube : CnfCube variables) : List Int :=
  cube.map CnfLiteral.toDimacsInteger

/-- Numeric DIMACS form of the same four-literal cube as
`exactEdgePairCube`. -/
def exactEdgePairDimacsCube
    (hBase hRows hWidth jBase jRows jWidth : Nat)
    (pair : Nat × Nat) : List Int :=
  [Int.ofNat (counterOutputDimacsVariable hBase hRows hWidth (pair.1 - 1)),
    -Int.ofNat (counterOutputDimacsVariable hBase hRows hWidth pair.1),
    Int.ofNat (counterOutputDimacsVariable jBase jRows jWidth (pair.2 - 1)),
    -Int.ofNat (counterOutputDimacsVariable jBase jRows jWidth pair.2)]

/-- Degree-20 formula: lex clauses end at variable 36627; the H counter ends
at 50767 and becomes the J counter's base. -/
def order45Degree20DimacsCubes : List (List Int) :=
  order45Degree20EdgePairs.map
    (exactEdgePairDimacsCube 36627 190 101 50767 276 133)

/-- Degree-21 formula: lex clauses end at variable 36630; the H counter ends
at 53532 and becomes the J counter's base. -/
def order45Degree21DimacsCubes : List (List Int) :=
  order45Degree21EdgePairs.map
    (exactEdgePairDimacsCube 36630 210 108 53532 253 123)

/-- Degree-22 formula: lex clauses end at variable 36631; the H counter ends
at 56641 and becomes the J counter's base. -/
def order45Degree22DimacsCubes : List (List Int) :=
  order45Degree22EdgePairs.map
    (exactEdgePairDimacsCube 36631 231 115 56641 231 115)

/-- Typed CNF cubes whose literal indices use the direct-DIMACS embedding.
Mapping them back to signed integers is checked below against every generated
manifest cube, not only the endpoints. -/
def order45Degree20CnfCubes : List (CnfCube (78697 + 1)) :=
  order45Degree20EdgePairs.map (exactEdgePairCube
    (counterStateDimacsLiteral 78697 36627 101 (190 - 1))
    (counterStateDimacsLiteral 78697 50767 133 (276 - 1)))

def order45Degree21CnfCubes : List (CnfCube (77148 + 1)) :=
  order45Degree21EdgePairs.map (exactEdgePairCube
    (counterStateDimacsLiteral 77148 36630 108 (210 - 1))
    (counterStateDimacsLiteral 77148 53532 123 (253 - 1)))

def order45Degree22CnfCubes : List (CnfCube (76651 + 1)) :=
  order45Degree22EdgePairs.map (exactEdgePairCube
    (counterStateDimacsLiteral 76651 36631 115 (231 - 1))
    (counterStateDimacsLiteral 76651 56641 115 (231 - 1)))

def order45Degree20HInput : Nat → CnfLiteral (78697 + 1) :=
  counterInputDimacsLiteral 78697 (order45HInputIdentifiers 20) true

def order45Degree20JInput : Nat → CnfLiteral (78697 + 1) :=
  counterInputDimacsLiteral 78697 (order45JInputIdentifiers 20) false

def order45Degree21HInput : Nat → CnfLiteral (77148 + 1) :=
  counterInputDimacsLiteral 77148 (order45HInputIdentifiers 21) true

def order45Degree21JInput : Nat → CnfLiteral (77148 + 1) :=
  counterInputDimacsLiteral 77148 (order45JInputIdentifiers 21) false

def order45Degree22HInput : Nat → CnfLiteral (76651 + 1) :=
  counterInputDimacsLiteral 76651 (order45HInputIdentifiers 22) true

def order45Degree22JInput : Nat → CnfLiteral (76651 + 1) :=
  counterInputDimacsLiteral 76651 (order45JInputIdentifiers 22) false

/-- The exact typed suffix emitted after the common Ramsey, fixed-star,
degree-window, and lex prefixes. It contains the H counter, J counter, four
range units, and all sum-threshold clauses. -/
def order45Degree20CounterTail : CnfFormula (78697 + 1) :=
  sequentialCounterCellFormula order45Degree20HInput
      (counterStateDimacsLiteral 78697 36627 101) 190 101 ++
    sequentialCounterCellFormula order45Degree20JInput
      (counterStateDimacsLiteral 78697 50767 133) 276 133 ++
    counterPairConstraintFormula
      (counterStateDimacsLiteral 78697 36627 101 (190 - 1))
      (counterStateDimacsLiteral 78697 50767 133 (276 - 1))
      101 133 68 100 116 132 226

def order45Degree21CounterTail : CnfFormula (77148 + 1) :=
  sequentialCounterCellFormula order45Degree21HInput
      (counterStateDimacsLiteral 77148 36630 108) 210 108 ++
    sequentialCounterCellFormula order45Degree21JInput
      (counterStateDimacsLiteral 77148 53532 123) 253 123 ++
    counterPairConstraintFormula
      (counterStateDimacsLiteral 77148 36630 108 (210 - 1))
      (counterStateDimacsLiteral 77148 53532 123 (253 - 1))
      108 123 77 107 101 122 222

def order45Degree22CounterTail : CnfFormula (76651 + 1) :=
  sequentialCounterCellFormula order45Degree22HInput
      (counterStateDimacsLiteral 76651 36631 115) 231 115 ++
    sequentialCounterCellFormula order45Degree22JInput
      (counterStateDimacsLiteral 76651 56641 115) 231 115 ++
    counterPairConstraintFormula
      (counterStateDimacsLiteral 76651 36631 115 (231 - 1))
      (counterStateDimacsLiteral 76651 56641 115 (231 - 1))
      115 115 88 114 88 114 220

set_option maxRecDepth 100000 in
theorem order45DimacsCubeCounts :
    order45Degree20DimacsCubes.length = 28 ∧
    order45Degree21DimacsCubes.length = 36 ∧
    order45Degree22DimacsCubes.length = 45 := by
  decide

set_option maxRecDepth 100000 in
theorem order45DimacsCubeEndpoints :
    order45Degree20DimacsCubes.head? =
      some [50760, -50761, 78696, -78697] ∧
    order45Degree20DimacsCubes.getLast? =
      some [50766, -50767, 78696, -78697] ∧
    order45Degree21DimacsCubes.head? =
      some [53524, -53525, 77147, -77148] ∧
    order45Degree21DimacsCubes.getLast? =
      some [53531, -53532, 77147, -77148] ∧
    order45Degree22DimacsCubes.head? =
      some [56632, -56633, 76650, -76651] ∧
    order45Degree22DimacsCubes.getLast? =
      some [56640, -56641, 76650, -76651] := by
  decide

set_option maxRecDepth 100000 in
theorem order45CounterFinalVariables :
    counterOutputDimacsVariable 50767 276 133 132 = 78697 ∧
    counterOutputDimacsVariable 53532 253 123 122 = 77148 ∧
    counterOutputDimacsVariable 56641 231 115 114 = 76651 := by
  decide

set_option maxRecDepth 100000 in
theorem order45TypedCubes_matchDimacs :
    order45Degree20CnfCubes.map CnfCube.toDimacsIntegers =
      order45Degree20DimacsCubes ∧
    order45Degree21CnfCubes.map CnfCube.toDimacsIntegers =
      order45Degree21DimacsCubes ∧
    order45Degree22CnfCubes.map CnfCube.toDimacsIntegers =
      order45Degree22DimacsCubes := by
  decide

set_option maxRecDepth 100000 in
theorem order45InternalInputDimensions :
    (order45HInputIdentifiers 20).length = 190 ∧
    (order45JInputIdentifiers 20).length = 276 ∧
    (order45HInputIdentifiers 21).length = 210 ∧
    (order45JInputIdentifiers 21).length = 253 ∧
    (order45HInputIdentifiers 22).length = 231 ∧
    (order45JInputIdentifiers 22).length = 231 := by
  decide

set_option maxRecDepth 100000 in
theorem order45InternalInputEndpoints :
    (order45HInputIdentifiers 20).head? = some 3 ∧
    (order45HInputIdentifiers 20).getLast? = some 210 ∧
    (order45JInputIdentifiers 20).head? = some 253 ∧
    (order45JInputIdentifiers 20).getLast? = some 990 ∧
    (order45HInputIdentifiers 21).getLast? = some 231 ∧
    (order45JInputIdentifiers 21).head? = some 276 ∧
    (order45HInputIdentifiers 22).getLast? = some 253 ∧
    (order45JInputIdentifiers 22).head? = some 300 := by
  decide

theorem order45Degree20CounterTail_cover :
    CnfCubeFamilyCoversFormula order45Degree20CounterTail
      order45Degree20CnfCubes := by
  simpa [order45Degree20CnfCubes] using
    (order45Degree20CounterEncoding_cover order45Degree20CounterTail
      order45Degree20HInput order45Degree20JInput
      (counterStateDimacsLiteral 78697 36627 101)
      (counterStateDimacsLiteral 78697 50767 133)
      (by
        intro clause membership
        simp [order45Degree20CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree20CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree20CounterTail, membership]))

theorem order45Degree21CounterTail_cover :
    CnfCubeFamilyCoversFormula order45Degree21CounterTail
      order45Degree21CnfCubes := by
  simpa [order45Degree21CnfCubes] using
    (order45Degree21CounterEncoding_cover order45Degree21CounterTail
      order45Degree21HInput order45Degree21JInput
      (counterStateDimacsLiteral 77148 36630 108)
      (counterStateDimacsLiteral 77148 53532 123)
      (by
        intro clause membership
        simp [order45Degree21CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree21CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree21CounterTail, membership]))

theorem order45Degree22CounterTail_cover :
    CnfCubeFamilyCoversFormula order45Degree22CounterTail
      order45Degree22CnfCubes := by
  simpa [order45Degree22CnfCubes] using
    (order45Degree22CounterEncoding_cover order45Degree22CounterTail
      order45Degree22HInput order45Degree22JInput
      (counterStateDimacsLiteral 76651 36631 115)
      (counterStateDimacsLiteral 76651 56641 115)
      (by
        intro clause membership
        simp [order45Degree22CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree22CounterTail, membership])
      (by
        intro clause membership
        simp [order45Degree22CounterTail, membership]))

theorem order45Degree20Mother_cover
    (formula : CnfFormula (78697 + 1))
    (tailIncluded : ∀ clause ∈ order45Degree20CounterTail,
      clause ∈ formula) :
    CnfCubeFamilyCoversFormula formula order45Degree20CnfCubes := by
  exact cnfCubeFamilyCoversFormula_of_subformula formula
    order45Degree20CounterTail order45Degree20CnfCubes
    order45Degree20CounterTail_cover tailIncluded

theorem order45Degree21Mother_cover
    (formula : CnfFormula (77148 + 1))
    (tailIncluded : ∀ clause ∈ order45Degree21CounterTail,
      clause ∈ formula) :
    CnfCubeFamilyCoversFormula formula order45Degree21CnfCubes := by
  exact cnfCubeFamilyCoversFormula_of_subformula formula
    order45Degree21CounterTail order45Degree21CnfCubes
    order45Degree21CounterTail_cover tailIncluded

theorem order45Degree22Mother_cover
    (formula : CnfFormula (76651 + 1))
    (tailIncluded : ∀ clause ∈ order45Degree22CounterTail,
      clause ∈ formula) :
    CnfCubeFamilyCoversFormula formula order45Degree22CnfCubes := by
  exact cnfCubeFamilyCoversFormula_of_subformula formula
    order45Degree22CounterTail order45Degree22CnfCubes
    order45Degree22CounterTail_cover tailIncluded

#print axioms order45DimacsCubeCounts
#print axioms order45DimacsCubeEndpoints
#print axioms order45CounterFinalVariables
#print axioms order45TypedCubes_matchDimacs
#print axioms order45InternalInputDimensions
#print axioms order45InternalInputEndpoints
#print axioms order45Degree20CounterTail_cover
#print axioms order45Degree21CounterTail_cover
#print axioms order45Degree22CounterTail_cover
#print axioms order45Degree20Mother_cover
#print axioms order45Degree21Mother_cover
#print axioms order45Degree22Mother_cover

end Ramsey55
