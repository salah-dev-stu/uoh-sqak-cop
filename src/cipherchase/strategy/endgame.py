"""Exact endgame solver (AB-8..AB-11) — the cornered game is finite; solve it.

Depth-bounded alpha-beta over TRUE positions with the thief playing ALL legal
replies (a guarantee, not a prediction). Returns the first action of a forced
capture line iff the root proves capture within the horizon against every reply,
else None → the caller falls back to L2 (never stalls a live turn). Hard depth +
node caps make "unproven" the safe answer; a per-turn memo table bounds cost.
"""

from __future__ import annotations

from dataclasses import dataclass

from cipherchase.constants import Cell, Direction
from cipherchase.domain.board import Board
from cipherchase.domain.rules import can_place_barrier, is_capture

_WIN = 10_000


def wall_dist(board: Board, cell: Cell) -> int:
    last = board.size - 1
    return min(cell[0], last - cell[0], cell[1], last - cell[1])


def endgame_trigger(board: Board, cop: Cell, thief: Cell, *, wall_k: int, gap_max: int) -> bool:
    return wall_dist(board, thief) <= wall_k and board.distance(cop, thief) <= gap_max


@dataclass
class Line:
    action: tuple[Direction, Cell | None]
    value: int


class EndgameSolver:
    def __init__(self, board: Board, *, depth: int, nodes: int, survival_threshold: int) -> None:
        self.board = board
        self.depth = depth
        self.node_cap = nodes
        self.survival = survival_threshold
        self.nodes_used = 0
        self._memo: dict = {}

    def solve(self, *, cop: Cell, thief: Cell, barriers: frozenset[Cell], ply: int) -> Line | None:
        self.nodes_used = 0
        self._memo = {}
        best: Line | None = None
        alpha = -_WIN - 1
        for move, q in self._cop_actions(cop, barriers):
            b2 = barriers | ({q} if q else frozenset())
            new_cop = self.board.step(cop, move, b2)
            value = self._min_thief(new_cop, thief, b2, ply + 1, alpha, _WIN + 1)
            if value > alpha:
                alpha, best = value, Line((move, q), value)
        return best if best and best.value > 0 else None

    def _cop_actions(self, cop: Cell, barriers: frozenset[Cell]):
        adjacent = self.board.neighbors(cop, frozenset())
        walls = [q for q in sorted(adjacent) if can_place_barrier(self.board, cop, q, barriers, 14)]
        for move in self.board.legal_moves(cop, barriers):
            yield move, None
            for q in walls:
                if self.board.target_of(cop, move) != q:
                    yield move, q

    def _max_cop(self, cop, thief, barriers, ply, alpha, beta):
        if self.nodes_used >= self.node_cap or ply >= self.depth:
            return 0
        best = -_WIN - 1
        for move, q in self._cop_actions(cop, barriers):
            b2 = barriers | ({q} if q else frozenset())
            value = self._min_thief(self.board.step(cop, move, b2), thief, b2, ply + 1, alpha, beta)
            best = max(best, value)
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best

    def _min_thief(self, cop, thief, barriers, ply, alpha, beta):
        self.nodes_used += 1
        if is_capture(self.board, cop, thief, barriers):
            return _WIN - ply
        if ply >= 2 * self.depth or ply // 2 >= self.survival or self.nodes_used >= self.node_cap:
            return 0
        key = (cop, thief, barriers, ply)
        if key in self._memo:
            return self._memo[key]
        worst = _WIN + 1
        for direction in self.board.legal_moves(thief, barriers):
            reply = self.board.step(thief, direction, barriers)
            value = self._max_cop(cop, reply, barriers, ply + 1, alpha, beta)
            worst = min(worst, value)
            beta = min(beta, worst)
            if alpha >= beta:
                break
        self._memo[key] = worst
        return worst
