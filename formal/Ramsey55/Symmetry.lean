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

/-- If every satisfying assignment comes with a finite closed orbit of
satisfying assignments, refuting all assignments that obey the listed
lex-leader inequalities refutes the original predicate. -/
theorem predicate_unsat_of_no_finite_orbit_leader
    {Assignment : Type u} [LE Assignment] [Min Assignment]
    [Std.IsLinearOrder Assignment] [Std.LawfulOrderMin Assignment]
    (transformations : List (Assignment → Assignment))
    (predicate : Assignment → Prop)
    (orbit : Assignment → List Assignment)
    (orbitNonempty : ∀ assignment, orbit assignment ≠ [])
    (orbitSatisfies : ∀ assignment, predicate assignment →
      ∀ member ∈ orbit assignment, predicate member)
    (orbitClosed : ∀ assignment, ∀ member ∈ orbit assignment,
      ∀ transformation ∈ transformations,
        transformation member ∈ orbit assignment)
    (noLeader : ¬∃ leader, predicate leader ∧
      ∀ transformation ∈ transformations,
        leader ≤ transformation leader) :
    ¬∃ assignment, predicate assignment := by
  rintro ⟨assignment, satisfies⟩
  rcases exists_finite_orbit_leader transformations (orbit assignment)
      predicate (orbitNonempty assignment)
      (orbitSatisfies assignment satisfies) (orbitClosed assignment) with
    ⟨leader, _, leaderSatisfies, leaderMinimal⟩
  exact noLeader ⟨leader, leaderSatisfies, leaderMinimal⟩

#print axioms exists_finite_orbit_leader
#print axioms predicate_unsat_of_no_finite_orbit_leader

end Ramsey55
