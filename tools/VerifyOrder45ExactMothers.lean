import Ramsey55.Order45LexAssignment

open Ramsey55

private def renderClause {variables : Nat}
    (clause : CnfClause variables) : String :=
  String.intercalate " "
      ((clause.map fun literal => toString literal.toDimacsInteger) ++ ["0"]) ++
    "\n"

private def verifyFormula {variables : Nat}
    (path : System.FilePath) (maximum expectedClauses : Nat)
    (formula : CnfFormula variables) : IO Unit := do
  let input ← IO.FS.Handle.mk path .read
  let header ← input.getLine
  let expectedHeader := s!"p cnf {maximum} {expectedClauses}\n"
  if header != expectedHeader then
    throw <| IO.userError s!"{path}: DIMACS header differs"
  let mut clauseNumber := 0
  for clause in formula do
    clauseNumber := clauseNumber + 1
    let actual ← input.getLine
    let expected := renderClause clause
    if actual != expected then
      throw <| IO.userError s!"{path}: clause {clauseNumber} differs"
  if clauseNumber != expectedClauses then
    throw <| IO.userError
      s!"{path}: typed formula has {clauseNumber} clauses, expected {expectedClauses}"
  let trailing ← input.getLine
  if !trailing.isEmpty then
    throw <| IO.userError s!"{path}: data follows the typed formula"
  IO.println s!"verified {path}: {clauseNumber} clauses"

def main (arguments : List String) : IO UInt32 := do
  let directory ← match arguments with
    | [directory] => pure (System.FilePath.mk directory)
    | _ =>
        IO.eprintln
          "usage: VerifyOrder45ExactMothers <order45-strata-directory>"
        return 2
  verifyFormula (directory / "r55-n45-strata-d20.cnf") 78697 2751846
    order45Degree20ExactFullMotherFormula
  verifyFormula (directory / "r55-n45-strata-d21.cnf") 77148 2745658
    order45Degree21ExactFullMotherFormula
  verifyFormula (directory / "r55-n45-strata-d22.cnf") 76651 2743672
    order45Degree22ExactFullMotherFormula
  return 0
