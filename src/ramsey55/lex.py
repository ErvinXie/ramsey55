"""Small CNF lexicographic symmetry encodings."""

from __future__ import annotations

from typing import Sequence

from .sat import Clause


def lex_leq_encoding(
    left: Sequence[int], right: Sequence[int], maximum_variable: int
) -> tuple[int, tuple[Clause, ...]]:
    """Encode ``left <= right`` for Boolean rows with false before true."""

    if len(left) != len(right) or not left:
        raise ValueError("lex rows must have the same positive width")
    inputs = tuple(left) + tuple(right)
    if any(variable <= 0 or variable > maximum_variable for variable in inputs):
        raise ValueError("lex inputs must be existing positive variables")
    if len(set(inputs)) != len(inputs):
        raise ValueError("lex inputs must be distinct")

    variable = maximum_variable
    prefix_equal = 0
    clauses: list[Clause] = []
    for column, (left_bit, right_bit) in enumerate(zip(left, right)):
        order = [] if prefix_equal == 0 else [-prefix_equal]
        clauses.append(tuple((*order, -left_bit, right_bit)))
        if column + 1 == len(left):
            continue
        variable += 1
        next_equal = variable
        if prefix_equal:
            clauses.append((-next_equal, prefix_equal))
        clauses.extend(
            (
                (-next_equal, -left_bit, right_bit),
                (-next_equal, left_bit, -right_bit),
            )
        )
        if prefix_equal:
            clauses.extend(
                (
                    (-prefix_equal, -left_bit, -right_bit, next_equal),
                    (-prefix_equal, left_bit, right_bit, next_equal),
                )
            )
        else:
            clauses.extend(
                ((-left_bit, -right_bit, next_equal),
                 (left_bit, right_bit, next_equal))
            )
        prefix_equal = next_equal
    return variable, tuple(clauses)
