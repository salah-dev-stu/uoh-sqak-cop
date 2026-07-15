"""Step-0 signed fairness declaration (FR-F4, F5).

A per-game JSON attesting hardware, LLM model, team/players, and the GitHub
commit hash for that game, signed with SHA-256 over its canonical body so any
post-hoc edit is detectable.
"""

from __future__ import annotations

import secrets
from typing import Any


def sign_declaration(body: dict[str, Any]) -> str:
    from cipherchase.domain.canonical import canonical_json, sha256_hex

    unsigned = {k: v for k, v in body.items() if k != "signature"}
    return sha256_hex(canonical_json(unsigned))


def build_declaration(
    *,
    team: str,
    players: list[str],
    role: str,
    git_commit: str,
    llm: dict[str, Any],
    system: dict[str, Any],
    version: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": "declaration/1.0",
        "team": team,
        "players": players,
        "role": role,
        "git_commit": git_commit,
        "llm": llm,
        "system": system,
        "version": version,
    }
    body["signature"] = sign_declaration(body)
    return body


def verify_declaration(declaration: dict[str, Any]) -> bool:
    claimed = declaration.get("signature", "")
    return secrets.compare_digest(claimed, sign_declaration(declaration))
