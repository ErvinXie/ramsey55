namespace Ramsey55

/-- A total Boolean assignment for a DIMACS-style finite variable set. -/
abbrev CnfAssignment (variables : Nat) := Fin variables → Bool

/-- A finite CNF literal. `positive = true` denotes the positive literal. -/
structure CnfLiteral (variables : Nat) where
  index : Fin variables
  positive : Bool
deriving DecidableEq, Repr

abbrev CnfClause (variables : Nat) := List (CnfLiteral variables)
abbrev CnfFormula (variables : Nat) := List (CnfClause variables)
abbrev CnfCube (variables : Nat) := List (CnfLiteral variables)

def CnfLiteral.Holds {variables : Nat}
    (assignment : CnfAssignment variables) (literal : CnfLiteral variables) : Prop :=
  assignment literal.index = literal.positive

def CnfLiteral.negate {variables : Nat}
    (literal : CnfLiteral variables) : CnfLiteral variables :=
  { literal with positive := !literal.positive }

theorem CnfLiteral.negate_holds_iff_not_holds {variables : Nat}
    (assignment : CnfAssignment variables) (literal : CnfLiteral variables) :
    literal.negate.Holds assignment ↔ ¬literal.Holds assignment := by
  simp only [CnfLiteral.Holds, CnfLiteral.negate]
  cases assignment literal.index <;> cases literal.positive <;> simp

def SatisfiesCnfClause {variables : Nat}
    (assignment : CnfAssignment variables) (clause : CnfClause variables) : Prop :=
  ∃ literal ∈ clause, literal.Holds assignment

def SatisfiesCnfFormula {variables : Nat}
    (assignment : CnfAssignment variables) (formula : CnfFormula variables) : Prop :=
  ∀ clause ∈ formula, SatisfiesCnfClause assignment clause

theorem SatisfiesCnfFormula.of_subset {variables : Nat}
    (assignment : CnfAssignment variables) (formula subformula : CnfFormula variables)
    (satisfied : SatisfiesCnfFormula assignment formula)
    (included : ∀ clause ∈ subformula, clause ∈ formula) :
    SatisfiesCnfFormula assignment subformula := by
  intro clause membership
  exact satisfied clause (included clause membership)

def SatisfiesCnfCube {variables : Nat}
    (assignment : CnfAssignment variables) (cube : CnfCube variables) : Prop :=
  ∀ literal ∈ cube, literal.Holds assignment

/-- The cube family is a DNF tautology over all assignments. -/
def CnfCubeFamilyCovers {variables : Nat}
    (cubes : List (CnfCube variables)) : Prop :=
  ∀ assignment, ∃ cube ∈ cubes, SatisfiesCnfCube assignment cube

/-- The cube family covers every assignment that satisfies a particular
mother formula. Unlike `CnfCubeFamilyCovers`, this permits a structural cover
whose cases are exhaustive only after the formula's counter and bound clauses
are assumed. -/
def CnfCubeFamilyCoversFormula {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables)) : Prop :=
  ∀ assignment, SatisfiesCnfFormula assignment formula →
    ∃ cube ∈ cubes, SatisfiesCnfCube assignment cube

def CnfCubeIsUnsat {variables : Nat}
    (formula : CnfFormula variables) (cube : CnfCube variables) : Prop :=
  ¬∃ assignment, SatisfiesCnfFormula assignment formula ∧
    SatisfiesCnfCube assignment cube

def CnfFormulaIsUnsat {variables : Nat} (formula : CnfFormula variables) : Prop :=
  ¬∃ assignment, SatisfiesCnfFormula assignment formula

theorem cnfLiteral_holds_or_negate {variables : Nat}
    (assignment : CnfAssignment variables) (literal : CnfLiteral variables) :
    literal.Holds assignment ∨ literal.negate.Holds assignment := by
  simp only [CnfLiteral.Holds, CnfLiteral.negate]
  cases assignment literal.index <;> cases literal.positive <;> simp

