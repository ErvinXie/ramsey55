import Ramsey55.Ramsey34Target

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
  let path ← match arguments with
    | [path] => pure (System.FilePath.mk path)
    | _ =>
        IO.eprintln "usage: VerifyRamsey34Exact <r34-n9.cnf>"
        return 2
  verifyFormula path 36 210 ramsey34ExactFormula
  return 0
