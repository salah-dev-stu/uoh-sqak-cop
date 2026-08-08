"""The result's shape, as imreeyal diffed it against the reference (their §1-3).

A matching signature is not a matching report: the grader compares the emails.
Three differences they found, all of them places they had read the reference and
we had not — league counters in the wrong place and shape, sub-game rows carrying
only the five signed fields, and a missing timezone/report_type.

The invariant that makes the extra fields safe: the mutual signature is computed
over the SYMMETRIC five only. Per-side data (our commit, our tokens, our clock)
must never reach it, or two honest teams can never agree.
"""

from __future__ import annotations

from cipherchase.report import league

TABLE = {"capture_cop": 20, "capture_thief": 5, "survival_cop": 5,
         "survival_thief": 10, "tie_score": 2, "technical_loss": 0}
US, THEM = "uoh-sqak", "imreeyal"
SUMMARIES = [{"sub_game_number": 1, "role": "police", "result": "capture",
              "winner": "police", "audit": {"passed": True}}]


def test_the_signature_ignores_everything_per_side() -> None:
    bare = league.subgame_rows(SUMMARIES, US, THEM, TABLE)
    rich = league.subgame_rows(SUMMARIES, US, THEM, TABLE,
                               commits={US: "abc1234", THEM: "def5678"},
                               tokens={US: 4096, THEM: 0}, game_id="imreeyal-vs-uoh-sqak")
    agg = league.aggregate(bare, 2)
    assert league.series_signature("g", agg, bare) == league.series_signature("g", agg, rich), (
        "our commit and our token count must not move the one field we must share")


def test_rows_carry_the_reference_field_set() -> None:
    rows = league.subgame_rows(SUMMARIES, US, THEM, TABLE,
                               commits={US: "abc1234", THEM: "def5678"},
                               tokens={US: 4096, THEM: 0}, game_id="imreeyal-vs-uoh-sqak")
    row = rows[0]
    assert set(row) >= {"sub_game_number", "roles", "result", "winner_group", "score",
                        "tie", "github_commit", "tokens", "log_files", "audit"}
    assert row["github_commit"] == {US: "abc1234", THEM: "def5678"}, (
        "the field that lets a grader reach the code that played this sub-game")
    assert row["audit"] == {"log_verified": True, "tampered": False}
    assert row["tie"] is False
    assert row["log_files"][US].endswith("log_imreeyal-vs-uoh-sqak_g01.json")


def test_a_tie_row_says_so() -> None:
    drawn = [{"sub_game_number": 1, "role": "police", "result": "timeout",
              "winner": None, "audit": {"passed": None}}]
    row = league.subgame_rows(drawn, US, THEM, TABLE)[0]
    assert row["tie"] is True and row["winner_group"] is None
    assert row["audit"] == {"log_verified": False, "tampered": False}, (
        "a window with no audit is unverified, not tampered")


def test_the_result_carries_timezone_report_type_and_per_group_counters() -> None:
    from pathlib import Path

    from cipherchase.sdk.league_reports import build_series_artifacts
    from cipherchase.shared.config import ConfigManager
    from cipherchase.shared.gatekeeper import ApiGatekeeper

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    outcome = {"game_id": "imreeyal-vs-uoh-sqak", "game_uid": "u",
               "summaries": [{"sub_game_number": n, "role": "police", "result": "capture",
                              "winner": "police", "steps": 12, "audit": {"passed": True},
                              "records": []} for n in range(1, 7)]}
    arts = build_series_artifacts(
        cfg, outcome, opponent=THEM, generated_at="x",
        gate=ApiGatekeeper.from_config(cfg, now=lambda: 0.0),
        counted=True, first_meeting=True, opponent_counted=1)
    result = next(a for a in arts if a["_schema"] == "result")
    assert result["report_type"] == "final_game_result"
    assert result["timezone"], "a grader reading two files needs both to say the zone"
    final = result["final_result"]
    assert final["games_played_including_this"] == {US: 1, THEM: 1}, (
        "per-group and inside final_result, where the book's example carries them")
    assert final["first_meeting_between_groups"] is True
    assert final["diversity_reward_applied"] == {US: True, THEM: True}


