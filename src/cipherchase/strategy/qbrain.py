"""Tabular Q-learning cop (FR-C5, the learning seam) — pure Python (F8).

A deliberately small, legible RL brain: the state is the thief's position relative
to the cop, clamped to a 7×7 window (49 states); the action is one of the five
moves. A policy trained offline (`scripts/train_qbrain.py` → `analysis/qbrain_policy.json`)
is looked up per turn; any unseen state or illegal suggestion falls back to the
proven greedy pursuit of `PoliceBrain`. Shipped as a comparison to `ApexCop`, not
as the champion — the learning curve is the artifact (README §4).
"""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.constants import Cell, Direction
from cipherchase.strategy.police_heuristic import PoliceBrain

MOVES = (Direction.N, Direction.S, Direction.E, Direction.W, Direction.STAY)
_SPAN = 3
N_STATES = (2 * _SPAN + 1) ** 2


def encode_state(cop: Cell, thief: Cell, board) -> int:
    dr = max(-_SPAN, min(_SPAN, thief[0] - cop[0])) + _SPAN
    dc = max(-_SPAN, min(_SPAN, thief[1] - cop[1])) + _SPAN
    return dr * (2 * _SPAN + 1) + dc


class QBrain(PoliceBrain):
    def __init__(self, board, params=None, rng=None) -> None:
        super().__init__(board, params, rng)
        self.policy = self._load_policy()

    def _load_policy(self) -> list[int]:
        if self.params.get("policy") is not None:
            return list(self.params["policy"])
        path = self.params.get("qbrain_policy_path")
        if path and Path(path).exists():
            return list(json.loads(Path(path).read_text())["policy"])
        return []

    def _pick_move(self, state, belief, barriers) -> Direction:
        thief = belief.most_likely()
        idx = encode_state(state.position, thief, self.board)
        legal = self.board.legal_moves(state.position, barriers)
        if idx < len(self.policy):
            action = MOVES[self.policy[idx]]
            if action in legal:
                return action
        return super()._pick_move(state, belief, barriers)  # greedy fallback (F8-safe)
