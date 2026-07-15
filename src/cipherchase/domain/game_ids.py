"""Deterministic game identifiers (FR-B, F11).

``game_uid`` is symmetric — both peers derive the *same* series id from the
sorted group names + the signed config hash. ``game_id`` is per-peer (role
differs) but shares the uid so the paired reports link up.
"""

from __future__ import annotations

from cipherchase.domain.canonical import canonical_json, sha256_hex


def game_uid(group_a: str, group_b: str, config_sha256: str) -> str:
    payload = {"groups": sorted([group_a, group_b]), "config": config_sha256}
    return sha256_hex(canonical_json(payload))[:16]


def game_id(group_id: str, role: str, uid: str) -> str:
    return f"{group_id}-{role}-{uid[:8]}"
