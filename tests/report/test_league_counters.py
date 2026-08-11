"""League counters in the result — declared by the peer, not invented by us.

Rules 37-38 make the game count a MUTUAL declaration, so filing a zero where the
opponent declared a number is the rule-35 contradictory shape with both sides
honest. Both defects here were caught by opponents reading our artifacts.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cipherchase.report import league

TABLE = {"capture_cop": 20, "capture_thief": 5, "survival_cop": 5,
         "survival_thief": 10, "tie_score": 2, "technical_loss": 0}
US, THEM = "uoh-sqak", "imreeyal"


def test_the_opponents_declared_count_reaches_the_artifact(tmp_path) -> None:
    # The regression imreeyal caught: they declare counted_games_played on the
    # wire, we read it correctly at the handshake, and then dropped it before
    # the report — filing a counted match that says they have played none.
    # Rules 37-38 make the count a MUTUAL declaration and a false first-meeting
    # is a project-level disqualification.

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

    from cipherchase.sdk.league_reports import write_league_series
    from cipherchase.shared.config import ConfigManager

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    outcome = {"game_id": "imreeyal-vs-uoh-sqak", "game_uid": "u",
               "summaries": [{"sub_game_number": n, "role": "police", "result": "capture",
                              "winner": "police", "steps": 12, "audit": {"passed": True},
                              "records": [],
                              "peer_identity": {"group_id": THEM, "counted_games_played": 1}}
                             for n in range(1, 7)]}
    with tempfile.TemporaryDirectory() as tmp:
        write_league_series(cfg, outcome, tmp, generated_at="x", opponent=THEM, counted=True)
        r = _json.loads((Path(tmp) / "result_imreeyal-vs-uoh-sqak.json").read_text())
    declared = int(cfg.private["game"]["counted_games_played"])
    assert r["final_result"]["games_played_including_this"] == {US: declared + 1, THEM: 2}, (
        "each side's DECLARED total plus this counted game — never a pinned literal")


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


def test_our_own_counted_total_comes_from_our_declaration_not_the_local_ledger() -> None:
    # vibecode's filed result put uoh-sqak at 1 (read off the count we SIGN at
    # the handshake); ours put us at 0. Theirs was right. The field is each
    # side's TOTAL counted series including this one, and we were computing
    # "how many times have we played THIS opponent" from a per-directory
    # ledger — a different quantity that reads 0 in every fresh out-dir.
    #
    # Third time this exact field has been wrong on our side, and the second
    # time an opponent's file was more accurate about us than our own.
    from cipherchase.sdk.settled import own_counted_total
    assert own_counted_total(declared=1, counted=True) == 2, "a counted series bumps us"
    assert own_counted_total(declared=1, counted=False) == 1, "a friendly moves nothing"
    assert own_counted_total(declared=0, counted=True) == 1
    assert own_counted_total(declared=0, counted=False) == 0
