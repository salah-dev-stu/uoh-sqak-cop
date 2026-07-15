"""Reachability-minimizing cop (FR-C5, excellence — behind the BrainBase seam).

Where the heuristic cop chases by Manhattan distance, this one jointly picks its
move AND barrier to minimise the thief's *reachable-set size* (a 1-ply
adversarial evaluation), systematically shrinking the thief's space until it is
boxed in — turning containment into capture. Still pure Python, zero tokens.
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Cell
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import Decision
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import reachable_cells
from cipherchase.strategy.police_heuristic import PoliceBrain


class PoliceExpectimax(PoliceBrain):
    role = "police"

    def _eval(self, cop: Cell, thief: Cell, barriers: frozenset[Cell]) -> float:
        if cop == thief:
            return -1e9  # capture
        reach = len(reachable_cells(self.board, thief, barriers))
        return reach * 10.0 + self.board.distance(cop, thief)

    def _decide_move(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Decision:
        thief = belief.most_likely()
        best: tuple[Any, Cell | None] | None = None
        best_val = float("inf")
        candidates: list[Cell | None] = [None, *self._candidates(state.position, barriers)]
        for direction in self.board.legal_moves(state.position, barriers):
            new_pos = self.board.target_of(state.position, direction)
            for barrier in candidates:
                extra = {barrier} if barrier and barrier != new_pos else set()
                value = self._eval(new_pos, thief, barriers | extra)
                if value < best_val:
                    best_val, best = value, (direction, barrier if extra else None)
        direction, barrier = best  # type: ignore[misc]
        return Decision(direction=direction, barrier_cell=barrier)
