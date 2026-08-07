"""Strategy seam (F8): the MOVE is always pure Python; the LLM only fills text.

``_pick_move`` (direction) and ``_decide_move`` (full decision incl. any
barrier) are the graded hooks. ``Decision.intent`` — ``"truth"``/``"lie"`` — is
the bluff flag bound into the commit (PLAN §8.1); the ``hint`` text is written
later by the trash-talk layer, never here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState


def under_barrier_law(decision: Decision) -> Decision:
    """A cop that places a barrier FORGOES its step that turn (book ch.3).

    Stated twice in chapter 3 — in the body and in the boxed rule of the same
    name — and implemented by the reference as an exclusive move TYPE:
    MOVE | BARRIER | HOLD, "the three legal actions an agent may take in a turn".

    Applied here, at the one place every brain's decision passes through, so no
    strategy can take two actions in a turn by construction. We shipped a season
    of cop games that stepped AND walled; an extra action per turn against an
    opponent taking one is precisely the asymmetry this law prices.
    """
    if decision.barrier_cell is None or decision.direction is Direction.STAY:
        return decision
    return replace(decision, direction=Direction.STAY)


@dataclass
class Decision:
    direction: Direction
    intent: str = "truth"
    hint: str = ""
    barrier_cell: Cell | None = None
    fallback: bool = False
    reasoning: str = ""


class BrainBase:
    """Base brain. Subclasses implement ``_pick_move`` (+ ``_pick_barrier`` for cop)."""

    role = "base"

    def __init__(self, board: Board, params: dict[str, Any] | None = None, rng: Any = None) -> None:
        self.board = board
        self.params = params or {}
        self.rng = rng

    def param(self, key: str, default: float) -> float:
        """Config-first numeric parameter lookup (single helper, R2)."""
        return float(self.params.get(key, default))

    def decide(self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]) -> Decision:
        # Every brain's decision passes through here, so the Barrier Law cannot
        # be bypassed by a strategy that would rather have both actions.
        return under_barrier_law(self._decide_move(state, belief, barriers))

    def _decide_move(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Decision:
        return Decision(
            direction=self._pick_move(state, belief, barriers),
            barrier_cell=self._pick_barrier(state, belief, barriers),
        )

    def _pick_move(self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]) -> Direction:
        raise NotImplementedError

    def _pick_barrier(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Cell | None:
        return None
