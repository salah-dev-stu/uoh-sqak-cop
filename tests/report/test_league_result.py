"""League series result — the cross-team agreed outcome (App-F table 20, §6).

``mutual_agreement.sha256`` must be EQUAL in both teams' result files, so it is
hashed over the symmetric outcome only, with the REFERENCE construction:
``json.dumps(doc, sort_keys=True, ensure_ascii=False)`` — default (spaced)
separators, not our compact canonical form. Anything per-side (timestamps, our
own tokens, our commit hashes) would make the two hashes unequal by construction.
"""

from __future__ import annotations

import hashlib
import json

from cipherchase.report import league

TABLE = {"capture_cop": 20, "capture_thief": 5, "survival_cop": 5,
         "survival_thief": 10, "tie_score": 2, "technical_loss": 0}
US, THEM = "uoh-sqak", "imreeyal"


def _summaries(perspective: str) -> list[dict]:
    """The same two sub-games as seen from one peer or the other."""
    flip = {"police": "thief", "thief": "police"}
    rows = [{"sub_game_number": 1, "role": "police", "result": "capture",
             "winner": "police", "audit": {"passed": True}},
            {"sub_game_number": 2, "role": "thief", "result": "survival",
             "winner": "thief", "audit": {"passed": True}}]
    if perspective == "them":
        rows = [{**r, "role": flip[r["role"]]} for r in rows]
    return rows


def test_series_signature_uses_the_reference_spaced_separator_form() -> None:
    rows = league.subgame_rows(_summaries("us"), US, THEM, TABLE)
    agg = league.aggregate(rows, TABLE["tie_score"])
    trimmed = [{k: r[k] for k in league.SYMMETRIC} for r in rows]
    doc = {"game_id": "imreeyal-vs-uoh-sqak", "aggregate": agg, "sub_games": trimmed}
    expected = hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert league.series_signature("imreeyal-vs-uoh-sqak", agg, rows) == expected


def test_both_peers_compute_an_identical_signature_from_mirrored_views() -> None:
    ours = league.subgame_rows(_summaries("us"), US, THEM, TABLE)
    theirs = league.subgame_rows(_summaries("them"), THEM, US, TABLE)
    gid = "imreeyal-vs-uoh-sqak"
    a = league.series_signature(gid, league.aggregate(ours, 2), ours)
    b = league.series_signature(gid, league.aggregate(theirs, 2), theirs)
    assert a == b, "the two peers' result files must carry the SAME mutual sha256"


def test_rows_carry_the_symmetric_fields_and_the_signature_sees_only_those() -> None:
    rows = league.subgame_rows(_summaries("us"), US, THEM, TABLE)
    assert set(rows[0]) >= set(league.SYMMETRIC)
    assert league.SYMMETRIC == ("sub_game_number", "roles", "result", "winner_group", "score")
    assert rows[0]["roles"] == {US: "police", THEM: "thief"}
    assert rows[0]["score"] == {US: 20, THEM: 5}
    assert rows[0]["winner_group"] == US
    assert rows[1]["score"] == {US: 10, THEM: 5}  # we were the surviving thief


def test_a_technical_outcome_scores_zero_for_both() -> None:
    rows = league.subgame_rows(
        [{"sub_game_number": 1, "role": "police", "result": "tamper_forfeit",
          "winner": None, "audit": {"passed": False}}], US, THEM, TABLE)
    assert rows[0]["score"] == {US: 0, THEM: 0}
    assert rows[0]["winner_group"] is None


def test_aggregate_totals_and_series_tie() -> None:
    rows = league.subgame_rows(_summaries("us"), US, THEM, TABLE)
    agg = league.aggregate(rows, TABLE["tie_score"])
    assert agg["total_score"] == {US: 30, THEM: 10}
    assert agg["winner_group"] == US and agg["series_tie"] is False
    tied = league.aggregate(
        league.subgame_rows(
            [{"sub_game_number": 1, "role": "police", "result": "timeout",
              "winner": None, "audit": {"passed": True}}], US, THEM, TABLE), 2)
    assert tied["series_tie"] is True and tied["total_score"] == {US: 2, THEM: 2}


def test_a_row_with_no_scored_groups_is_skipped_not_counted() -> None:
    # `aggregate` is public and may be handed hand-built rows; an empty score
    # must not invent a winner out of an empty max().
    agg = league.aggregate([{"score": {}}, {"score": {US: 20, THEM: 5}}], 2)
    assert agg["sub_games_won"] == {US: 1, THEM: 0} and agg["ties"] == 0
