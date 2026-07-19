"""Predict the opponent's reply by running ITS rule, not ours (AB-3..AB-5).

The decoder gives the thief's exact cell; the cop is only as good as its model
of the thief's next move. We possess the archetype/evader decision rules, so we
interrogate the *real* brain (no duplicated scoring, R2). Deterministic models
give a single reply; EvaderV2's seeded near-ties give the whole tie set
(support-exact); ``paranoid`` returns every legal reply (league-safe minimax).
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Cell
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.exceptions import ConfigError
from cipherchase.strategy.factory import load_brain

_PKG = "cipherchase.strategy"
_MODELS = {
    "thief_v1": f"{_PKG}.thief_heuristic:ThiefBrain",
    "naive_edge": f"{_PKG}.archetypes:NaiveEdgeThief",
    "evader_v2": f"{_PKG}.thief_evader_v2:EvaderBrain",
}
_RULELESS = {"paranoid", "random", "still"}
_ENSEMBLE = ("thief_v1", "naive_edge", "still")


class _FixedBelief:
    """Minimal belief whose peak is a fixed cell — enough for any thief brain."""

    def __init__(self, cell: Cell) -> None:
        self._cell = cell

    def most_likely(self) -> Cell:
        return self._cell

    def mass_at(self, cell: Cell) -> float:
        return 1.0 if cell == self._cell else 0.0


class OpponentModel:
    def __init__(self, name: str, board: Board, params: dict[str, Any], rng: Any = None) -> None:
        if name not in _MODELS and name not in _RULELESS and name != "ensemble":
            raise ConfigError(f"unknown opponent model {name!r}")
        self.name = name
        self.board = board
        self.members = ([OpponentModel(m, board, params, rng) for m in _ENSEMBLE]
                        if name == "ensemble" else [])
        self.brain = load_brain(_MODELS[name], board, params, rng) if name in _MODELS else None

    def _legal_targets(self, thief: Cell, barriers: frozenset[Cell]) -> set[Cell]:
        return {self.board.target_of(thief, d)
                for d in self.board.legal_moves(thief, barriers)}

    def predict(self, thief: Cell, cop: Cell, barriers: frozenset[Cell]) -> set[Cell]:
        if self.name == "ensemble":
            return set().union(*(m.predict(thief, cop, barriers) for m in self.members))
        if self.name in ("paranoid", "random"):
            return self._legal_targets(thief, barriers)
        if self.name == "still":
            return {thief}
        if self.name == "evader_v2":
            eps = self.brain.param("tie_epsilon", 0.25)
            scored = {t: self.brain._score(t, cop, barriers)
                      for t in self._legal_targets(thief, barriers)}
            best = max(scored.values())
            return {t for t, s in scored.items() if s >= best - eps}
        direction = self.brain._pick_move(OwnState("thief", thief), _FixedBelief(cop), barriers)
        return {self.board.target_of(thief, direction)}
