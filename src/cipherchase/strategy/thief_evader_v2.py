"""EvaderBrain — survival by ROOM, not by distance (WB §5).

Maximising distance from the cop is the intuitive evader and it loses: on any
board the farthest cell is a corner, and a corner is the fewest exits and the
cheapest enclosure. Our thief sprinted to (6,6), then STAYed — leaving cost a
point of distance and gained only a fraction back in exits — until the cop
walked over and sealed it with two barriers. Three sub-games, three identical
13-step losses against imreeyal.

So the objective is the escape region: cells this thief reaches strictly before
the cop can, which collapses in a corner exactly when the cop closes and stays
large in open ground. Distance survives only as a tiebreak. Still pure Python,
still seeded-random among near-ties so an intercept predictor cannot read us.
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
            + self.param("w_exits", 1.0) * exits  # measured: 0.3 -> 1.0 doubles survival
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
        # Standing still is never preferred on a tie. In the far corner the score
        # for STAY and for stepping off is exactly equal at w_exits 1.0, and a
        # thief that flips a coin on that eventually parks — which is how a cop
        # gets the free tempo to seal a two-exit cell with two barriers.
        moving = [d for d in near_ties if d is not Direction.STAY]
        rng = self.rng or random.Random(0)
        return rng.choice(moving or near_ties)
