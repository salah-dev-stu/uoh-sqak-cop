"""ApexCop — the championship pursuer (AB-1,2,6..15). Pure Python (F8).

Three layers, safest first:
  L3 ENDGAME  — when the belief is *locked* and the thief sits near a wall, run
                the exact solver; if it proves a forced capture, play that line.
  L2 BEST-RESPONSE — otherwise pick the (move, barrier) minimising the thief's
                worst-case escape value over ITS own predicted replies.
  L1 BELIEF   — the peak of the decoder-sharpened belief is the thief estimate.
``last_layer`` records which fired (HUD/replay telemetry, not a test hook).
"""

from __future__ import annotations

from cipherchase.constants import Cell, Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.brains import Decision
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import reachable_cells
from cipherchase.strategy.endgame import EndgameSolver, endgame_trigger, wall_dist
from cipherchase.strategy.opponent_model import OpponentModel
from cipherchase.strategy.police_heuristic import PoliceBrain


def escape_value(board, cop, thief, barriers, w_reach, w_dist, w_wall) -> float:
    """How free the thief is: reachable area + gap to cop + room from walls."""
    reach = len(reachable_cells(board, thief, barriers))
    return (w_reach * reach + w_dist * board.distance(cop, thief)
            + w_wall * wall_dist(board, thief))


class ApexCop(PoliceBrain):
    def __init__(self, board, params=None, rng=None) -> None:
        super().__init__(board, params, rng)
        self.model = OpponentModel(
            self.params.get("opponent_model", "thief_v1"), board, self.params, rng)
        self._solver = EndgameSolver(
            board,
            depth=int(self.param("apex_endgame_depth", 8)),
            nodes=int(self.param("apex_endgame_nodes", 50_000)),
            survival_threshold=int(self.param("survival_threshold", 35)))
        self.last_layer = "best_response"

    def _weights(self) -> tuple[float, float, float]:
        return (self.param("apex_w_reach", 1.0),
                self.param("apex_w_dist", 0.6), self.param("apex_w_wall", 0.8))

    def _worst_escape(self, cop: Cell, thief: Cell, barriers: frozenset[Cell]) -> float:
        w = self._weights()
        replies = self.model.predict(thief, cop, barriers)
        return max(escape_value(self.board, cop, r, barriers, *w) for r in replies)

    def _topk_barriers(self, cop, thief, barriers) -> list[Cell]:
        k = int(self.param("apex_barrier_topk", 3))
        if k <= 0:
            return []
        reach0 = len(reachable_cells(self.board, thief, barriers))
        scored = []
        for q in self._candidates(cop, barriers):
            gain = reach0 - len(reachable_cells(self.board, thief, barriers | {q}))
            # A wall costs a turn, so it must do more than delete one cell.
            if gain >= self.param("min_gain", 2.0):
                scored.append((gain, q))
        scored.sort(key=lambda gq: (-gq[0], gq[1]))
        return [q for _, q in scored[:k]]

    def _best_response(self, cop, thief, barriers) -> tuple[Direction, Cell | None]:
        """Best legal action: EITHER a step OR a wall, never both (ch.3).

        The Barrier Law prices the wall in tempo, so the two are genuinely
        alternatives and the search has to compare them as such. Evaluating
        move-and-wall together searched a game we were not entitled to play, and
        chose a wall on almost every turn because it never cost anything.
        """
        best: tuple[Direction, Cell | None] = (Direction.STAY, None)
        best_val = float("inf")
        cost = self.param("apex_barrier_cost", 0.0)
        for move in self.board.legal_moves(cop, barriers):  # step, no wall
            val = self._worst_escape(self.board.target_of(cop, move), thief, barriers)
            if val < best_val:
                best_val, best = val, (move, None)
        for q in self._topk_barriers(cop, thief, barriers):  # wall, forgoing the step
            val = self._worst_escape(cop, thief, barriers | {q}) + cost
            if val < best_val:
                best_val, best = val, (Direction.STAY, q)
        return best

    def _decide_move(
        self, state: OwnState, belief: BeliefGrid, barriers: frozenset[Cell]
    ) -> Decision:
        thief = belief.most_likely()
        locked = belief.mass_at(thief) >= self.param("apex_lock_mass", 0.5)
        if locked and endgame_trigger(
            self.board, state.position, thief,
            wall_k=int(self.param("apex_endgame_wall", 2)),
            gap_max=int(self.param("apex_endgame_gap", 4)),
        ):
            line = self._solver.solve(cop=state.position, thief=thief, barriers=barriers, ply=0)
            if line is not None:
                self.last_layer = "endgame"
                return Decision(direction=line.action[0], barrier_cell=line.action[1])
        self.last_layer = "best_response"
        move, q = self._best_response(state.position, thief, barriers)
        return Decision(direction=move, barrier_cell=q)

    def _pick_move(self, state, belief, barriers) -> Direction:
        return self._decide_move(state, belief, barriers).direction

    def _pick_barrier(self, state, belief, barriers) -> Cell | None:
        return self._decide_move(state, belief, barriers).barrier_cell
