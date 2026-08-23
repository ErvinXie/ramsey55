import Std.Tactic.BVDecide.LRAT

open Std.Tactic.BVDecide

namespace Ramsey55.Tools.NormalizeLratIds

private def remapReference (inputClauses : Nat)
    (mapping : Std.HashMap Nat Nat) (identifier : Nat) : Except String Nat := do
  if identifier == 0 then
    throw "LRAT clause reference zero is invalid"
  if identifier ≤ inputClauses then
    return identifier
  match mapping[identifier]? with
  | some remapped => return remapped
  | none => throw s!"LRAT reference {identifier} precedes its defining action"

private def remapReferences (inputClauses : Nat)
    (mapping : Std.HashMap Nat Nat) (identifiers : Array Nat) :
    Except String (Array Nat) :=
  identifiers.mapM (remapReference inputClauses mapping)

/-- Densely renumber every added LRAT clause after the fixed input-clause
prefix.  Lean's compact LRAT checker stores additions by array position, so it
requires this normal form even though the LRAT format itself permits gaps. -/
def normalize (inputClauses : Nat) (proof : Array LRAT.IntAction) :
    Except String (Array LRAT.IntAction) := do
  let mut mapping : Std.HashMap Nat Nat := {}
  let mut normalized := #[]
  let mut additions := 0
  for action in proof do
    match action with
    | .del identifiers =>
        let remapped ← remapReferences inputClauses mapping identifiers
        normalized := normalized.push (.del remapped)
    | .addEmpty identifier rupHints =>
        if identifier ≤ inputClauses || mapping.contains identifier then
          throw s!"duplicate or input LRAT addition identifier {identifier}"
        let remappedHints ← remapReferences inputClauses mapping rupHints
        let denseIdentifier := inputClauses + additions + 1
        mapping := mapping.insert identifier denseIdentifier
        additions := additions + 1
        normalized := normalized.push (.addEmpty denseIdentifier remappedHints)
    | .addRup identifier clause rupHints =>
        if identifier ≤ inputClauses || mapping.contains identifier then
          throw s!"duplicate or input LRAT addition identifier {identifier}"
        let remappedHints ← remapReferences inputClauses mapping rupHints
        let denseIdentifier := inputClauses + additions + 1
        mapping := mapping.insert identifier denseIdentifier
        additions := additions + 1
        normalized := normalized.push
          (.addRup denseIdentifier clause remappedHints)
    | .addRat identifier clause pivot rupHints ratHints =>
        if identifier ≤ inputClauses || mapping.contains identifier then
          throw s!"duplicate or input LRAT addition identifier {identifier}"
        let remappedRupHints ← remapReferences inputClauses mapping rupHints
        let remappedRatHints ← ratHints.mapM fun (candidate, hints) => do
          let remappedCandidate ← remapReference inputClauses mapping candidate
          let remappedHints ← remapReferences inputClauses mapping hints
          return (remappedCandidate, remappedHints)
        let denseIdentifier := inputClauses + additions + 1
        mapping := mapping.insert identifier denseIdentifier
        additions := additions + 1
        normalized := normalized.push
          (.addRat denseIdentifier clause pivot remappedRupHints remappedRatHints)
  return normalized

end Ramsey55.Tools.NormalizeLratIds

def main (arguments : List String) : IO UInt32 := do
  let (inputClauses, inputPath, outputPath) ← match arguments with
    | [inputClauses, inputPath, outputPath] =>
        let some inputClauses := inputClauses.toNat?
          | throw <| IO.userError s!"invalid input clause count: {inputClauses}"
        pure (inputClauses, System.FilePath.mk inputPath,
          System.FilePath.mk outputPath)
    | _ =>
        IO.eprintln "usage: NormalizeLratIds <input-clauses> <input.lrat> <output.lrat>"
        return 2
  let proof ← LRAT.loadLRATProof inputPath
  let normalized ← match Ramsey55.Tools.NormalizeLratIds.normalize inputClauses proof with
    | .ok normalized => pure normalized
    | .error message => throw <| IO.userError message
  IO.FS.writeFile outputPath (LRAT.lratProofToString normalized)
  IO.println s!"normalized {proof.size} LRAT actions ({normalized.size} emitted)"
  return 0
