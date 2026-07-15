"""Symmetric mutual signature (FR-G1, ADR-009).

Hashes ONLY the symmetric game outcome — never peer-private fields — so both
peers independently compute a byte-identical signature. This is the shared
proof both sides attach to their reports (both send or neither is scored).
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.canonical import canonical_json, sha256_hex


def mutual_signature(
    *,
    game_uid: str,
    sub_game: int,
    outcome: str,
    scores: dict[str, int],
    final_result: str,
    audit_verdict: str,
    config_sha256: str,
) -> str:
    symmetric: dict[str, Any] = {
        "game_uid": game_uid,
        "sub_game": sub_game,
        "outcome": outcome,
        "scores": {role: scores[role] for role in sorted(scores)},
        "final_result": final_result,
        "audit_verdict": audit_verdict,
        "config_sha256": config_sha256,
    }
    return sha256_hex(canonical_json(symmetric))
