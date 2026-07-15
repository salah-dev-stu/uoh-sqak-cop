"""SimulationSdk — the single business entry (R1).

CLI and GUI hold no logic; they call here. ``run_self_match`` plays a full
offline game and returns the 4 signed artifacts (the grader's proof); every
artifact shares one ``game_uid`` and the symmetric mutual signature.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cipherchase.constants import Outcome
from cipherchase.domain.board import Board
from cipherchase.domain.game_ids import game_id, game_uid
from cipherchase.peer.summary import full_audit
from cipherchase.report import artifacts, emit
from cipherchase.report.mutual_signature import mutual_signature
from cipherchase.sdk.game_loop import GameResult, run_game

_WINNER = {Outcome.CAPTURE: "police", Outcome.SURVIVAL: "thief", Outcome.TIE: "tie"}


class SimulationSdk:
    @staticmethod
    def run_self_match(
        cfg: Any, *, generated_at: str, opponent: str = "uoh-opponent"
    ) -> dict[str, dict[str, Any]]:
        result = run_game(cfg)
        game = cfg.private["game"]
        uid = game_uid(game["group_id"], opponent, cfg.config_sha256)
        gid = game_id(game["group_id"], cfg.role, uid)
        return _assemble(cfg, result, uid, gid, generated_at, opponent)

    @staticmethod
    def write_reports(cfg: Any, directory: str | Path, *, generated_at: str) -> list[Path]:
        arts = SimulationSdk.run_self_match(cfg, generated_at=generated_at)
        return emit.write_all(directory, list(arts.values()))


def _assemble(
    cfg: Any, result: GameResult, uid: str, gid: str, generated_at: str, opponent: str
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
    return {
        "declaration": artifacts.build_declaration(
            **common, groups=[game["group_id"], opponent], num_sub_games=1,
            max_tokens=cfg.shared["network_and_league"]["token_budget_per_series"],
        ),
        "config": artifacts.build_config(
            **common, sub_game=1, shared_config=cfg.shared, config_sha256=cfg.config_sha256
        ),
        "log": artifacts.build_log(
            **common, sub_game=1, summary={"turns": result.turns, "outcome": outcome},
            records=result.records, mutual_agreement=agreement,
        ),
        "result": artifacts.build_result(
            **common, sub_games=[{"sub_game": 1, "outcome": outcome, "scores": scores}],
            final_result=final, mutual_agreement=agreement,
        ),
    }
