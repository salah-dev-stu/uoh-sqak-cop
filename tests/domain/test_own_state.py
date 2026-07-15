"""Immutable per-peer state (FR-A1). Never holds the opponent's truth."""

from __future__ import annotations

from cipherchase.domain.own_state import OwnState


def test_defaults() -> None:
    s = OwnState(role="thief", position=(3, 3))
    assert s.barriers == frozenset()
    assert s.turn == 0
    assert s.history == ()


def test_moved_to_is_immutable_and_records_history() -> None:
    s = OwnState(role="thief", position=(3, 3))
    s2 = s.moved_to((2, 3))
    assert s2.position == (2, 3)
    assert s2.history == ((3, 3),)
    assert s.position == (3, 3)  # original untouched
    assert s2 is not s


def test_with_barrier_adds_without_mutating() -> None:
    s = OwnState(role="police", position=(0, 0))
    s2 = s.with_barrier((0, 1))
    assert s2.barriers == frozenset({(0, 1)})
    assert s.barriers == frozenset()


def test_advanced_increments_turn() -> None:
    s = OwnState(role="police", position=(0, 0))
    assert s.advanced().turn == 1
    assert s.turn == 0
