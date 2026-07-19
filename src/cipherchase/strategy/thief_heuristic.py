"""ThiefBrain — evade the believed cop, keep escape routes open (FR-C3).

Pure Python (F8). Scores each legal move by distance from the believed cop
plus the number of onward exits, penalising cells adjacent to the cop; ties
break by the frozen move order for reproducible replays.
"""

from __future__ import annotations

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import BrainBase
from cipherchase.domain.own_state import OwnState


class ThiefBrain(BrainBase):
    role = "thief"


    def _score(self, target: Cell, cop: Cell, barriers: frozenset[Cell]) -> float:
        dist = self.board.distance(target, cop)
        exits = len(self.board.neighbors(target, barriers))
        risk = 1.0 if dist <= 1 else 0.0
        return (
            self.param("w_dist", 1.0) * dist
            + self.param("w_exits", 0.3) * exits
            - self.param("w_risk", 1.0) * risk
        )

    def _pick_move(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Direction:
        cop = belief.most_likely()
        best_dir = Direction.STAY
        best_score = float("-inf")
        for direction in self.board.legal_moves(state.position, barriers):
            target = self.board.target_of(state.position, direction)
            score = self._score(target, cop, barriers)
            if score > best_score:
                best_dir, best_score = direction, score
        return best_dir
