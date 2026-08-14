"""Dependency-free CNF encodings of small cardinality constraints."""

from __future__ import annotations

from typing import Sequence

from .sat import Clause


def at_least_counter_encoding(
    inputs: Sequence[int], threshold: int, maximum_variable: int
) -> tuple[int, tuple[Clause, ...], tuple[int, ...]]:
    """Define all final ``at least j`` states through ``threshold``."""

    size = len(inputs)
    if not 1 <= threshold <= size:
        raise ValueError("counter threshold outside input range")
    if any(lit == 0 or abs(lit) > maximum_variable for lit in inputs):
        raise ValueError("counter inputs must be existing nonzero literals")
    if len({abs(lit) for lit in inputs}) != size:
        raise ValueError("counter inputs must be distinct")
    variable = maximum_variable
    clauses: list[Clause] = []
    state = [[0] * (threshold + 1) for _ in range(size + 1)]
    for i, item in enumerate(inputs, 1):
        for j in range(1, min(i, threshold) + 1):
            variable += 1
            current = state[i][j] = variable
            if i == j == 1:
                clauses += [(-current, item), (-item, current)]
            elif j == 1:
                old = state[i - 1][1]
                clauses += [(-old, current), (-item, current), (-current, old, item)]
            elif j == i:
                diagonal = state[i - 1][j - 1]
                clauses += [(-current, diagonal), (-current, item),
                            (-diagonal, -item, current)]
            else:
                old, diagonal = state[i - 1][j], state[i - 1][j - 1]
                clauses += [(-old, current), (-diagonal, -item, current),
                            (-current, old, diagonal), (-current, old, item)]
    outputs = tuple(state[size][j] for j in range(1, threshold + 1))
    return variable, tuple(clauses), outputs


def cardinality_range_encoding(
    inputs: Sequence[int],
    lower: int,
    upper: int,
    maximum_variable: int,
) -> tuple[int, tuple[Clause, ...]]:
    """Encode a range on the number of satisfied input literals.

    Auxiliary ``s[i,j]`` means that at least ``j`` of the first ``i`` inputs
    are true.  Defining both directions makes the auxiliary assignment unique,
    which simplifies independent checking and proof-producing preprocessing.
    The returned integer is the new maximum variable.
    """

    size = len(inputs)
    if lower < 0 or lower > upper or upper > size:
        raise ValueError("invalid cardinality range")
    if any(literal == 0 or abs(literal) > maximum_variable for literal in inputs):
        raise ValueError("cardinality inputs must be existing nonzero literals")
    if len({abs(literal) for literal in inputs}) != size:
        raise ValueError("cardinality inputs must be distinct")
    if lower == 0 and upper == size:
        return maximum_variable, ()

    variable = maximum_variable
    clauses: list[Clause] = []
    required_upper_state = upper + 1 if upper < size else 0
    threshold = min(size, max(lower, required_upper_state))
    at_least = [[0] * (threshold + 1) for _ in range(size + 1)]
    for i in range(1, size + 1):
        item = inputs[i - 1]
        for j in range(1, min(i, threshold) + 1):
            variable += 1
            current = variable
            at_least[i][j] = current
            if i == 1 and j == 1:
                clauses.extend(((-current, item), (-item, current)))
            elif j == 1:
                previous = at_least[i - 1][1]
                clauses.extend(
                    ((-previous, current), (-item, current),
                     (-current, previous, item))
                )
            elif j == i:
                lower_counter = at_least[i - 1][j - 1]
                clauses.extend(
                    ((-current, lower_counter), (-current, item),
                     (-lower_counter, -item, current))
                )
            else:
                previous = at_least[i - 1][j]
                lower_counter = at_least[i - 1][j - 1]
                clauses.extend(
                    (
                        (-previous, current),
                        (-lower_counter, -item, current),
                        (-current, previous, lower_counter),
                        (-current, previous, item),
                    )
                )
    if lower > 0:
        clauses.append((at_least[size][lower],))
    if upper < size:
        clauses.append((-at_least[size][upper + 1],))
    return variable, tuple(clauses)
