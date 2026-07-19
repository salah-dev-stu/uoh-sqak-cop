"""HerderCop — herd the thief into a corner, then wall it in (WB §4).

The lab proved co-location never catches a competent evader; boxing does. So:
(1) HERD — approach from the anti-corner side (target the cell just beyond the
thief, away from its nearest corner) so its best escapes shrink toward the
corner; (2) BOX — once the thief is near a wall and we are close, hug it and
spend barriers on its escape cells (reachability min-cut). Barrier discipline:
hold fire until close AND near a boundary — never waste the budget early.
"""

from __future__ import annotations

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import BrainBase
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import can_place_barrier, reachable_cells


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


class HerderCop(BrainBase):
    role = "police"

    def _nearest_corner(self, cell: Cell) -> Cell:
        last = self.board.size - 1
        return (0 if cell[0] <= last // 2 else last, 0 if cell[1] <= last // 2 else last)

    def _wall_dist(self, cell: Cell) -> int:
        last = self.board.size - 1
        return min(cell[0], last - cell[0], cell[1], last - cell[1])

    def _chase_point(self, thief: Cell) -> Cell:
        overshoot = int(self.param("herd_overshoot", 1))
        if not overshoot:
            return thief  # direct pursuit variant
        corner = self._nearest_corner(thief)
        # the overshoot points inward (away from the nearest corner) — always on-board
        return (thief[0] + _sign(thief[0] - corner[0]) * overshoot,
                thief[1] + _sign(thief[1] - corner[1]) * overshoot)

    def _boxing(self, thief: Cell, me: Cell) -> bool:
        return (self._wall_dist(thief) <= int(self.param("box_wall_k", 1))
                and self.board.distance(me, thief) <= int(self.param("box_dist", 3)))

    def _pick_move(self, state: OwnState, belief: BeliefGrid,
                   barriers: frozenset[Cell]) -> Direction:
        thief = belief.most_likely()
        goal = thief if self._boxing(thief, state.position) else self._chase_point(thief)
        best_dir, best = Direction.STAY, float("inf")
        for direction in self.board.legal_moves(state.position, barriers):
            target = self.board.target_of(state.position, direction)
            score = self.board.distance(target, goal)
            if score < best:
                best_dir, best = direction, score
        return best_dir

    def _pick_barrier(self, state: OwnState, belief: BeliefGrid,
                      barriers: frozenset[Cell]) -> Cell | None:
        thief = belief.most_likely()
        close = self.board.distance(state.position, thief) <= int(self.param("fire_dist", 3))
        if not close or self._wall_dist(thief) > int(self.param("near_wall_k", 2)):
            return None  # discipline: hold fire until the endgame
        reach0 = len(reachable_cells(self.board, thief, barriers))
        best_q, best = None, float("-inf")
        for q in sorted(self.board.neighbors(state.position, frozenset())):
            if not can_place_barrier(self.board, state.position, q, barriers,
                                     int(self.param("max_barriers", 14))):
                continue
            gain = reach0 - len(reachable_cells(self.board, thief, barriers | {q}))
            score = gain - self.param("lambda_barrier", 0.2) * self.board.distance(q, thief)
            if gain >= self.param("min_gain", 1.0) and score > best:
                best_q, best = q, score
        return best_q
