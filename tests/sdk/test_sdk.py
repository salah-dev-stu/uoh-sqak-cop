"""SimulationSdk — single business entry that runs a match → 4 artifacts (R1)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.sdk.sdk import SimulationSdk
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_run_self_match_produces_four_linked_artifacts() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    arts = SimulationSdk.run_self_match(cfg, generated_at="2026-08-01T00:00:00Z")
    assert set(arts) == {"declaration", "config", "log", "result"}
    assert len({a["game_uid"] for a in arts.values()}) == 1  # one shared game_uid
    assert arts["config"]["config_sha256"] == cfg.config_sha256


def test_self_match_log_audits_clean_and_signs() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    arts = SimulationSdk.run_self_match(cfg, generated_at="2026-08-01T00:00:00Z")
    assert arts["log"]["mutual_agreement"]["audit"] == "verified"
    assert arts["result"]["final_result"] in ("police", "thief", "tie")
    assert arts["log"]["mutual_agreement"]["signature"]  # non-empty symmetric sig


def test_write_reports_creates_the_four_files(tmp_path) -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    paths = SimulationSdk.write_reports(cfg, tmp_path, generated_at="2026-08-01T00:00:00Z")
    assert len(paths) == 4
    assert all(p.exists() for p in paths)


def test_run_self_match_both_mirrors_one_game_from_both_roles() -> None:
    police = ConfigManager.load(CONFIG / "police")
    thief = ConfigManager.load(CONFIG / "thief")
    ours, theirs = SimulationSdk.run_self_match_both(
        police, thief, generated_at="2026-08-01T00:00:00Z", opponent="uoh-sqak")
    # ONE game: identical sealed records + shared game_uid across both quartets
    assert ours["log"]["records"] == theirs["log"]["records"]
    assert ours["log"]["game_uid"] == theirs["log"]["game_uid"]
    # byte-identical symmetric mutual signature — the F11 claim, demonstrated
    assert ours["log"]["mutual_agreement"] == theirs["log"]["mutual_agreement"]
    # but each side keeps its own role-scoped game_id
    assert ours["result"]["game_id"] != theirs["result"]["game_id"]
    assert "police" in ours["result"]["game_id"] and "thief" in theirs["result"]["game_id"]
