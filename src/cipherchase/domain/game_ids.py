"""Deterministic game identifiers (FR-B, F11).

``derive_game_ids`` is the REFERENCE formula (PRD_league_runtime §2.1): both
peers derive identical ids from the agreed terms + sorted group ids, no extra
round-trip. The older ``game_uid``/``game_id`` remain for offline reporting.
"""

from __future__ import annotations

import hashlib
import uuid

from cipherchase.domain.canonical import canonical_json, sha256_hex


def derive_game_ids(terms: dict, group_a: str, group_b: str) -> tuple[str, str]:
    lo, hi = sorted([group_a, group_b])
    game_id = f"{lo}-vs-{hi}"
    seed = canonical_json(terms) + f"|{lo}|{hi}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:16]
    return game_id, str(uuid.UUID(bytes=digest))


def game_uid(group_a: str, group_b: str, config_sha256: str) -> str:
    payload = {"groups": sorted([group_a, group_b]), "config": config_sha256}
    return sha256_hex(canonical_json(payload))[:16]


def game_id(group_id: str, role: str, uid: str) -> str:
    return f"{group_id}-{role}-{uid[:8]}"
