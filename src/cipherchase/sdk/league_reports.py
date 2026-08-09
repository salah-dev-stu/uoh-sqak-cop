"""The four App-F artifacts for a LIVE league series (F11/F14).

``SimulationSdk.run_peer`` plays the real series; this turns its summaries into
the reports both teams email. The distinction matters: the offline self-match
writer replays a game the opponent never saw, so a counted match reported from
it would describe a fixture, not the match.

Per sub-game: one ``config`` + one ``log`` (sealed records + audit verdict).
Per series: one ``declaration`` (signed Step-0) + one ``result`` carrying the
symmetric mutual signature the opponent independently recomputes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cipherchase.report import artifacts, emit, league, links
from cipherchase.sdk.league_mail import gmail_backend, mail_report
from cipherchase.sdk.settled import declared_commit, peer_declaration, settled_summaries
from cipherchase.sdk.step0 import git_commit, step0
from cipherchase.shared.gatekeeper import ApiGatekeeper

Json = dict[str, Any]


def write_league_series(
    cfg: Any, outcome: Json, directory: str | Path, *, generated_at: str,
    opponent: str, email_backend: Any = None, counted: bool = False,
) -> list[Path]:
    """Build, persist and (rule 32) auto-email one played series' reports.

    League fields key on COUNTED series only. A friendly exercises the whole
    rulebook and moves nothing: claiming a diversity reward for one is a false
    claim, and a false first meeting is a rule-38 disqualification.
    """
    # A series that did not finish has no honest report. Checked against the
    # SIGNED num_games directly, never inferred from how the loop terminated:
    # dropping unplayed windows from a report is a different fix, and having
    # shipped only that one we mailed a two-game "series tie" mid-series.
    required = int(cfg.shared["network_and_league"]["num_games"])
    settled = settled_summaries(outcome["summaries"])
    if len(settled) < required:
        missing = sorted(set(range(1, required + 1))
                         - {s["sub_game_number"] for s in settled})
        print(f"NO REPORT — {len(settled)} of {required} sub-games settled; "
              f"a partial series has no honest report (missing: {missing})")
        return []
    gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)
    ledger = Path(directory) / "opponents.json"
    history: list[str] = json.loads(ledger.read_text()) if ledger.exists() else []
    first_meeting = opponent != cfg.private["game"]["group_id"] and opponent not in history
    played = [*history, opponent] if counted else history
    # Their declared count, from the identity block they put on the wire.
    ident = peer_declaration(outcome["summaries"])
    declared = int(ident.get("counted_games_played", 0))
    peer_repos = dict(ident.get("repos", {}))
    arts = build_series_artifacts(
        cfg, outcome, opponent=opponent, generated_at=generated_at, gate=gate,
        games_played=played.count(opponent), first_meeting=first_meeting,
        # "including this": their DECLARED prior plus this game, exactly as ours
        # counts this game for us. Filing their prior unchanged puts our two
        # honest files one apart on the opponent's column.
        counted=counted, opponent_counted=declared + (1 if counted else 0),
        # Verified at every audit and dropped before the file: six sub-games
        # shipped as "unknown" while their hash was on the wire throughout.
        opponent_commits=declared_commit(settled), peer_repos=peer_repos)
    paths = emit.write_all(directory, arts)
    if counted:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps(played))
    email = cfg.private["email"]
    if email["enabled"]:
        result = next(a for a in arts if a["_schema"] == "result")
        mail_report(cfg, gate, result, email_backend or gmail_backend())
    return paths


def build_series_artifacts(
    cfg: Any, outcome: Json, *, opponent: str, generated_at: str,
    gate: ApiGatekeeper, games_played: int = 1, first_meeting: bool = False,
    counted: bool = False, opponent_counted: int = 0, commit: str = "",
    opponent_commits: Any = "unknown", peer_repos: Json | None = None,
) -> list[Json]:
    game = cfg.private["game"]
    own = game["group_id"]
    summaries = settled_summaries(outcome["summaries"])
    table = cfg.shared["scoring"]
    # A regenerated report names the commit that PLAYED, not today's HEAD.
    commit = commit or git_commit(gate)
    rows = league.subgame_rows(
        summaries, own, opponent, table, game_id=outcome["game_id"],
        # Ours is the hash the step-0 seal names; theirs is whatever they declare,
        # which we never invent on their behalf.
        commits={own: commit, opponent: opponent_commits},
        tokens={own: sum(e.get("tokens", 0) for e in gate.ledger), opponent: 0},
        clocks={s["sub_game_number"]: (s.get("started_at", ""), s.get("ended_at", ""))
                for s in summaries})
    agg = league.aggregate(rows, table["tie_score"])
    gid, uid = outcome["game_id"], outcome["game_uid"]
    common = {"game_id": gid, "game_uid": uid, "generated_at": generated_at,
              # Sibling filenames + BOTH teams' repos (rule 49). Theirs is what
              # they signed at the handshake, never a guess on their behalf.
              "links": links.links_block(
                  game_id=gid, own=own, opponent=opponent,
                  own_repos=game.get("repos", {}), peer_repos=peer_repos or {})}
    confirmed = all(s.get("audit", {}).get("passed") for s in summaries)
    agreement = {"sha256": league.series_signature(gid, agg, rows), "confirmed": confirmed}

    declaration = artifacts.build_declaration(
        **common, groups=sorted([own, opponent]), num_sub_games=len(summaries),
        max_tokens=cfg.shared["network_and_league"]["token_budget_per_series"])
    declaration["step0"] = step0(cfg, gate)
    out: list[Json] = [declaration]
    for summary in summaries:
        n = summary["sub_game_number"]
        out.append(artifacts.build_config(
            **common, sub_game=n, shared_config=cfg.shared,
            config_sha256=cfg.config_sha256))
        out.append(artifacts.build_log(
            **common, sub_game=n,
            summary={k: summary.get(k, "") for k in ("result", "winner", "steps", "role", "note")},
            records=summary.get("records", []), mutual_agreement=agreement))
    # Truthful and mutually consistent, or it is a rule-38 project-level
    # disqualification — the bonus rides on the first meeting, never a repeat.
    # In `final_result`, per-group, where the book's example result carries them:
    # one location and one shape, so two honest files cannot look contradictory.
    final = {
        **agg,
        "games_played_including_this": {own: games_played, opponent: opponent_counted},
        # Mode-independent, per imreeyal: "is this pairing in our COUNTED ledger?"
        # One derivation for both run modes — the field means the same thing on a
        # friendly as on a counted series. The reward, unlike the fact, is earned
        # only by a counted first meeting.
        "first_meeting_between_groups": first_meeting,
        # Per-group, like every other counter in this block: a reward is a thing
        # a GROUP earns, so a scalar cannot say who earned it — and it is earned
        # by WINNING a counted first meeting, so the loser's column is False.
        "diversity_reward_applied": links.diversity(
            (own, opponent), winner=agg["winner_group"],
            first_meeting=first_meeting, counted=counted),
        "tokens_total_series": {own: sum(e.get("tokens", 0) for e in gate.ledger),
                                opponent: 0},
    }
    out.append(artifacts.build_result(
        **common, sub_games=rows, final_result=final, mutual_agreement=agreement,
        groups=sorted([own, opponent])))
    return out
