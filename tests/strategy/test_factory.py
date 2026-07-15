"""Strategy factory — swap brains by config spec, no engine change (FR-C4)."""

from __future__ import annotations

import pytest

from cipherchase.domain.board import Board
from cipherchase.exceptions import ConfigError
from cipherchase.strategy.factory import load_brain
from cipherchase.strategy.police_heuristic import PoliceBrain
from cipherchase.strategy.thief_heuristic import ThiefBrain


def test_loads_police_and_thief_from_config_spec() -> None:
    board = Board(7)
    cop = load_brain("cipherchase.strategy.police_heuristic:PoliceBrain", board)
    thief = load_brain("cipherchase.strategy.thief_heuristic:ThiefBrain", board)
    assert isinstance(cop, PoliceBrain)
    assert isinstance(thief, ThiefBrain)


def test_passes_params_to_the_brain() -> None:
    board = Board(7)
    brain = load_brain(
        "cipherchase.strategy.thief_heuristic:ThiefBrain", board, params={"w_dist": 2.0}
    )
    assert brain.params["w_dist"] == 2.0


def test_bad_spec_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        load_brain("no-colon-here", Board(7))
    with pytest.raises(ConfigError):
        load_brain("cipherchase.strategy.police_heuristic:Nope", Board(7))