/-- A binary split on a literal covers every assignment satisfying its parent
cube. This is the local soundness step used by a dynamic cube tree. -/
theorem satisfies_split_of_satisfies_cube {variables : Nat}
    (assignment : CnfAssignment variables) (cube : CnfCube variables)
    (literal : CnfLiteral variables)
    (parent : SatisfiesCnfCube assignment cube) :
    SatisfiesCnfCube assignment (literal :: cube) ∨
      SatisfiesCnfCube assignment (literal.negate :: cube) := by
  rcases cnfLiteral_holds_or_negate assignment literal with positive | negative
  · left
    intro item membership
    simp only [List.mem_cons] at membership
    rcases membership with rfl | membership
    · exact positive
    · exact parent item membership
  · right
    intro item membership
    simp only [List.mem_cons] at membership
    rcases membership with rfl | membership
    · exact negative
    · exact parent item membership

/-- Replacing one covered parent by its two signed children preserves a cover
relative to the mother formula. -/
theorem cnfCubeFamilyCoversFormula_split_head {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables))
    (parent : CnfCube variables) (literal : CnfLiteral variables)
    (cover : CnfCubeFamilyCoversFormula formula (parent :: cubes)) :
    CnfCubeFamilyCoversFormula formula
      ((literal :: parent) :: (literal.negate :: parent) :: cubes) := by
  intro assignment formulaSatisfied
  rcases cover assignment formulaSatisfied with
    ⟨cube, cubeMember, cubeSatisfied⟩
  simp only [List.mem_cons] at cubeMember
  rcases cubeMember with rfl | cubeMember
  · rcases satisfies_split_of_satisfies_cube assignment cube literal
      cubeSatisfied with positive | negative
    · exact ⟨literal :: cube, by simp, positive⟩
    · exact ⟨literal.negate :: cube, by simp, negative⟩
  · exact ⟨cube, by simp [cubeMember], cubeSatisfied⟩

/-- An unconditional DNF cover is in particular a cover of the satisfying
assignments of any mother formula. -/
theorem cnfCubeFamilyCoversFormula_of_cover {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables))
    (cover : CnfCubeFamilyCovers cubes) :
    CnfCubeFamilyCoversFormula formula cubes := by
  intro assignment _
  exact cover assignment

/-- A cover proved from a structural CNF suffix also covers every satisfying
assignment of any larger mother formula that contains that suffix. -/
theorem cnfCubeFamilyCoversFormula_of_subformula {variables : Nat}
    (formula subformula : CnfFormula variables)
    (cubes : List (CnfCube variables))
    (cover : CnfCubeFamilyCoversFormula subformula cubes)
    (included : ∀ clause ∈ subformula, clause ∈ formula) :
    CnfCubeFamilyCoversFormula formula cubes := by
  intro assignment formulaSatisfied
  apply cover assignment
  exact SatisfiesCnfFormula.of_subset assignment formula subformula
    formulaSatisfied included

/-- Refuting every member of a formula-relative exhaustive cube family
refutes the mother CNF. This is the composition theorem used by structural
edge-count covers, which need not be tautologies on assignments that already
violate the mother formula. -/
theorem cnfFormulaIsUnsat_of_relativeCubeCover {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables))
    (cover : CnfCubeFamilyCoversFormula formula cubes)
    (leaves : ∀ cube ∈ cubes, CnfCubeIsUnsat formula cube) :
    CnfFormulaIsUnsat formula := by
  intro satisfiable
  rcases satisfiable with ⟨assignment, formulaSatisfied⟩
  rcases cover assignment formulaSatisfied with
    ⟨cube, cubeMember, cubeSatisfied⟩
  exact leaves cube cubeMember ⟨assignment, formulaSatisfied, cubeSatisfied⟩
/-- Independently refuting every member of an exhaustive cube family refutes
the mother CNF. The proof does not trust how the cubes or leaf proofs were
found; those enter only through `cover` and `leaves`. -/
theorem cnfFormulaIsUnsat_of_cubeCover {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables))
    (cover : CnfCubeFamilyCovers cubes)
    (leaves : ∀ cube ∈ cubes, CnfCubeIsUnsat formula cube) :
    CnfFormulaIsUnsat formula := by
  exact cnfFormulaIsUnsat_of_relativeCubeCover formula cubes
    (cnfCubeFamilyCoversFormula_of_cover formula cubes cover) leaves

#print axioms satisfies_split_of_satisfies_cube
#print axioms SatisfiesCnfFormula.of_subset
#print axioms cnfCubeFamilyCoversFormula_split_head
#print axioms cnfCubeFamilyCoversFormula_of_subformula
#print axioms cnfFormulaIsUnsat_of_relativeCubeCover
#print axioms cnfFormulaIsUnsat_of_cubeCover

end Ramsey55
