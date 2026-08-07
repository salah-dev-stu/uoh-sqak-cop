"""Refusing to report: a series that did not finish has no honest artifact.

We shipped the narrow half of this fix first — dropping unplayed windows FROM a
report — and then mailed a two-game "series tie" while the opponent was still
playing sub-game 3.
"""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
OUTCOME = {
    "game_id": "imreeyal-vs-uoh-sqak",
    "game_uid": "a59583ca-0700-085e-ba79-64976ecdc0ac",
    "summaries": [
        {"sub_game_number": 1, "role": "police", "result": "capture", "winner": "police",
         "steps": 14, "audit": {"passed": True, "status": "done"}, "records": []},
    ],
}
FULL = {**OUTCOME, "summaries": [
    {"sub_game_number": n, "role": "police" if n % 2 else "thief", "result": "capture",
     "winner": "police", "steps": 12, "audit": {"passed": True}, "records": [{"c": n}]}
    for n in range(1, 7)]}


def test_a_partial_series_produces_no_artifact_and_no_mail(tmp_path, capsys) -> None:
    # Dropping unplayed windows FROM a report is not the same as refusing to emit
    # a short one. We shipped the first and believed we were done — then mailed a
    # two-game "series tie" while the opponent was still playing sub-game 3.
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["email"] = {**cfg.private["email"], "enabled": True}
    sent: list = []
    paths = write_league_series(
        cfg, OUTCOME, tmp_path, generated_at="x", opponent="imreeyal",
        email_backend=lambda raw: sent.append(raw) or {"id": "1"})
    assert paths == [], "a partial series has no honest report"
    assert sent == [], "and nothing to send"
    assert not list(tmp_path.glob("result_*.json"))
    out = capsys.readouterr().out
    assert "1 of 6 sub-games settled" in out, f"the refusal must name the shortfall: {out}"


def test_a_complete_series_reports_normally(tmp_path) -> None:
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    full = {**OUTCOME, "summaries": [
        {"sub_game_number": n, "role": "police" if n % 2 else "thief",
         "result": "capture", "winner": "police", "steps": 12,
         "audit": {"passed": True}, "records": []} for n in range(1, 7)]}
    paths = write_league_series(cfg, full, tmp_path, generated_at="x", opponent="imreeyal")
    assert len(paths) == 14, "declaration + result + 6 config/log pairs"


def test_a_friendly_moves_no_counter_and_claims_no_reward(tmp_path) -> None:
    # League fields key on COUNTED series, never on "we ran the full rulebook".
    # A friendly that claims a diversity reward is a false claim, and a false
    # first-meeting is a rule-38 project-level disqualification.
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    write_league_series(cfg, FULL, tmp_path, generated_at="x",
                        opponent="imreeyal", counted=False)
    res = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert res["final_result"]["diversity_reward_applied"] == dict.fromkeys(("uoh-sqak", "imreeyal"), False)
    assert res["final_result"]["first_meeting_between_groups"] is True, (
        "the groups have still never met — the FACT is mode-independent")
    assert res["final_result"]["games_played_including_this"]["uoh-sqak"] == 0, (
        "a friendly is not a counted game")
    assert res["final_result"]["counted"] is False
    assert not (tmp_path / "opponents.json").exists(), "no counted opponent recorded"


def test_a_counted_series_moves_the_counter_once(tmp_path) -> None:
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    for _ in range(2):  # two friendlies first — neither may move anything
        write_league_series(cfg, FULL, tmp_path, generated_at="x",
                            opponent="imreeyal", counted=False)
    write_league_series(cfg, FULL, tmp_path, generated_at="x",
                        opponent="imreeyal", counted=True)
    res = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert res["final_result"]["games_played_including_this"]["uoh-sqak"] == 1
    assert res["final_result"]["first_meeting_between_groups"] is True
    assert res["final_result"]["diversity_reward_applied"] == dict.fromkeys(("uoh-sqak", "imreeyal"), True)
    write_league_series(cfg, FULL, tmp_path, generated_at="x",
                        opponent="imreeyal", counted=True)
    again = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert again["final_result"]["first_meeting_between_groups"] is False
    assert again["final_result"]["diversity_reward_applied"] == dict.fromkeys(("uoh-sqak", "imreeyal"), False)
