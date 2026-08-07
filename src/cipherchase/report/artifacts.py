"""The 4 signed JSON artifact builders (FR-G1, F11).

``declaration`` + ``result`` are per-series; ``config`` + ``log`` are per
sub-game. All share a ``game_uid``; each has a distinct ``game_id``. A common
base avoids duplication (R2).
"""

from __future__ import annotations

from typing import Any

from cipherchase.report import schemas

Json = dict[str, Any]


def _base(kind: str, game_id: str, game_uid: str, generated_at: str) -> Json:
    return {
        "_schema": kind,
        "schema_version": schemas.SCHEMA_VERSION,
        "game_id": game_id,
        "game_uid": game_uid,
        "generated_at": generated_at,
    }


def build_declaration(
    *, game_id: str, game_uid: str, generated_at: str,
    groups: list[str], num_sub_games: int, max_tokens: int, links: Json,
    timezone: str = schemas.DEFAULT_TIMEZONE,
) -> Json:
    return {
        **_base(schemas.DECLARATION, game_id, game_uid, generated_at),
        "timezone": timezone, "groups": groups,
        "num_sub_games": num_sub_games, "max_tokens": max_tokens, "links": links,
    }


def build_config(
    *, game_id: str, game_uid: str, generated_at: str,
    sub_game: int, shared_config: Json, config_sha256: str, links: Json,
) -> Json:
    return {
        **_base(schemas.CONFIG, game_id, game_uid, generated_at),
        # `sub_game_number` is the book's own term (p131) and the reference's key;
        # the league Gate-3 checker requires it. `sub_game` kept as a legacy alias.
        "sub_game_number": sub_game, "sub_game": sub_game, "config": shared_config,
        "config_sha256": config_sha256, "links": links,
    }


def build_log(
    *, game_id: str, game_uid: str, generated_at: str,
    sub_game: int, summary: Json, records: list[Json], mutual_agreement: Json, links: Json,
) -> Json:
    return {
        **_base(schemas.LOG, game_id, game_uid, generated_at),
        "sub_game": sub_game, "summary": summary,
        "records": records, "mutual_agreement": mutual_agreement, "links": links,
    }


def build_result(
    *, game_id: str, game_uid: str, generated_at: str,
    sub_games: list[Json], final_result: str, mutual_agreement: Json, links: Json,
    groups: list[str] | None = None,
) -> Json:
    return {
        **_base(schemas.RESULT, game_id, game_uid, generated_at),
        "report_type": "final_game_result", "timezone": schemas.DEFAULT_TIMEZONE,
        "groups": list(groups or []), "num_sub_games": len(sub_games),
        "sub_games": sub_games, "final_result": final_result,
        "mutual_agreement": mutual_agreement, "links": links,
    }