def test_the_opponents_declared_count_reaches_the_artifact(tmp_path) -> None:
    # The regression imreeyal caught: they declare counted_games_played on the
    # wire, we read it correctly at the handshake, and then dropped it before
    # the report — filing a counted match that says they have played none.
    # Rules 37-38 make the count a MUTUAL declaration and a false first-meeting
    # is a project-level disqualification.
    from pathlib import Path

    from cipherchase.sdk.league_reports import write_league_series
    from cipherchase.shared.config import ConfigManager

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    outcome = {
        "game_id": "imreeyal-vs-uoh-sqak", "game_uid": "u",
        "summaries": [{"sub_game_number": n, "role": "police", "result": "capture",
                       "winner": "police", "steps": 12, "audit": {"passed": True},
                       "records": [], "started_at": "2026-08-08T00:45:00+00:00",
                       "ended_at": "2026-08-08T00:47:00+00:00",
                       # what they put on the wire, read at negotiate time
                       "peer_identity": {"group_id": THEM, "counted_games_played": 1}}
                      for n in range(1, 7)]}
    write_league_series(cfg, outcome, tmp_path, generated_at="x", opponent=THEM)
    import json
    result = json.loads((tmp_path / "result_imreeyal-vs-uoh-sqak.json").read_text())
    final = result["final_result"]
    assert final["games_played_including_this"][THEM] == 1, (
        "their declared count, not a zero we invented for them")
    assert final["diversity_reward_applied"] == {US: False, THEM: False}, "per-group"
    assert final["tokens_total_series"] == {US: 0, THEM: 0}, "per-group, never null"
    row = result["sub_games"][0]
    assert row["started_at"] and row["ended_at"], "timestamps, not null"


def test_including_this_means_including_this_for_both_groups() -> None:
    # The field is games_played_including_this. Ours counts this game; theirs is
    # their DECLARED prior, which must also have this game added — or two honest
    # files disagree by exactly one on the opponent's column.
    import json as _json
    from pathlib import Path

    from cipherchase.sdk.league_reports import write_league_series
    from cipherchase.shared.config import ConfigManager

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    outcome = {"game_id": "imreeyal-vs-uoh-sqak", "game_uid": "u",
               "summaries": [{"sub_game_number": n, "role": "police", "result": "capture",
                              "winner": "police", "steps": 12, "audit": {"passed": True},
                              "records": [],
                              "peer_identity": {"group_id": THEM, "counted_games_played": 1}}
                             for n in range(1, 7)]}
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        write_league_series(cfg, outcome, tmp, generated_at="x", opponent=THEM, counted=True)
        r = _json.loads((Path(tmp) / "result_imreeyal-vs-uoh-sqak.json").read_text())
    assert r["final_result"]["games_played_including_this"] == {US: 1, THEM: 2}, (
        "their declared 1 plus this game = 2; ours 0 plus this game = 1")


def test_a_role_aware_opponent_commit_can_be_filed_per_sub_game() -> None:
    # imreeyal's cop and thief live in different repos, so their commit differs
    # by sub-game parity. Ours is one tree, one hash. The column has to carry
    # both shapes or we cannot file what they actually declared.
    rows = league.subgame_rows(
        [{"sub_game_number": n, "role": "thief" if n % 2 else "police",
          "result": "survival", "winner": "thief", "audit": {"passed": True}}
         for n in (1, 2)],
        US, THEM, TABLE, game_id="imreeyal-vs-uoh-sqak",
        commits={US: "aaaa111", THEM: {1: "27568a1", 2: "24e4687"}})
    assert rows[0]["github_commit"] == {US: "aaaa111", THEM: "27568a1"}
    assert rows[1]["github_commit"] == {US: "aaaa111", THEM: "24e4687"}
