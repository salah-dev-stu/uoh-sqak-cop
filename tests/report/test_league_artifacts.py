"""A LIVE league series must emit the four App-F artifacts of the game it played.

Before this existed, ``cipherchase peer`` printed its tally and exited, and the
only artifact writer replayed a fresh OFFLINE self-match — so a counted match
would have emailed artifacts of a game the opponent never played.
"""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.report import emit, league
from cipherchase.sdk.league_reports import build_series_artifacts
from cipherchase.shared.config import ConfigManager
from cipherchase.shared.gatekeeper import ApiGatekeeper

CONFIG = Path(__file__).resolve().parents[2] / "config"
OUTCOME = {
    "game_id": "imreeyal-vs-uoh-sqak",
    "game_uid": "a59583ca-0700-085e-ba79-64976ecdc0ac",
    "summaries": [
        {"sub_game_number": 1, "role": "police", "result": "capture", "winner": "police",
         "steps": 14, "audit": {"passed": True, "status": "done"}, "records": [{"commit": "ab"}]},
        {"sub_game_number": 2, "role": "thief", "result": "survival", "winner": "thief",
         "steps": 35, "audit": {"passed": True, "status": "done"}, "records": [{"commit": "cd"}]},
    ],
}


def _build(**kw):
    cfg = ConfigManager.load(CONFIG / "police")
    gate = ApiGatekeeper.from_config(cfg, now=lambda: 0.0)
    return build_series_artifacts(
        cfg, OUTCOME, opponent="imreeyal", generated_at="2026-08-05T00:00:00+00:00",
        gate=gate, **kw)


def test_a_series_emits_one_declaration_one_result_and_a_pair_per_sub_game() -> None:
    arts = _build()
    kinds = [a["_schema"] for a in arts]
    assert kinds.count("declaration") == 1 and kinds.count("result") == 1
    assert kinds.count("config") == 2 and kinds.count("log") == 2
    assert [a["sub_game"] for a in arts if a["_schema"] == "log"] == [1, 2]


def test_the_result_carries_the_symmetric_signature_the_opponent_will_recompute() -> None:
    result = next(a for a in _build() if a["_schema"] == "result")
    table = ConfigManager.load(CONFIG / "police").shared["scoring"]
    rows = league.subgame_rows(OUTCOME["summaries"], "uoh-sqak", "imreeyal", table)
    expected = league.series_signature(
        OUTCOME["game_id"], league.aggregate(rows, table["tie_score"]), rows)
    assert result["mutual_agreement"]["sha256"] == expected
    assert result["mutual_agreement"]["confirmed"] is True
    assert result["groups"] == ["imreeyal", "uoh-sqak"], "sorted pair, same on both sides"


def test_the_result_declares_the_league_counters_truthfully() -> None:
    result = next(a for a in _build(games_played=3, first_meeting=True) if a["_schema"] == "result")
    league_fields = result["league"]
    assert league_fields["games_played_including_this"] == 3
    assert league_fields["first_meeting_between_groups"] is True
    assert league_fields["diversity_reward_applied"] is True
    # A false "first meeting" is a rule-38 disqualification, so a repeat pairing
    # must never carry the bonus.
    again = next(a for a in _build(games_played=4, first_meeting=False) if a["_schema"] == "result")
    assert again["league"]["diversity_reward_applied"] is False


def test_filenames_are_the_sorted_pair_both_teams_derive() -> None:
    arts = _build()
    result = next(a for a in arts if a["_schema"] == "result")
    assert emit.filename("result", result["game_id"]) == "result_imreeyal-vs-uoh-sqak.json"


def test_an_unverified_audit_is_never_reported_as_confirmed() -> None:
    bad = {**OUTCOME, "summaries": [
        {**OUTCOME["summaries"][0], "audit": {"passed": False, "status": "done"}},
        OUTCOME["summaries"][1]]}
    cfg = ConfigManager.load(CONFIG / "police")
    arts = build_series_artifacts(
        cfg, bad, opponent="imreeyal", generated_at="x",
        gate=ApiGatekeeper.from_config(cfg, now=lambda: 0.0))
    result = next(a for a in arts if a["_schema"] == "result")
    assert result["mutual_agreement"]["confirmed"] is False


def test_writing_a_league_series_persists_files_ledger_and_mails_them(tmp_path) -> None:
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["email"] = {**cfg.private["email"], "enabled": True}
    sent: list = []
    paths = write_league_series(
        cfg, OUTCOME, tmp_path, generated_at="2026-08-05T00:00:00+00:00",
        opponent="imreeyal", counted=True,
        email_backend=lambda raw: sent.append(raw) or {"id": "1"})
    names = sorted(p.name for p in paths)
    assert names == ["config_imreeyal-vs-uoh-sqak_g01.json",
                     "config_imreeyal-vs-uoh-sqak_g02.json",
                     "declaration_imreeyal-vs-uoh-sqak.json",
                     "log_imreeyal-vs-uoh-sqak_g01.json",
                     "log_imreeyal-vs-uoh-sqak_g02.json",
                     "result_imreeyal-vs-uoh-sqak.json"]
    assert sent, "a counted series must auto-report (rule 32) — never a human sending it"
    assert (tmp_path / "opponents.json").exists()


def test_the_first_meeting_is_claimed_once_and_never_again(tmp_path) -> None:
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    kw = {"generated_at": "x", "opponent": "imreeyal", "counted": True}
    write_league_series(cfg, OUTCOME, tmp_path, **kw)
    first = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert first["league"]["first_meeting_between_groups"] is True
    assert first["league"]["games_played_including_this"] == 1
    write_league_series(cfg, OUTCOME, tmp_path, **kw)
    again = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert again["league"]["first_meeting_between_groups"] is False
    assert again["league"]["games_played_including_this"] == 2
