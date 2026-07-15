"""Negotiate + sign + verify the shared game.json (FR-I1, F14).

Both peers must sign a byte-identical constitution; a signature mismatch
refuses the match (constant-time comparison via ``secrets.compare_digest``).
"""

from __future__ import annotations

import secrets
from typing import Any

from cipherchase.domain.canonical import canonical_json, sha256_hex
from cipherchase.exceptions import HandshakeError


def config_sha256(game_json: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(game_json))


def sign_agreement(game_json: dict[str, Any]) -> dict[str, Any]:
    return {"config": game_json, "config_sha256": config_sha256(game_json)}


def verify_agreement(local: dict[str, Any], remote: dict[str, Any]) -> str:
    """Return the shared config hash, or raise if the two configs differ."""
    local_sha = config_sha256(local)
    remote_sha = config_sha256(remote)
    if not secrets.compare_digest(local_sha, remote_sha):
        raise HandshakeError(f"config mismatch: {local_sha} != {remote_sha}")
    return local_sha
