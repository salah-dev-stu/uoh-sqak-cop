"""Full config-driven self-match engine (integrates Stages 1-6)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.constants import Outcome
from cipherchase.domain.crypto import audit_records
from cipherchase.sdk.game_loop import run_game
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_self_match_reaches_a_terminal_outcome() -> None:
    result = run_game(ConfigManager.load(CONFIG / "police"))
    assert result.outcome in (Outcome.CAPTURE, Outcome.SURVIVAL)
    assert result.turns >= 1
    assert len(result.records) >= 1


def test_self_match_log_audits_clean() -> None:
    result = run_game(ConfigManager.load(CONFIG / "police"))
    assert audit_records(result.records)["passed"] is True


def test_scores_match_the_outcome() -> None:
    result = run_game(ConfigManager.load(CONFIG / "police"))
    cop, thief = result.scores
    assert (cop, thief) in {(20, 5), (5, 10)}  # capture or survival


def test_capture_on_cop_move_when_thief_starts_adjacent() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    cfg.shared["board_and_agents"]["thief_start"] = [0, 1]  # next to cop at [0,0]
    result = run_game(cfg)
    assert result.outcome is Outcome.CAPTURE
    assert result.turns == 1


def test_survival_path_when_the_cop_does_not_pursue() -> None:
    # A cop that evades (never captures) → thief survives to the threshold.
    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["strategy"]["police_class"] = "cipherchase.strategy.thief_heuristic:ThiefBrain"
    result = run_game(cfg)
    assert result.outcome is Outcome.SURVIVAL
    assert result.turns == cfg.shared["movement_and_barriers"]["max_moves"]
