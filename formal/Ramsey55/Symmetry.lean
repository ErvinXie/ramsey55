import Init.Data.List.MinMax

namespace Ramsey55

universe u

/-- A finite, transformation-closed orbit has a least element. If a predicate
is true throughout that orbit, its least element is a satisfying assignment
that obeys every corresponding lex-leader inequality.

This is the abstract bridge needed to use independently checked symmetry
clauses without claiming that those clauses are logical consequences of the
unsymmetrized CNF. A concrete certificate must still show that its listed
relabelings preserve the base predicate and that the orbit is closed under
them. -/
theorem exists_finite_orbit_leader
    {Assignment : Type u} [LE Assignment] [Min Assignment]
    [Std.IsLinearOrder Assignment] [Std.LawfulOrderMin Assignment]
    (transformations : List (Assignment → Assignment))
    (orbit : List Assignment) (predicate : Assignment → Prop)
    (orbitNonempty : orbit ≠ [])
    (orbitSatisfies : ∀ assignment ∈ orbit, predicate assignment)
    (orbitClosed : ∀ assignment ∈ orbit,
      ∀ transformation ∈ transformations, transformation assignment ∈ orbit) :
    ∃ leader, leader ∈ orbit ∧ predicate leader ∧
      ∀ transformation ∈ transformations,
        leader ≤ transformation leader := by
  let leader := orbit.min orbitNonempty
  have leaderMember : leader ∈ orbit := List.min_mem orbitNonempty
  refine ⟨leader, leaderMember, orbitSatisfies leader leaderMember, ?_⟩
  intro transformation transformationMember
  exact List.min_le_of_mem
    (orbitClosed leader leaderMember transformation transformationMember)

#print axioms exists_finite_orbit_leader

end Ramsey55
