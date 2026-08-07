"""PoliceBrain — pursue the believed thief and place barriers that box it in.

Pure Python (F8). The move greedily reduces Manhattan distance to the belief
peak; the barrier is the adjacent, legal placement that most shrinks the
thief's reachable set (min-cut intuition), discounted by distance to it.
"""

from __future__ import annotations

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import BrainBase
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import can_place_barrier, reachable_cells


class PoliceBrain(BrainBase):
    role = "police"


    def _move_score(self, target: Cell, thief: Cell, belief: BeliefGrid) -> float:
        center = (self.board.size // 2, self.board.size // 2)
        return (
            -self.param("w_dist", 1.0) * self.board.distance(target, thief)
            - self.param("w_center", 0.5) * self.board.distance(target, center)
            + self.param("w_belief", 1.0) * belief.mass_at(target)
        )

    def _pick_move(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Direction:
        thief = belief.most_likely()
        best_dir, best = Direction.STAY, float("-inf")
        for direction in self.board.legal_moves(state.position, barriers):
            score = self._move_score(self.board.target_of(state.position, direction), thief, belief)
            if score > best:
                best_dir, best = direction, score
        return best_dir

    def _candidates(self, cop: Cell, barriers: frozenset[Cell]) -> list[Cell]:
        max_b = int(self.params.get("max_barriers", 14))
        adjacent = self.board.neighbors(cop, frozenset())
        return [q for q in adjacent if can_place_barrier(self.board, cop, q, barriers, max_b)]

    def _pick_barrier(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Cell | None:
        thief = belief.most_likely()
        reach0 = len(reachable_cells(self.board, thief, barriers))
        best_q: Cell | None = None
        best = float("-inf")
        for q in sorted(self._candidates(state.position, barriers)):
            gain = reach0 - len(reachable_cells(self.board, thief, barriers | {q}))
            score = gain - self.param("lambda_barrier", 0.2) * self.board.distance(q, thief)
            # A wall costs a turn, so it must do more than delete one cell.
            if gain >= self.param("min_gain", 2.0) and score > best:
                best_q, best = q, score
        return best_q
