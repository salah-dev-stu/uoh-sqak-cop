"""IC-9/10: belief stays a distribution under any op sequence; board legality closes."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.exceptions import IllegalMoveError

CELLS = [(r, c) for r in range(7) for c in range(7)]
cell = st.sampled_from(CELLS)
_smell = st.tuples(st.integers(0, 6), st.integers(0, 6),
                   st.floats(min_value=0, max_value=5, allow_nan=False, allow_infinity=False))
_op = st.one_of(
    st.lists(_smell, max_size=6).map(lambda es: ("smell", es)),
    cell.map(lambda c: ("exclude", c)),
    st.just(("diffuse", None)),
)
BOARD = Board(7)


@given(st.lists(_op, max_size=30))
def test_belief_is_always_a_distribution(ops) -> None:
    grid = BeliefGrid(7, smell_trust=4.0, alpha=0.85)
    for kind, arg in ops:
        if kind == "smell":
            grid.observe_smell({f"{r},{c}": v for r, c, v in arg})
        elif kind == "exclude":
            grid.exclude(arg)
        else:
            grid.diffuse()
        masses = [m for row in grid.as_matrix() for m in row]
        assert abs(sum(masses) - 1.0) <= 1e-9
        assert all(m >= 0.0 for m in masses)
        assert grid.most_likely() in CELLS


@given(cell, st.frozensets(cell, max_size=8))
def test_board_move_legality_closure(start, barriers) -> None:
    barriers = barriers - {start}
    legal = set(BOARD.legal_moves(start, barriers))
    for direction in legal:
        target = BOARD.step(start, direction, barriers)  # legal → never raises
        if direction is Direction.STAY:
            assert target == start
        else:
            assert BOARD.in_bounds(target) and target not in barriers
    for direction in Direction:
        if direction is Direction.STAY or direction in legal:
            continue
        with pytest.raises(IllegalMoveError):
            BOARD.step(start, direction, barriers)  # everything else is illegal
