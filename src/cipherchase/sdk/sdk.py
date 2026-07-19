"""SimulationSdk — the single business entry (R1).

``run_self_match`` plays a full offline game THROUGH the gatekeeper (git hash
via ``service="subprocess"``, any LLM via ``service="llm"``), embeds the SIGNED
Step-0 declaration in the declaration artifact (F5), carries the gate ledger in
the log artifact, and — when ``[email].enabled`` — auto-emails the 4 reports
(F11). CLI and GUI hold no logic; they call here.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from cipherchase.constants import Outcome
from cipherchase.domain.board import Board
from cipherchase.domain.game_ids import game_id, game_uid
from cipherchase.peer.summary import full_audit
from cipherchase.report import artifacts, emit
from cipherchase.report.mutual_signature import mutual_signature
from cipherchase.sdk.game_loop import GameResult, run_game
from cipherchase.sdk.step0 import step0
from cipherchase.shared.gatekeeper import ApiGatekeeper

_WINNER = {Outcome.CAPTURE: "police", Outcome.SURVIVAL: "thief", Outcome.TIE: "tie"}


class SimulationSdk:
    @staticmethod
    def run_self_match(
        cfg: Any, *, generated_at: str, opponent: str = "uoh-opponent", gate: ApiGatekeeper | None = None
    ) -> dict[str, dict[str, Any]]:
        gate = gate or ApiGatekeeper.from_config(cfg, now=time.monotonic)
        result = run_game(cfg, gate=gate)
        game = cfg.private["game"]
        uid = game_uid(game["group_id"], opponent, cfg.config_sha256)
        gid = game_id(game["group_id"], cfg.role, uid)
        return _assemble(cfg, result, uid, gid, generated_at, opponent, gate)

    @staticmethod
    def run_peer(
        cfg: Any, *, natural_role: str, transport: Any = None, gate: Any = None
    ) -> dict[str, Any]:
        """Live league entry (F1/F14): validate terms → serve → play the series."""
        from cipherchase.peer.terms import validate_terms
        from cipherchase.sdk.series import run_series

        validate_terms(cfg)
        gate = gate or ApiGatekeeper.from_config(cfg, now=time.monotonic)
        if transport is None:  # pragma: no cover — real sockets (interop test covers it)
            from cipherchase.infra.mcp_client import McpTransport
            from cipherchase.infra.mcp_server import start_peer_server

            inboxes = start_peer_server(natural_role, cfg)
            transport = McpTransport.from_config(cfg, inboxes, gate=gate)
        series = run_series(cfg, natural_role, transport, gate=gate)
        return {
            "game_id": series.game_id, "game_uid": series.game_uid,
            "sub_games": [
                {k: s[k] for k in ("sub_game_number", "role", "result", "winner", "steps", "audit")}
                for s in series.summaries
            ],
            "summaries": series.summaries,
        }

    @staticmethod
    def write_reports(
        cfg: Any, directory: str | Path, *, generated_at: str, email_backend: Any = None
    ) -> list[Path]:
        gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)
        arts = SimulationSdk.run_self_match(cfg, generated_at=generated_at, gate=gate)
        paths = emit.write_all(directory, list(arts.values()))
        email = cfg.private["email"]
        if email["enabled"]:
            from cipherchase.infra.email_sender import GmailSender

            sender = GmailSender(
                gate, recipient=email["recipient"], sender=email.get("sender", ""),
                backend=email_backend,
            )
            subject = email["subject_template"].format(game_id=arts["result"]["game_id"])
            sender.send(subject, paths)
        return paths


def _assemble(
    cfg: Any, result: GameResult, uid: str, gid: str, generated_at: str, opponent: str,
    gate: ApiGatekeeper,
) -> dict[str, dict[str, Any]]:
    outcome = result.outcome.value
    final = _WINNER[result.outcome]
    scores = {"police": result.scores[0], "thief": result.scores[1]}
    board = Board(cfg.shared["board_and_agents"]["board_size"])
    verdict = "verified" if full_audit(result.records, board)["passed"] else "tamper_forfeit"
    signature = mutual_signature(
        game_uid=uid, sub_game=1, outcome=outcome, scores=scores,
        final_result=final, audit_verdict=verdict, config_sha256=cfg.config_sha256,
    )
    agreement = {"signature": signature, "audit": verdict}
    game = cfg.private["game"]
    links = game.get("repos", {})
    common = {"game_id": gid, "game_uid": uid, "generated_at": generated_at, "links": links}
    summary = {"turns": result.turns, "outcome": outcome, "gatekeeper_ledger": gate.ledger}
    declaration = artifacts.build_declaration(
        **common, groups=[game["group_id"], opponent], num_sub_games=1,
        max_tokens=cfg.shared["network_and_league"]["token_budget_per_series"],
    )
    declaration["step0"] = step0(cfg, gate)
    return {
        "declaration": declaration,
        "config": artifacts.build_config(
            **common, sub_game=1, shared_config=cfg.shared, config_sha256=cfg.config_sha256
        ),
        "log": artifacts.build_log(
            **common, sub_game=1, summary=summary,
            records=result.records, mutual_agreement=agreement,
        ),
        "result": artifacts.build_result(
            **common, sub_games=[{"sub_game": 1, "outcome": outcome, "scores": scores}],
            final_result=final, mutual_agreement=agreement,
        ),
    }
