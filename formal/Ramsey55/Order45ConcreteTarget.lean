import Ramsey55.Order45LexRelabeling
import Ramsey55.Ramsey34Target

namespace Ramsey55

/-- Fully concrete logical endpoint for the current order-45 certificate
route.  The `R(4,5) = 25` premise is expanded into the exact order-9
`R(3,4)` CNF and the degree-8/10/12 order-25 fixed-star CNFs.  Together with
the five published local-catalog ranges, the remaining order-45 inputs are
exactly the 109 formula-relative mother/cube refutations. -/
theorem forcesMonochromatic5_45_of_exactCnfInputs
    (r34Unsat : CnfFormulaIsUnsat ramsey34ExactFormula)
    (r45Degree8Unsat :
      CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 8))
    (r45Degree10Unsat :
      CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 10))
    (r45Degree12Unsat :
      CnfFormulaIsUnsat (ramsey45ExactFixedStarFormula 12))
    (ranges : Order45ExcessCatalogRanges)
    (leaves20 : ∀ cube ∈ order45Degree20CnfCubes,
      CnfCubeIsUnsat order45Degree20ExactFullMotherFormula cube)
    (leaves21 : ∀ cube ∈ order45Degree21CnfCubes,
      CnfCubeIsUnsat order45Degree21ExactFullMotherFormula cube)
    (leaves22 : ∀ cube ∈ order45Degree22CnfCubes,
      CnfCubeIsUnsat order45Degree22ExactFullMotherFormula cube) :
    ForcesMonochromatic5 45 := by
  exact forcesMonochromatic5_45_of_exactFullMotherCubeRefutations
    (forcesRed4OrBlue5_of_r34ExactCnfAndThreeExactFixedStarUnsat
      r34Unsat r45Degree8Unsat r45Degree10Unsat r45Degree12Unsat)
    ranges leaves20 leaves21 leaves22

#print axioms forcesMonochromatic5_45_of_exactCnfInputs

end Ramsey55
