"""Reporting a live series: retries, and a send that fails (imreeyal replay).

Both defects came out of our first real league series — one made the mutual
signature impossible to match, the other lost the run on a credential error.
"""

from __future__ import annotations

from pathlib import Path

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
    ],
}


def test_retries_collapse_to_one_row_per_sub_game() -> None:
    # A live series appends EVERY handshake retry to its summaries. Left alone
    # they each became a result row: our first real series emitted 76 rows,
    # "ties": 70, and sub_game_number 1 seven times. The opponent's file has six
    # rows, so the mutual signature could never have matched — the one field
    # that must agree, computed over a list that cannot.
    noisy = {**OUTCOME, "summaries": [
        {"sub_game_number": 1, "role": "thief", "result": "handshake_failed",
         "winner": "-", "steps": 0, "audit": {"passed": None}, "records": []},
        {"sub_game_number": 1, "role": "thief", "result": "handshake_failed",
         "winner": "-", "steps": 0, "audit": {"passed": None}, "records": []},
        {"sub_game_number": 1, "role": "thief", "result": "capture",
         "winner": "police", "steps": 13, "audit": {"passed": True}, "records": [{"c": 1}]},
        {"sub_game_number": 2, "role": "police", "result": "timeout",
         "winner": "police", "steps": 7, "audit": {"passed": None}, "records": []},
    ]}  # a timeout WITH play in it settles; a zero-turn one is covered separately
    cfg = ConfigManager.load(CONFIG / "police")
    arts = build_series_artifacts(
        cfg, noisy, opponent="imreeyal", generated_at="x",
        gate=ApiGatekeeper.from_config(cfg, now=lambda: 0.0))
    result = next(a for a in arts if a["_schema"] == "result")
    numbers = [r["sub_game_number"] for r in result["sub_games"]]
    assert numbers == [1, 2], "one row per sub-game, in order"
    assert result["sub_games"][0]["result"] == "capture", "the SETTLED outcome, not a retry"
    assert result["num_sub_games"] == 2
    # and the per-sub-game log/config pairs must not multiply either
    assert [a["sub_game"] for a in arts if a["_schema"] == "log"] == [1, 2]


def test_a_missing_mail_backend_never_costs_us_the_artifacts(tmp_path, capsys) -> None:
    # Rule 32 wants the report auto-fired, but a credential problem must not
    # destroy the evidence of a series that was actually played. Our first live
    # series wrote all six artifacts and then died on the send, exiting non-zero
    # with a traceback — the artifacts survived by luck of ordering, not design.
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["email"] = {**cfg.private["email"], "enabled": True}
    paths = write_league_series(
        cfg, OUTCOME, tmp_path, generated_at="x", opponent="imreeyal",
        email_backend=None)  # no credentials available
    assert len(paths) == 4, "declaration + config + log + result all written"
    assert (tmp_path / "result_imreeyal-vs-uoh-sqak.json").exists()
    assert "REPORT NOT SENT" in capsys.readouterr().out, "and the failure is loud"


def test_the_send_failure_is_reported_not_swallowed(tmp_path, capsys) -> None:
    from cipherchase.sdk.league_reports import write_league_series

    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["email"] = {**cfg.private["email"], "enabled": True}

    def _explode(raw):
        raise RuntimeError("quota exceeded")

    write_league_series(cfg, OUTCOME, tmp_path, generated_at="x",
                        opponent="imreeyal", email_backend=_explode)
    out = capsys.readouterr().out
    assert "REPORT NOT SENT" in out and "quota exceeded" in out


def test_a_window_that_never_became_a_game_contributes_no_row() -> None:
    # Our first settled series emitted a `handshake_failed` row for sub-game 3,
    # which never connected. imreeyal's file has no row for it at all — so our
    # two mutual signatures would differ over a sub-game that did not happen,
    # and the one field that must agree would disagree for the second time.
    from cipherchase.sdk.league_reports import settled_summaries
    rows = settled_summaries([
        {"sub_game_number": 1, "role": "thief", "result": "capture", "winner": "police",
         "steps": 13, "audit": {"passed": True}, "records": []},
        {"sub_game_number": 2, "role": "police", "result": "timeout", "winner": "police",
         "steps": 0, "audit": {"passed": None}, "records": []},
        {"sub_game_number": 2, "role": "police", "result": "capture", "winner": "police",
         "steps": 14, "audit": {"passed": True}, "records": []},
        {"sub_game_number": 3, "role": "thief", "result": "handshake_failed", "winner": "-",
         "steps": 0, "audit": {"passed": None}, "records": []},
    ])
    assert [r["sub_game_number"] for r in rows] == [1, 2], "no row for a game never played"
    assert rows[1]["result"] == "capture", "the retried window's SETTLED outcome"


def test_an_unplayed_series_reports_nothing_rather_than_a_row_of_zeroes() -> None:
    from cipherchase.sdk.league_reports import settled_summaries
    assert settled_summaries([
        {"sub_game_number": 1, "role": "thief", "result": "handshake_failed",
         "winner": "-", "steps": 0, "audit": {"passed": None}, "records": []}]) == []
