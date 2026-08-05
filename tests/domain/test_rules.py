"""Capture / survival / barrier adjudication (FR-A2/A3/A4)."""

from __future__ import annotations

import pytest

from cipherchase.constants import Direction, Outcome
from cipherchase.domain import rules
from cipherchase.domain.board import Board
from cipherchase.exceptions import IllegalBarrierError, IllegalMoveError

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_is_legal_move() -> None:
    assert rules.is_legal_move(B, (3, 3), Direction.N, EMPTY)
    assert not rules.is_legal_move(B, (0, 0), Direction.N, EMPTY)
    assert not rules.is_legal_move(B, (3, 3), Direction.E, frozenset({(3, 4)}))


def test_validate_move() -> None:
    assert rules.validate_move(B, (3, 3), Direction.S, EMPTY) == (4, 3)
    with pytest.raises(IllegalMoveError):
        rules.validate_move(B, (0, 0), Direction.W, EMPTY)


def test_can_place_barrier_adjacent_within_budget() -> None:
    assert rules.can_place_barrier(B, (0, 0), (0, 1), EMPTY, 14)


def test_cannot_place_barrier_non_adjacent() -> None:
    assert not rules.can_place_barrier(B, (0, 0), (3, 3), EMPTY, 14)


def test_cannot_place_barrier_off_board_or_existing_or_over_budget() -> None:
    assert not rules.can_place_barrier(B, (0, 0), (-1, 0), EMPTY, 14)
    assert not rules.can_place_barrier(B, (0, 0), (0, 1), frozenset({(0, 1)}), 14)
    assert not rules.can_place_barrier(B, (0, 0), (0, 1), frozenset({(1, 0)}), 1)


def test_barrier_budget_is_config_driven() -> None:
    # Two already placed; target (2,1) is adjacent to cop (1,1) and free.
    placed = frozenset({(1, 0), (0, 1)})
    assert not rules.can_place_barrier(B, (1, 1), (2, 1), placed, 2)  # budget full
    assert rules.can_place_barrier(B, (1, 1), (2, 1), placed, 3)  # budget available


def test_validate_barrier_returns_target_or_raises() -> None:
    assert rules.validate_barrier(B, (0, 0), (0, 1), EMPTY, 14) == (0, 1)
    with pytest.raises(IllegalBarrierError):
        rules.validate_barrier(B, (0, 0), (3, 3), EMPTY, 14)


def test_is_boxed_in_when_all_escapes_blocked() -> None:
    barriers = frozenset({(1, 0), (0, 1)})
    assert rules.is_boxed_in(B, (0, 0), (5, 5), barriers)
    assert not rules.is_boxed_in(B, (0, 0), (5, 5), EMPTY)


def test_is_capture_colocation_and_barrier_on_thief() -> None:
    assert rules.is_capture(B, (2, 2), (2, 2), EMPTY)  # co-location
    assert rules.is_capture(B, (5, 5), (0, 0), frozenset({(0, 0)}))  # barrier on thief cell
    assert not rules.is_capture(B, (0, 0), (6, 6), EMPTY)


def test_an_enclosure_is_a_capture_from_any_distance() -> None:
    # The book's three capture families are equal in standing, so there is no
    # cop-adjacency condition. We used to require one; that made us score
    # SURVIVAL where a conforming opponent scored CAPTURE — rule 35 zeroes both
    # teams for exactly that contradiction.
    boxed = frozenset({(1, 0), (0, 1)})  # thief (0,0) has no legal move
    assert rules.is_capture(B, (5, 5), (0, 0), boxed)
    assert rules.outcome(B, (5, 5), (0, 0), boxed, 3, survival_threshold=35) is Outcome.CAPTURE
    # The cop's own body is not a wall: it blocks no move under rules 46/47.
    assert not rules.is_capture(B, (1, 0), (0, 0), frozenset({(0, 1)}))


def test_reachable_cells_open_board_is_everything() -> None:
    assert len(rules.reachable_cells(B, (0, 0), EMPTY)) == 49


def test_reachable_cells_shrinks_with_barriers() -> None:
    boxed = rules.reachable_cells(B, (0, 0), frozenset({(1, 0), (0, 1)}))
    assert boxed == frozenset({(0, 0)})


def test_outcome_capture_survival_none() -> None:
    assert rules.outcome(B, (2, 2), (2, 2), EMPTY, 3, survival_threshold=35) is Outcome.CAPTURE
    assert rules.outcome(B, (0, 0), (6, 6), EMPTY, 35, survival_threshold=35) is Outcome.SURVIVAL
    assert rules.outcome(B, (0, 0), (6, 6), EMPTY, 3, survival_threshold=35) is None


def test_is_enclosed_is_the_spec_rule_46_and_47_predicate() -> None:
    # SPEC 3.1 / rules 46-47: a barrier on the thief's OWN cell, or every
    # orthogonal neighbour a barrier or off the board. The cop's body is not
    # part of it — enclosure is a fact of the thief's cell alone, which is why
    # only the thief can observe it and therefore must SAY it (concession).
    assert rules.is_enclosed(B, (2, 2), frozenset({(2, 2)}))  # rule 46
    walled = frozenset({(1, 2), (3, 2), (2, 1), (2, 3)})
    assert rules.is_enclosed(B, (2, 2), walled)  # rule 47
    assert not rules.is_enclosed(B, (2, 2), frozenset({(1, 2), (3, 2), (2, 1)}))  # one exit
    corner = frozenset({(1, 0), (0, 1)})  # off-board edges count as walls
    assert rules.is_enclosed(B, (0, 0), corner)
    assert not rules.is_enclosed(B, (2, 2), frozenset()), "a cop adjacent is not enclosure"
