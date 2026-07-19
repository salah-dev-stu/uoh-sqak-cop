"""Strategy seam (F8): the MOVE is always pure Python; the LLM only fills text.

``_pick_move`` (direction) and ``_decide_move`` (full decision incl. any
barrier) are the graded hooks. ``Decision.intent`` — ``"truth"``/``"lie"`` — is
the bluff flag bound into the commit (PLAN §8.1); the ``hint`` text is written
later by the trash-talk layer, never here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState


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
        return self._decide_move(state, belief, barriers)

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
