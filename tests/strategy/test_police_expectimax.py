"""Reachability-minimizing cop (FR-C5) — a seam-swappable excellence brain."""

from __future__ import annotations

from pathlib import Path

from cipherchase.constants import Outcome
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.crypto import audit_records
from cipherchase.domain.own_state import OwnState
from cipherchase.sdk.game_loop import run_game
from cipherchase.shared.config import ConfigManager
from cipherchase.strategy.police_expectimax import PoliceExpectimax

CONFIG = Path(__file__).resolve().parents[2] / "config"
EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_makes_a_legal_move() -> None:
    brain = PoliceExpectimax(Board(7))
    decision = brain.decide(OwnState("police", (0, 0)), BeliefGrid(7), EMPTY)
    assert decision.direction in Board(7).legal_moves((0, 0), EMPTY)


def test_eval_rewards_shrinking_thief_reachability() -> None:
    brain = PoliceExpectimax(Board(7))
    open_board = brain._eval((3, 3), (0, 0), EMPTY)
    thief_boxed = brain._eval((3, 3), (0, 0), frozenset({(1, 0), (0, 1)}))
    assert thief_boxed < open_board  # a smaller reachable set is preferred


def test_plays_a_clean_auditable_game_through_the_seam() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["strategy"]["police_class"] = "cipherchase.strategy.police_expectimax:PoliceExpectimax"
    result = run_game(cfg)
    assert result.outcome in (Outcome.CAPTURE, Outcome.SURVIVAL)
    assert audit_records(result.records)["passed"] is True
