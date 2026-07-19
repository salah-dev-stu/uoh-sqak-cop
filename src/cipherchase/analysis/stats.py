"""Statistical honesty for benchmark & league evidence — no hand-waving %.

``wilson_interval`` is the score interval for a binomial proportion: unlike the
normal approximation it stays inside [0, 1] and behaves at the 0/N and N/N
extremes, so "100% (60/60)" is reported as strong-but-not-certain. ``elo_update``
is the standard logistic rating step used by the league ladder.
"""

from __future__ import annotations

import math


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95%-default Wilson score interval for ``successes`` out of ``n`` trials."""
    if n == 0:
        return (0.0, 1.0)
    phat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (phat + z2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def _expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def elo_update(
    rating_a: float, rating_b: float, *, winner_first: bool, k: float = 16.0
) -> tuple[float, float]:
    """Return updated (rating_a, rating_b); ``winner_first`` marks A as the winner."""
    score_a = 1.0 if winner_first else 0.0
    exp_a = _expected(rating_a, rating_b)
    delta = k * (score_a - exp_a)
    return (rating_a + delta, rating_b - delta)
