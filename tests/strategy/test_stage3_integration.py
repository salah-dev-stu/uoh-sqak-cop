"""Milestone S3: with a known target the agent computes + executes a path.

Also guards F8: the strategy layer never touches the LLM to decide a move.
"""

from __future__ import annotations

from pathlib import Path

from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.police_heuristic import PoliceBrain
from cipherchase.strategy.thief_heuristic import ThiefBrain

EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_police_autonomously_reaches_a_known_target() -> None:
    board = Board(7)
    brain = PoliceBrain(board)
    belief = BeliefGrid(7, smell_trust=4.0)
    belief.observe_smell({"3,3": 0.95})  # known thief location
    pos = (0, 0)
    for _ in range(12):
        decision = brain.decide(OwnState("police", pos), belief, EMPTY)
        pos = board.step(pos, decision.direction, EMPTY)
        if pos == (3, 3):
            break
    assert pos == (3, 3)


def test_thief_increases_distance_from_a_known_pursuer() -> None:
    board = Board(7)
    brain = ThiefBrain(board)
    belief = BeliefGrid(7, smell_trust=4.0)
    belief.observe_smell({"3,3": 0.95})  # believed cop at (3,3)
    start = (2, 2)
    decision = brain.decide(OwnState("thief", start), belief, EMPTY)
    moved = board.step(start, decision.direction, EMPTY)
    assert board.distance(moved, (3, 3)) >= board.distance(start, (3, 3))


def test_strategy_layer_never_imports_the_llm() -> None:
    strat = Path(__file__).resolve().parents[2] / "src" / "cipherchase" / "strategy"
    for py in strat.glob("*heuristic.py"):
        assert "llm_provider" not in py.read_text()
