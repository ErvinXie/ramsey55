import Ramsey55.Ramsey45Target

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

private def paddedDegree (degree : Nat) : String :=
  if degree < 10 then "0" ++ toString degree else toString degree

def main (arguments : List String) : IO UInt32 := do
  let directory ← match arguments with
    | [directory] => pure (System.FilePath.mk directory)
    | _ =>
        IO.eprintln
          "usage: VerifyRamsey45ExactBranches <r45-fixed-star-directory>"
        return 2
  for degree in List.range 25 do
    let path := directory /
      s!"r45-n25-fixed-d{paddedDegree degree}.cnf"
    verifyFormula path 300 65804 (ramsey45ExactFixedStarFormula degree)
  return 0
