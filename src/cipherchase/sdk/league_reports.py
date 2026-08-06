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
import os
import time
from pathlib import Path
from typing import Any

from cipherchase.report import artifacts, emit, league
from cipherchase.sdk.series import settles
from cipherchase.sdk.step0 import step0
from cipherchase.shared.gatekeeper import ApiGatekeeper

Json = dict[str, Any]


def write_league_series(
    cfg: Any, outcome: Json, directory: str | Path, *, generated_at: str,
    opponent: str, email_backend: Any = None,
) -> list[Path]:
    """Build, persist and (rule 32) auto-email one played series' reports."""
    gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)
    ledger = Path(directory) / "opponents.json"
    history: list[str] = json.loads(ledger.read_text()) if ledger.exists() else []
    first_meeting = opponent != cfg.private["game"]["group_id"] and opponent not in history
    played = [*history, opponent]
    arts = build_series_artifacts(
        cfg, outcome, opponent=opponent, generated_at=generated_at, gate=gate,
        games_played=played.count(opponent), first_meeting=first_meeting)
    paths = emit.write_all(directory, arts)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(played))
    email = cfg.private["email"]
    if email["enabled"]:
        _mail(cfg, gate, outcome, paths, email_backend or gmail_backend())
    return paths


def gmail_backend() -> Any:  # pragma: no cover — real credentials + network
    """The live Gmail sender, or None when no token is configured."""
    token = os.environ.get("CIPHERCHASE_GMAIL_TOKEN", "")
    if not token or not Path(token).expanduser().exists():
        return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(Path(token).expanduser()))
    service = build("gmail", "v1", credentials=creds)
    return lambda raw: service.users().messages().send(
        userId="me", body={"raw": raw}).execute()


def _mail(cfg: Any, gate: ApiGatekeeper, outcome: Json, paths: list[Path], backend: Any) -> None:
    """Auto-fire the report (rule 32), but never destroy a played series' evidence.

    A credential or quota problem must be loud and must not unwind the run: the
    artifacts describe a game that really happened, and they are the only copy.
    """
    from cipherchase.infra.email_sender import GmailSender

    email = cfg.private["email"]
    try:
        GmailSender(gate, recipient=email["recipient"], sender=email.get("sender", ""),
                    backend=backend).send(
            email["subject_template"].format(game_id=outcome["game_id"]), paths)
    except Exception as exc:  # noqa: BLE001 — any send failure, reported not raised
        print(f"REPORT NOT SENT — {type(exc).__name__}: {exc}\n"
              f"  artifacts are on disk; re-send with scripts/send_sample_report.py")


def settled_summaries(summaries: list[Json]) -> list[Json]:
    """One row per sub-game — the outcome it settled on, not its retries.

    A live series records every handshake retry, so a window that waited out 25
    attempts contributes 25 summaries. Reported verbatim they become 25 result
    rows, while the opponent's file carries one: the mutual signature is then
    computed over lists that cannot agree, and the single field both teams must
    match is the one guaranteed to differ.

    A window that never became a game contributes NO row — the opponent has no
    row for it either, since from their side it never happened. Reporting it as
    a 0/0 result would put a sub-game in our file that is absent from theirs.
    """
    latest: dict[int, Json] = {}
    for summary in summaries:
        latest[summary["sub_game_number"]] = summary  # last write wins = the settled one
    return [latest[n] for n in sorted(latest) if settles(latest[n])]


def build_series_artifacts(
    cfg: Any, outcome: Json, *, opponent: str, generated_at: str,
    gate: ApiGatekeeper, games_played: int = 1, first_meeting: bool = False,
) -> list[Json]:
    game = cfg.private["game"]
    own = game["group_id"]
    summaries = settled_summaries(outcome["summaries"])
    table = cfg.shared["scoring"]
    rows = league.subgame_rows(summaries, own, opponent, table)
    agg = league.aggregate(rows, table["tie_score"])
    gid, uid = outcome["game_id"], outcome["game_uid"]
    common = {"game_id": gid, "game_uid": uid, "generated_at": generated_at,
              "links": game.get("repos", {})}
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
    result = artifacts.build_result(
        **common, sub_games=rows, final_result=agg, mutual_agreement=agreement,
        groups=sorted([own, opponent]))
    # Truthful and mutually consistent, or it is a rule-38 project-level
    # disqualification — the bonus rides on the first meeting, never a repeat.
    result["league"] = {
        "games_played_including_this": games_played,
        "first_meeting_between_groups": first_meeting,
        "diversity_reward_applied": first_meeting,
    }
    out.append(result)
    return out
