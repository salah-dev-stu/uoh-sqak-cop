"""PoliceBrain pursuit + barrier box-in heuristic (FR-C3, F8)."""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.police_heuristic import PoliceBrain

EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_police_pursues_toward_believed_thief() -> None:
    brain = PoliceBrain(Board(7))
    belief = BeliefGrid(7, smell_trust=4.0)
    belief.observe_smell({"3,3": 0.9})  # believed thief at (3,3)
    decision = brain.decide(OwnState("police", (0, 0)), belief, EMPTY)
    assert decision.direction is Direction.S  # steps toward (3,3), tie → S


def test_police_places_barrier_that_boxes_the_thief() -> None:
    brain = PoliceBrain(Board(7))
    belief = BeliefGrid(7)  # uniform → believed thief at corner (0,0)
    decision = brain.decide(OwnState("police", (0, 2)), belief, frozenset({(1, 0)}))
    # Barrier at (0,1) seals (0,0)'s last exit → massive reachability drop.
    assert decision.barrier_cell == (0, 1)


def test_police_barrier_is_a_legal_adjacent_placement() -> None:
    brain = PoliceBrain(Board(7))
    decision = brain.decide(OwnState("police", (3, 3)), BeliefGrid(7), EMPTY)
    if decision.barrier_cell is not None:
        assert Board(7).distance((3, 3), decision.barrier_cell) == 1


def test_police_move_is_always_legal() -> None:
    brain = PoliceBrain(Board(7))
    decision = brain.decide(OwnState("police", (6, 6)), BeliefGrid(7), EMPTY)
    assert decision.direction in Board(7).legal_moves((6, 6), EMPTY)
