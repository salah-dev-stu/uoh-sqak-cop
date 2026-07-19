"""Bluff-aware hint fusion (F6/F7): opponent words nudge belief, honesty-scaled."""

from __future__ import annotations

import pytest

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.hint_belief import HonestyTracker, apply_hint, extract_claim


def test_extract_claim_reads_a_cardinal_word() -> None:
    assert extract_claim("Heading north, promise.") is Direction.N
    assert extract_claim("I'm slipping east now") is Direction.E
    assert extract_claim("Catch me if you can!") is None  # no spatial content


def test_honesty_tracker_is_a_beta_posterior() -> None:
    t = HonestyTracker()
    assert t.p_honest() == pytest.approx(0.5)  # Beta(1,1) prior
    t.record(True)
    t.record(True)
    t.record(False)
    assert t.p_honest() == pytest.approx(3 / 5)  # (1+2)/(2+3)


def test_trusted_hint_boosts_the_claimed_direction() -> None:
    belief = BeliefGrid(7)
    honest = 0.95
    apply_hint(belief, (3, 3), Direction.N, honest, bluff_weight=0.15, board_size=7)
    # N = decreasing row: cells above (3,3) gain relative to cells below.
    assert belief.mass_at((1, 3)) > belief.mass_at((5, 3))


def test_distrusted_hint_suppresses_the_claimed_direction() -> None:
    belief = BeliefGrid(7)
    apply_hint(belief, (3, 3), Direction.N, 0.05, bluff_weight=0.15, board_size=7)
    assert belief.mass_at((1, 3)) < belief.mass_at((5, 3))  # known liar → don't chase north


def test_neutral_honesty_or_zero_weight_is_a_no_op() -> None:
    for honest, weight in ((0.5, 0.15), (0.99, 0.0)):
        belief = BeliefGrid(7)
        before = belief.as_matrix()
        apply_hint(belief, (3, 3), Direction.N, honest, bluff_weight=weight, board_size=7)
        assert belief.as_matrix() == before


def test_no_claim_leaves_belief_untouched() -> None:
    belief = BeliefGrid(7)
    before = belief.as_matrix()
    apply_hint(belief, (3, 3), None, 0.9, bluff_weight=0.15, board_size=7)
    assert belief.as_matrix() == before
