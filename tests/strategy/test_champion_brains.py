"""P2 champion brains: herder variant, evader v2, archetypes (WB §4-6)."""

from __future__ import annotations

import random

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.archetypes import NaiveEdgeThief, RandomThief, StillThief
from cipherchase.strategy.police_herder import HerderCop
from cipherchase.strategy.thief_evader_v2 import EvaderBrain

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def _belief_at(cell: tuple[int, int]) -> BeliefGrid:
    grid = BeliefGrid(7, smell_trust=1e6)
    grid.observe_smell({f"{cell[0]},{cell[1]}": 1.0})
    return grid


def test_herder_aims_beyond_the_thief_away_from_its_corner() -> None:
    brain = HerderCop(B)
    # thief at (5,5): nearest corner (6,6) → chase point (4,4) — approach anti-corner side
    assert brain._chase_point((5, 5)) == (4, 4)
    decision = brain.decide(OwnState("police", (2, 2)), _belief_at((5, 5)), EMPTY)
    assert decision.direction in B.legal_moves((2, 2), EMPTY)


def test_herder_barrier_discipline_holds_fire_when_far_or_central() -> None:
    brain = HerderCop(B)
    # far thief → no barrier even though placements exist
    assert brain._pick_barrier(OwnState("police", (0, 0)), _belief_at((6, 6)), EMPTY) is None
    # close but central thief → still holds (not near a wall)
    assert brain._pick_barrier(OwnState("police", (3, 2)), _belief_at((3, 3)), EMPTY) is None


def test_herder_boxes_a_cornered_thief_with_a_wall() -> None:
    brain = HerderCop(B)
    barrier = brain._pick_barrier(OwnState("police", (1, 1)), _belief_at((0, 0)), EMPTY)
    assert barrier in {(0, 1), (1, 0)}  # seals an escape of the cornered thief


def test_herder_variant_edges() -> None:
    direct = HerderCop(B, params={"herd_overshoot": 0})
    assert direct._chase_point((5, 5)) == (5, 5)  # direct-pursuit variant
    edge = HerderCop(B)
    assert edge._chase_point((6, 6)) == (6, 6)  # overshoot off-board → clamp to thief
    # boxing mode: cornered thief + adjacent cop → goal is the thief itself
    boxing = HerderCop(B)
    assert boxing._boxing((0, 0), (1, 1)) is True
    # a wall already placed blocks that candidate (can_place false branch)
    barrier = boxing._pick_barrier(OwnState("police", (1, 0)), _belief_at((0, 0)),
                                   frozenset({(0, 0)}))
    assert barrier != (0, 0)


def test_decoder_skips_malformed_keys_in_fit() -> None:
    from cipherchase.domain.scent_decode import ScentDecoder

    decoder = ScentDecoder(7, 4.0, 0.85,
                           {"grid_size": 5, "center_intensity": 0.9, "decay": 0.1, "falloff": 0.7})
    decoder.update({"bogus-key": 0.9, "3,3": 0.9})  # malformed key ignored, no crash
    assert decoder.grid.most_likely()[0] in range(7)


def test_evader_avoids_the_low_reach_pocket() -> None:
    brain = EvaderBrain(B, rng=random.Random(1))
    # corridor: (0,0) pocket walled except one gap — stepping in is suicide
    walls = frozenset({(0, 2), (1, 2), (2, 0), (2, 1)})
    decision = brain.decide(OwnState("thief", (1, 1)), _belief_at((6, 6)), walls)
    target = B.target_of((1, 1), decision.direction)
    assert target != (0, 0) or decision.direction is Direction.STAY


def test_evader_tie_randomization_is_seeded_deterministic() -> None:
    a = EvaderBrain(B, rng=random.Random(7))
    b = EvaderBrain(B, rng=random.Random(7))
    moves_a = [a.decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY).direction
               for _ in range(5)]
    moves_b = [b.decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY).direction
               for _ in range(5)]
    assert moves_a == moves_b  # same seed → same stream (audit reproducibility)


def test_archetypes_move_legally() -> None:
    naive = NaiveEdgeThief(B).decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY)
    assert naive.direction in B.legal_moves((3, 3), EMPTY)
    rand = RandomThief(B, rng=random.Random(3)).decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY)
    assert rand.direction in B.legal_moves((3, 3), EMPTY)
    assert StillThief(B).decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY).direction is Direction.STAY


def test_naive_edge_runs_from_the_believed_cop() -> None:
    brain = NaiveEdgeThief(B)
    decision = brain.decide(OwnState("thief", (3, 3)), _belief_at((0, 0)), EMPTY)
    target = B.target_of((3, 3), decision.direction)
    assert B.distance(target, (6, 6)) < B.distance((3, 3), (6, 6))  # toward the far corner
