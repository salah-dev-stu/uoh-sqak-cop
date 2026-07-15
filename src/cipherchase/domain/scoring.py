"""Config-driven scoring (FR-A5). All point values come from ``game.json``."""

from __future__ import annotations

from collections.abc import Mapping

from cipherchase.constants import Outcome

# Which side (if any) wins each terminal outcome — earns the diversity bonus.
_WINNER = {Outcome.CAPTURE: "cop", Outcome.SURVIVAL: "thief"}


class Scoring:
    """Maps a terminal :class:`Outcome` to a ``(cop, thief)`` score pair."""

    def __init__(self, table: Mapping[str, int]) -> None:
        self._table = dict(table)

    def technical_loss(self) -> tuple[int, int]:
        loss = self._table["technical_loss"]
        return (loss, loss)

    def score(self, outcome: Outcome, *, new_opponent: bool = False) -> tuple[int, int]:
        cop, thief = self._base(outcome)
        if new_opponent:
            bonus = self._table["diversity_reward"]
            if _WINNER.get(outcome) == "cop":
                cop += bonus
            elif _WINNER.get(outcome) == "thief":
                thief += bonus
        return (cop, thief)

    def _base(self, outcome: Outcome) -> tuple[int, int]:
        if outcome is Outcome.CAPTURE:
            return (self._table["capture_cop"], self._table["capture_thief"])
        if outcome is Outcome.SURVIVAL:
            return (self._table["survival_cop"], self._table["survival_thief"])
        if outcome is Outcome.TIE:
            tie = self._table["tie_score"]
            return (tie, tie)
        if outcome is Outcome.TECHNICAL_LOSS:
            return self.technical_loss()
        raise KeyError(outcome)
