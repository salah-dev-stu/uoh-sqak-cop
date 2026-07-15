"""BrainBase seam + Decision (F8 — move is always algorithmic)."""

from __future__ import annotations

import pytest

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.brains import BrainBase, Decision
from cipherchase.domain.own_state import OwnState

EMPTY: frozenset[tuple[int, int]] = frozenset()


class _AlwaysNorth(BrainBase):
    def _pick_move(self, state, belief, barriers):  # type: ignore[no-untyped-def]
        return Direction.N


def test_decision_defaults() -> None:
    d = Decision(direction=Direction.STAY)
    assert d.intent == "truth"
    assert d.barrier_cell is None
    assert d.hint == ""


def test_base_pick_move_is_abstract() -> None:
    brain = BrainBase(Board(7))
    with pytest.raises(NotImplementedError):
        brain._pick_move(OwnState("thief", (3, 3)), BeliefGrid(7), EMPTY)


def test_decide_wraps_pick_move_with_no_barrier_by_default() -> None:
    brain = _AlwaysNorth(Board(7))
    decision = brain.decide(OwnState("thief", (3, 3)), BeliefGrid(7), EMPTY)
    assert isinstance(decision, Decision)
    assert decision.direction is Direction.N
    assert decision.barrier_cell is None
