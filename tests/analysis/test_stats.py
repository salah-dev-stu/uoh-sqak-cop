"""Statistical honesty for the win-rate evidence (Wilson CI + Elo)."""

from __future__ import annotations

import math

from cipherchase.analysis.stats import elo_update, wilson_interval


def test_wilson_brackets_the_point_estimate() -> None:
    lo, hi = wilson_interval(30, 60)  # 50%
    assert lo < 0.5 < hi
    assert 0.0 <= lo < hi <= 1.0


def test_wilson_perfect_score_stays_below_one_but_high() -> None:
    lo, hi = wilson_interval(60, 60)  # 100% observed — CI must not claim certainty
    assert hi == 1.0 or math.isclose(hi, 1.0)
    assert lo < 1.0  # honest: a perfect sample is not a proof
    assert lo > 0.9  # 60/60 is still strong evidence


def test_wilson_zero_events_is_a_degenerate_but_valid_interval() -> None:
    lo, hi = wilson_interval(0, 0)
    assert (lo, hi) == (0.0, 1.0)  # no data → total ignorance, never a crash


def test_wilson_more_data_tightens_the_interval() -> None:
    narrow = wilson_interval(50, 100)
    wide = wilson_interval(5, 10)  # same 50%, less data
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_elo_winner_gains_what_loser_loses() -> None:
    new_w, new_l = elo_update(1000, 1000, winner_first=True, k=16)
    assert new_w > 1000 > new_l
    assert math.isclose((new_w - 1000), (1000 - new_l))
    assert math.isclose(new_w - 1000, 8.0)  # even match, K=16 → ±K/2


def test_elo_upset_moves_more_than_expected_win() -> None:
    underdog_win, _ = elo_update(1000, 1400, winner_first=True, k=16)
    favourite_win, _ = elo_update(1400, 1000, winner_first=True, k=16)
    assert (underdog_win - 1000) > (favourite_win - 1400)
