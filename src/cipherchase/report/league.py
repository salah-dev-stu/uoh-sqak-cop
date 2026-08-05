"""League series result — the symmetric outcome both teams must agree on (§6).

The mutual signature is the ONE field the two teams' result files share, and it
is what a grader diffs to see that both told the same story. It therefore hashes
the symmetric outcome ONLY (roles/result/score/aggregate) and uses the reference
construction — ``json.dumps(sort_keys=True, ensure_ascii=False)``, i.e. default
SPACED separators, deliberately not our compact canonical form, because the
league's byte contract for this one field is the reference's.

Anything per-peer (wall-clock, our own token count, our commit hash) stays out:
including it would make the two hashes unequal by construction, and unequal
hashes on two honest reports read as a contradiction — App-E rule 35, 0/0 both.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

Json = dict[str, Any]
_CAPTURE, _SURVIVAL = "capture", "survival"


def series_signature(game_id: str, aggregate: Json, rows: list[Json]) -> str:
    """SHA-256 over the symmetric series outcome, reference byte-for-byte."""
    doc = {"game_id": game_id, "aggregate": aggregate, "sub_games": rows}
    return hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _score(result: str, roles: dict[str, str], table: Json) -> dict[str, int]:
    """Points per group. Any non-terminal outcome is a technical loss: 0/0."""
    out = dict.fromkeys(roles, 0)
    if result not in (_CAPTURE, _SURVIVAL):
        return out
    cop_key = "capture_cop" if result == _CAPTURE else "survival_cop"
    thief_key = "capture_thief" if result == _CAPTURE else "survival_thief"
    for group, role in roles.items():
        out[group] = table[cop_key] if role == "police" else table[thief_key]
    return out


def subgame_rows(
    summaries: list[Json], own_gid: str, opp_gid: str, table: Json
) -> list[Json]:
    """One symmetric row per sub-game — identical from either peer's view."""
    rows: list[Json] = []
    for summary in summaries:
        own_role = summary["role"]
        roles = {own_gid: own_role, opp_gid: "thief" if own_role == "police" else "police"}
        score = _score(summary["result"], roles, table)
        winner_role = summary.get("winner")
        winner = next((g for g, r in roles.items() if r == winner_role), None)
        rows.append({
            "sub_game_number": summary["sub_game_number"],
            "roles": roles,
            "result": summary["result"],
            "winner_group": winner,
            "score": score,
        })
    return rows


def aggregate(rows: list[Json], tie_score: int) -> Json:
    """Sum the sub-game scores into the series result (reference semantics)."""
    scores = [row["score"] for row in rows]
    groups = sorted({group for score in scores for group in score})
    total = {g: sum(s.get(g, 0) for s in scores) for g in groups}
    won = dict.fromkeys(groups, 0)
    ties = 0
    for score in scores:
        if not score:
            continue
        top = max(score.values())
        leaders = [g for g, v in score.items() if v == top]
        if len(leaders) == 1:
            won[leaders[0]] += 1
        else:
            ties += 1
    if len(groups) == 2 and total[groups[0]] == total[groups[1]]:
        return {"total_score": {g: total[g] + tie_score for g in groups},
                "sub_games_won": won, "ties": ties,
                "winner_group": None, "series_tie": True}
    return {"total_score": total, "sub_games_won": won, "ties": ties,
            "winner_group": max(total, key=lambda g: total[g]) if total else None,
            "series_tie": False}
