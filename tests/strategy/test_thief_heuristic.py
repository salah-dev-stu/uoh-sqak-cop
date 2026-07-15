"""ThiefBrain evasion heuristic (FR-C3, F8 — algorithmic move)."""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.thief_heuristic import ThiefBrain

EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_thief_flees_away_from_believed_cop() -> None:
    brain = ThiefBrain(Board(7))
    belief = BeliefGrid(7)  # uniform → most_likely (0,0) = believed cop corner
    decision = brain.decide(OwnState("thief", (3, 3)), belief, EMPTY)
    # Moving away from (0,0): S or E increase distance; deterministic tie → S.
    assert decision.direction is Direction.S
    assert decision.barrier_cell is None  # thief never places barriers


def test_thief_stays_when_only_stay_is_legal() -> None:
    brain = ThiefBrain(Board(7))
    walled = frozenset({(0, 1), (1, 0)})  # thief at (0,0) fully boxed
    decision = brain.decide(OwnState("thief", (0, 0)), BeliefGrid(7), walled)
    assert decision.direction is Direction.STAY


def test_thief_move_is_always_legal() -> None:
    brain = ThiefBrain(Board(7))
    decision = brain.decide(OwnState("thief", (6, 6)), BeliefGrid(7), EMPTY)
    assert decision.direction in Board(7).legal_moves((6, 6), EMPTY)
