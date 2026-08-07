"""The evader must not walk into a corner and wait to die (imreeyal friendly).

Maximising distance from the cop puts the far corner top of the list on every
board — and the far corner is the cell with the fewest exits and the cheapest
enclosure. Our thief sprinted to (6,6) in six moves and then STAYed for seven
turns while the cop walked over and sealed it with two barriers: three sub-games,
three identical 13-step losses.

Distance is the wrong objective. What a thief needs is ROOM — the cells it can
still reach before the cop can cut them off — with distance only as a tiebreak.
"""

from __future__ import annotations

import random

from cipherchase.constants import Direction
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.thief_evader_v2 import EvaderBrain

B = Board(7)
EMPTY: frozenset = frozenset()


class _Belief:
    """A belief pinned to one cell — the cop's position, as the thief sees it."""

    def __init__(self, cell): self.cell = cell
    def most_likely(self): return self.cell


def _brain(**params) -> EvaderBrain:
    return EvaderBrain(B, params={"max_barriers": 14, **params}, rng=random.Random(0))


def test_the_thief_leaves_the_corner_instead_of_waiting_in_it() -> None:
    # The exact losing position: thief in the far corner, cop still distant.
    brain = _brain()
    for _ in range(8):  # not a lucky tie-break — every time
        move = brain._pick_move(OwnState("thief", (6, 6)), _Belief((3, 3)), EMPTY)
        assert move is not Direction.STAY, "sitting in a 2-exit corner is forfeiting"


def test_open_ground_beats_an_edge_at_equal_distance() -> None:
    # Both cells are exactly 6 from a cop at (3,0), so distance cannot separate
    # them: (1,4) is interior with four exits, (3,6) is against the wall with
    # three. Room and mobility must break the tie, not luck.
    brain = _brain()
    assert B.distance((1, 4), (3, 0)) == B.distance((3, 6), (3, 0)) == 6
    assert brain._score((1, 4), (3, 0), EMPTY) > brain._score((3, 6), (3, 0), EMPTY)


def test_it_never_steps_within_reach_of_the_cop_when_it_can_avoid_it() -> None:
    # Cop at (3,2); stepping to (3,3) is suicide, the cop simply moves onto us.
    brain = _brain()
    move = brain._pick_move(OwnState("thief", (3, 4)), _Belief((3, 2)), EMPTY)
    assert B.target_of((3, 4), move) != (3, 3)


def test_standing_still_never_wins_a_tie() -> None:
    # At the measured weight the corner and the step off it score EXACTLY equal,
    # so a coin-flip tie-break eventually parks the thief — and a stationary
    # thief hands the cop the free tempo to seal a two-exit cell with two
    # barriers. Moving wins every tie; the randomisation stays among real moves.
    brain = _brain()
    corner, step_off = (6, 6), (5, 6)
    assert brain._score(corner, (3, 3), EMPTY) == brain._score(step_off, (3, 3), EMPTY)
    for seed in range(6):
        b = EvaderBrain(B, params={"max_barriers": 14}, rng=random.Random(seed))
        assert b._pick_move(OwnState("thief", corner), _Belief((3, 3)), EMPTY) \
            is not Direction.STAY
