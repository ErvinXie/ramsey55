import Ramsey55.LratBridge
import Ramsey55.Ramsey34Target

open Ramsey55
open Std.Tactic.BVDecide
open Std.Sat

private def diagnoseFailure (proof : Array LRAT.IntAction)
    (formula : CNF Nat) : IO Unit := do
  let internalFormula := LRAT.Internal.CNF.convertLRAT formula
  let mut low := 0
  let mut high := proof.size
  while low < high do
    let middle := (low + high) / 2
    let result := LRAT.Internal.compactLratChecker internalFormula
      (proof.extract 0 middle)
    if result == .outOfProof then
      low := middle + 1
    else
      high := middle
  let result := LRAT.Internal.compactLratChecker internalFormula
    (proof.extract 0 low)
  IO.eprintln s!"first non-prefix result: end={low}, result={result}"
  if h : 0 < low ∧ low ≤ proof.size then
    IO.eprintln s!"action[{low - 1}]: {repr proof[low - 1]}"

def main (arguments : List String) : IO UInt32 := do
  let proofPath ← match arguments with
    | [proofPath] => pure (System.FilePath.mk proofPath)
    | _ =>
        IO.eprintln "usage: VerifyR34Lrat <r34-n9.lrat>"
        return 2
  let proof ← LRAT.loadLRATProof proofPath
  if LRAT.check proof ramsey34ExactFormula.toStd then
    IO.println s!"verified typed r34 LRAT: {proof.size} actions"
    return 0
  else
    IO.eprintln "typed r34 LRAT check failed"
    diagnoseFailure proof ramsey34ExactFormula.toStd
    return 1
