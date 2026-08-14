import Ramsey55.Definitions

namespace Ramsey55

/-- Twice the constant part of the order-45 local excess contribution for a
vertex of degree `degree`.  If `H` is its neighbourhood and `J` is the
complement of its dual neighbourhood, the full doubled contribution is this
constant minus `2 * (e(H) + e(J))`. -/
def twoOrder45LocalExcessConstant (degree : Nat) : Int :=
  let d : Int := degree
  (44 - d) * (43 - d) - d * (45 - 2 * d)

theorem twoOrder45LocalExcessConstant_values :
    twoOrder45LocalExcessConstant 20 = 452 ∧
    twoOrder45LocalExcessConstant 21 = 443 ∧
    twoOrder45LocalExcessConstant 22 = 440 ∧
    twoOrder45LocalExcessConstant 23 = 443 ∧
    twoOrder45LocalExcessConstant 24 = 452 := by
  decide

/-- Arithmetic core of the order-45 degree normalization.  The five counts
sum to 45, while the handshake lemma says that the number of odd-degree
vertices is even.  Hence an even degree 20, 22, or 24 occurs; complementation
turns the degree-24 case into degree 20.  Connecting these counts to an actual
Ramsey-free colouring and proving its 20--24 degree window are separate
graph-theoretic obligations. -/
theorem order45_even_degree_split_from_counts
    (n20 n21 n22 n23 n24 oddPairs : Nat)
    (total : n20 + n21 + n22 + n23 + n24 = 45)
    (oddDegrees : n21 + n23 = 2 * oddPairs) :
    (0 < n20 ∨ 0 < n24) ∨ 0 < n22 := by
  omega

theorem order45_dense_pair_of_nonpositive_degree20
    (edgesH edgesJ : Int)
    (nonpositive : 452 - 2 * (edgesH + edgesJ) ≤ 0) :
    226 ≤ edgesH + edgesJ := by
  omega

theorem order45_dense_pair_of_nonpositive_degree21
    (edgesH edgesJ : Int)
    (nonpositive : 443 - 2 * (edgesH + edgesJ) ≤ 0) :
    222 ≤ edgesH + edgesJ := by
  omega

theorem order45_dense_pair_of_nonpositive_degree22
    (edgesH edgesJ : Int)
    (nonpositive : 440 - 2 * (edgesH + edgesJ) ≤ 0) :
    220 ≤ edgesH + edgesJ := by
  omega

#print axioms order45_even_degree_split_from_counts
#print axioms order45_dense_pair_of_nonpositive_degree20
#print axioms order45_dense_pair_of_nonpositive_degree21
#print axioms order45_dense_pair_of_nonpositive_degree22

end Ramsey55
