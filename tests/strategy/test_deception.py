"""Strategic bluffing (F6/F8): a pure RULE decides when to lie, never the LLM."""

from __future__ import annotations

from cipherchase.domain.board import Board
from cipherchase.strategy.deception import should_bluff

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_cop_bluffs_only_when_it_has_closed_the_gap() -> None:
    # Close in → feign "I've lost your trail" to bait the thief into relaxing.
    assert should_bluff("police", (3, 3), (3, 5), EMPTY, B, gap_threshold=3)  # gap 2
    assert not should_bluff("police", (0, 0), (6, 6), EMPTY, B, gap_threshold=3)  # gap 12


def test_cop_gap_threshold_is_inclusive_and_configurable() -> None:
    assert should_bluff("police", (0, 0), (0, 3), EMPTY, B, gap_threshold=3)  # gap 3 == thr
    assert not should_bluff("police", (0, 0), (0, 4), EMPTY, B, gap_threshold=3)  # gap 4


def test_thief_bluffs_only_when_cornered() -> None:
    # One escape left (walls + board edge) → misdirect. Corner (0,0), cop at (0,1),
    # barrier at (1,0) leaves no escape → cornered → bluff.
    barriers = frozenset({(1, 0)})
    assert should_bluff("thief", (0, 1), (0, 0), barriers, B)
    # Open centre: four escapes → tell the truth (nothing to hide).
    assert not should_bluff("thief", (5, 5), (3, 3), EMPTY, B)


def test_thief_with_a_single_open_escape_still_bluffs() -> None:
    # Edge cell (0,3) with cop adjacent removing one neighbour and walls pinning the
    # rest → at most one escape → cornered.
    barriers = frozenset({(0, 2), (1, 3)})
    assert should_bluff("thief", (0, 4), (0, 3), barriers, B)


def test_unknown_role_never_bluffs() -> None:
    assert not should_bluff("spectator", (0, 0), (0, 1), EMPTY, B)
