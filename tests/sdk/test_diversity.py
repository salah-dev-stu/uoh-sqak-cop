"""Diversity bonus (league scoring): first game vs a NEW group earns it — once."""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.sdk.sdk import SimulationSdk
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _cfg():
    return ConfigManager.load(CONFIG / "police")


def _winner_score(arts) -> int:
    scores = arts["result"]["sub_games"][0]["scores"]
    return scores[arts["result"]["final_result"]]


def test_new_opponent_game_carries_the_diversity_bonus() -> None:
    cfg = _cfg()
    base = SimulationSdk.run_self_match(cfg, generated_at="t", opponent="uoh-rival")
    boosted = SimulationSdk.run_self_match(
        _cfg(), generated_at="t", opponent="uoh-rival", new_opponent=True)
    bonus = cfg.shared["scoring"]["diversity_reward"]
    assert _winner_score(boosted) == _winner_score(base) + bonus  # winner earns it


def test_write_reports_ledger_grants_the_bonus_exactly_once(tmp_path) -> None:
    def winner_score(paths):
        result = json.loads(next(p for p in paths if p.name.startswith("result_")).read_text())
        return result["sub_games"][0]["scores"][result["final_result"]]

    first = winner_score(SimulationSdk.write_reports(
        _cfg(), tmp_path, generated_at="t", opponent="uoh-rival"))
    again = winner_score(SimulationSdk.write_reports(  # same filenames — read per run
        _cfg(), tmp_path, generated_at="t", opponent="uoh-rival"))
    ledger = json.loads((tmp_path / "opponents.json").read_text())
    assert ledger == ["uoh-rival"]  # recorded once, not duplicated
    bonus = _cfg().shared["scoring"]["diversity_reward"]
    assert first == again + bonus  # only the FIRST game vs a group earns it


def test_self_play_never_earns_diversity(tmp_path) -> None:
    SimulationSdk.write_reports(_cfg(), tmp_path, generated_at="t", opponent="uoh-sqak")
    assert not (tmp_path / "opponents.json").exists() or \
        json.loads((tmp_path / "opponents.json").read_text()) == []
