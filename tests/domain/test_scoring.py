"""Config-driven scoring table (FR-A5)."""

from __future__ import annotations

import pytest

from cipherchase.constants import Outcome
from cipherchase.domain.scoring import Scoring

TABLE = {
    "capture_cop": 20,
    "capture_thief": 5,
    "survival_cop": 5,
    "survival_thief": 10,
    "tie_score": 2,
    "technical_loss": 0,
    "diversity_reward": 10,
}
S = Scoring(TABLE)


def test_capture_scores_cop_high() -> None:
    assert S.score(Outcome.CAPTURE) == (20, 5)


def test_survival_scores_thief_high() -> None:
    assert S.score(Outcome.SURVIVAL) == (5, 10)


def test_tie_is_symmetric() -> None:
    assert S.score(Outcome.TIE) == (2, 2)


def test_technical_loss_is_zero_zero() -> None:
    assert S.score(Outcome.TECHNICAL_LOSS) == (0, 0)
    assert S.technical_loss() == (0, 0)


def test_diversity_reward_goes_to_winner_vs_new_opponent() -> None:
    # New opponent: capture → cop is the winner, gets +10.
    assert S.score(Outcome.CAPTURE, new_opponent=True) == (30, 5)
    # Survival → thief winner gets +10.
    assert S.score(Outcome.SURVIVAL, new_opponent=True) == (5, 20)
    # Tie has no winner → no diversity bonus.
    assert S.score(Outcome.TIE, new_opponent=True) == (2, 2)


def test_unknown_outcome_rejected() -> None:
    with pytest.raises(KeyError):
        S.score("not-an-outcome")  # type: ignore[arg-type]


def test_score_is_config_driven_not_hardcoded() -> None:
    # A mutated table changes the result → proves no literals (NFR-11).
    mutated = {**TABLE, "capture_cop": 99}
    assert Scoring(mutated).score(Outcome.CAPTURE) == (99, 5)
