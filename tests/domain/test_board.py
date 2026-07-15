"""7×7 board geometry (FR-A1/A2)."""

from __future__ import annotations

import pytest

from cipherchase.constants import Direction
from cipherchase.domain.board import Board
from cipherchase.exceptions import IllegalMoveError

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_in_bounds() -> None:
    assert B.in_bounds((0, 0))
    assert B.in_bounds((6, 6))
    assert not B.in_bounds((-1, 0))
    assert not B.in_bounds((7, 0))
    assert not B.in_bounds((0, 7))


def test_manhattan_distance() -> None:
    assert B.distance((0, 0), (3, 3)) == 6
    assert B.distance((3, 3), (3, 3)) == 0


def test_target_of_applies_delta() -> None:
    assert B.target_of((3, 3), Direction.N) == (2, 3)
    assert B.target_of((3, 3), Direction.S) == (4, 3)
    assert B.target_of((3, 3), Direction.E) == (3, 4)
    assert B.target_of((3, 3), Direction.W) == (3, 2)
    assert B.target_of((3, 3), Direction.STAY) == (3, 3)


def test_step_legal_returns_target() -> None:
    assert B.step((3, 3), Direction.N, EMPTY) == (2, 3)


def test_step_off_board_raises() -> None:
    with pytest.raises(IllegalMoveError):
        B.step((0, 0), Direction.N, EMPTY)


def test_step_into_barrier_raises() -> None:
    with pytest.raises(IllegalMoveError):
        B.step((3, 3), Direction.E, frozenset({(3, 4)}))


def test_neighbors_excludes_out_of_bounds_and_barriers() -> None:
    # From corner (0,0): only S and E are in-bounds; block S with a barrier.
    assert set(B.neighbors((0, 0), frozenset({(1, 0)}))) == {(0, 1)}


def test_legal_moves_deterministic_order_with_stay() -> None:
    # From (0,0): N,W out of bounds → [S, E, STAY] in frozen order.
    assert B.legal_moves((0, 0), EMPTY) == [Direction.S, Direction.E, Direction.STAY]


def test_legal_moves_barrier_blocks_direction() -> None:
    assert B.legal_moves((0, 0), frozenset({(0, 1)})) == [Direction.S, Direction.STAY]


def test_board_size_is_config_driven_not_hardcoded() -> None:
    # A 5×5 board proves the size is injected, not a literal 7 (NFR-11).
    small = Board(5)
    assert small.in_bounds((4, 4))
    assert not small.in_bounds((5, 5))
