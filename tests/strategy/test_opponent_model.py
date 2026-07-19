"""Opponent reply prediction (AB-3..AB-5): evaluate THEIR rule, not ours."""

from __future__ import annotations

import random

from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.exceptions import ConfigError
from cipherchase.strategy.opponent_model import OpponentModel
from cipherchase.strategy.thief_evader_v2 import EvaderBrain
from cipherchase.strategy.thief_heuristic import ThiefBrain

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def _belief_at(cell):
    g = BeliefGrid(7, smell_trust=1e6)
    g.observe_smell({f"{cell[0]},{cell[1]}": 1.0})
    return g


def test_deterministic_model_predicts_the_real_thief_reply() -> None:
    model = OpponentModel("thief_v1", B, {})
    real = ThiefBrain(B)
    for seed in range(20):
        rng = random.Random(seed)
        thief = (rng.randrange(7), rng.randrange(7))
        cop = (rng.randrange(7), rng.randrange(7))
        if thief == cop:
            continue
        d = real._pick_move(OwnState("thief", thief), _belief_at(cop), EMPTY)
        actual = B.target_of(thief, d)
        assert model.predict(thief, cop, EMPTY) == {actual}


def test_still_model_is_stay_locked() -> None:
    assert OpponentModel("still", B, {}).predict((3, 3), (0, 0), EMPTY) == {(3, 3)}


def test_evader_v2_reply_is_always_inside_the_predicted_tie_set() -> None:
    model = OpponentModel("evader_v2", B, {})
    thief_brain = EvaderBrain(B, rng=random.Random(3))
    for seed in range(15):
        rng = random.Random(100 + seed)
        thief = (rng.randrange(7), rng.randrange(7))
        cop = (rng.randrange(7), rng.randrange(7))
        if thief == cop:
            continue
        d = thief_brain._pick_move(OwnState("thief", thief), _belief_at(cop), EMPTY)
        realised = B.target_of(thief, d)
        assert realised in model.predict(thief, cop, EMPTY)  # support-exactness (AB-4)


def test_paranoid_superset_of_every_model() -> None:
    paranoid = OpponentModel("paranoid", B, {})
    legal = paranoid.predict((3, 3), (0, 0), EMPTY)
    for name in ("thief_v1", "evader_v2", "naive_edge", "random", "still"):
        assert OpponentModel(name, B, {}).predict((3, 3), (0, 0), EMPTY) <= legal


def test_ensemble_hedges_the_deterministic_archetypes() -> None:
    # League-robust minimax: the ensemble contains every deterministic archetype
    # it hedges, yet stays a subset of paranoid (a tight hedge, not all legal cells).
    ens = OpponentModel("ensemble", B, {})
    paranoid = OpponentModel("paranoid", B, {})
    thief, cop = (0, 3), (4, 3)
    union = ens.predict(thief, cop, EMPTY)
    for name in ("thief_v1", "naive_edge", "still"):
        assert OpponentModel(name, B, {}).predict(thief, cop, EMPTY) <= union
    assert union <= paranoid.predict(thief, cop, EMPTY)


def test_fixed_belief_reports_full_mass_only_on_its_cell() -> None:
    from cipherchase.strategy.opponent_model import _FixedBelief
    fb = _FixedBelief((2, 4))
    assert fb.most_likely() == (2, 4)
    assert fb.mass_at((2, 4)) == 1.0
    assert fb.mass_at((0, 0)) == 0.0


def test_unknown_model_raises_config_error() -> None:
    try:
        OpponentModel("mystery", B, {})
    except ConfigError:
        return
    raise AssertionError("unknown model must raise ConfigError")
