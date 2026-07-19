"""EvaderBrain v2 — corner-aware, unpredictable survival (WB §5).

Adds to the v1 evader: a REACHABILITY term (never walk into a shrinking
region — the herder's whole plan), and seeded randomization among near-tied
moves so intercept-style predictors can't read us. Still pure Python.
"""

from __future__ import annotations

import random

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import BrainBase
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import reachable_cells


class EvaderBrain(BrainBase):
    role = "thief"

    def _score(self, target: Cell, cop: Cell, barriers: frozenset[Cell]) -> float:
        dist = self.board.distance(target, cop)
        exits = len(self.board.neighbors(target, barriers))
        reach = len(reachable_cells(self.board, target, barriers))
        risk = 1.0 if dist <= 1 else 0.0
        return (
            self.param("w_dist", 1.0) * dist
            + self.param("w_exits", 0.3) * exits
            + self.param("w_reach", 0.15) * reach
            - self.param("w_risk", 3.0) * risk
        )

    def _pick_move(self, state: OwnState, belief: BeliefGrid,
                   barriers: frozenset[Cell]) -> Direction:
        cop = belief.most_likely()
        scored: list[tuple[float, Direction]] = []
        for direction in self.board.legal_moves(state.position, barriers):
            target = self.board.target_of(state.position, direction)
            scored.append((self._score(target, cop, barriers), direction))
        best = max(score for score, _ in scored)
        eps = self.param("tie_epsilon", 0.25)
        near_ties = [direction for score, direction in scored if best - score <= eps]
        rng = self.rng or random.Random(0)
        return rng.choice(near_ties)
