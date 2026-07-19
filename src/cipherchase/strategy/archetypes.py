"""Opponent archetype brains (WB §6) — the benchmark opponents.

Models of what league opponents will realistically field: the reference's
placeholder edge-runner, a random walker, and a statue. Also used by tests.
"""

from __future__ import annotations

import random

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import BrainBase
from cipherchase.domain.own_state import OwnState


class NaiveEdgeThief(BrainBase):
    """Runs for the corner farthest from the believed cop (reference-style)."""

    role = "thief"

    def _pick_move(self, state: OwnState, belief: BeliefGrid,
                   barriers: frozenset[Cell]) -> Direction:
        cop = belief.most_likely()
        last = self.board.size - 1
        corners = [(0, 0), (0, last), (last, 0), (last, last)]
        goal = max(corners, key=lambda c: self.board.distance(c, cop))
        best_dir, best = Direction.STAY, float("inf")
        for direction in self.board.legal_moves(state.position, barriers):
            target = self.board.target_of(state.position, direction)
            if self.board.distance(target, goal) < best:
                best_dir, best = direction, self.board.distance(target, goal)
        return best_dir


class RandomThief(BrainBase):
    """Uniform random legal move (seeded)."""

    role = "thief"

    def _pick_move(self, state: OwnState, belief: BeliefGrid,
                   barriers: frozenset[Cell]) -> Direction:
        rng = self.rng or random.Random(0)
        return rng.choice(self.board.legal_moves(state.position, barriers))


class StillThief(BrainBase):
    """Never moves — the lower bound any cop must beat."""

    role = "thief"

    def _pick_move(self, state: OwnState, belief: BeliefGrid,
                   barriers: frozenset[Cell]) -> Direction:
        return Direction.STAY
