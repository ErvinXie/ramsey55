"""Dependency-free CNF encodings of small cardinality constraints."""

from __future__ import annotations

from typing import Sequence

from .sat import Clause


def cardinality_range_encoding(
    inputs: Sequence[int],
    lower: int,
    upper: int,
    maximum_variable: int,
) -> tuple[int, tuple[Clause, ...]]:
    """Encode ``lower <= sum(inputs) <= upper`` with full counter equivalences.

    Auxiliary ``s[i,j]`` means that at least ``j`` of the first ``i`` inputs
    are true.  Defining both directions makes the auxiliary assignment unique,
    which simplifies independent checking and proof-producing preprocessing.
    The returned integer is the new maximum variable.
    """

    size = len(inputs)
    if lower < 0 or lower > upper or upper > size:
        raise ValueError("invalid cardinality range")
    if any(variable <= 0 or variable > maximum_variable for variable in inputs):
        raise ValueError("cardinality inputs must be existing positive variables")
    if len(set(inputs)) != size:
        raise ValueError("cardinality inputs must be distinct")
    if lower == 0 and upper == size:
        return maximum_variable, ()

    variable = maximum_variable
    clauses: list[Clause] = []
    threshold = min(size, upper + 1)
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
