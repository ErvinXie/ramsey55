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

#print axioms order45DimacsCubeCounts
#print axioms order45DimacsCubeEndpoints
#print axioms order45CounterFinalVariables

end Ramsey55
