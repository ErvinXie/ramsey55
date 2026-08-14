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

def SatisfiesCnfClause {variables : Nat}
    (assignment : CnfAssignment variables) (clause : CnfClause variables) : Prop :=
  ∃ literal ∈ clause, literal.Holds assignment

def SatisfiesCnfFormula {variables : Nat}
    (assignment : CnfAssignment variables) (formula : CnfFormula variables) : Prop :=
  ∀ clause ∈ formula, SatisfiesCnfClause assignment clause

def SatisfiesCnfCube {variables : Nat}
    (assignment : CnfAssignment variables) (cube : CnfCube variables) : Prop :=
  ∀ literal ∈ cube, literal.Holds assignment

/-- The cube family is a DNF tautology over all assignments. -/
def CnfCubeFamilyCovers {variables : Nat}
    (cubes : List (CnfCube variables)) : Prop :=
  ∀ assignment, ∃ cube ∈ cubes, SatisfiesCnfCube assignment cube

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

/-- Independently refuting every member of an exhaustive cube family refutes
the mother CNF. The proof does not trust how the cubes or leaf proofs were
found; those enter only through `cover` and `leaves`. -/
theorem cnfFormulaIsUnsat_of_cubeCover {variables : Nat}
    (formula : CnfFormula variables) (cubes : List (CnfCube variables))
    (cover : CnfCubeFamilyCovers cubes)
    (leaves : ∀ cube ∈ cubes, CnfCubeIsUnsat formula cube) :
    CnfFormulaIsUnsat formula := by
  intro satisfiable
  rcases satisfiable with ⟨assignment, formulaSatisfied⟩
  rcases cover assignment with ⟨cube, cubeMember, cubeSatisfied⟩
  exact leaves cube cubeMember ⟨assignment, formulaSatisfied, cubeSatisfied⟩

#print axioms satisfies_split_of_satisfies_cube
#print axioms cnfFormulaIsUnsat_of_cubeCover

end Ramsey55
