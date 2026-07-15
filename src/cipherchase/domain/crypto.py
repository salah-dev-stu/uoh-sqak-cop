"""Commit-Reveal + mutual audit (FR-F1/F3). Interop-frozen (PLAN §8.1).

``commit = SHA256(canonical_json(payload) + "|" + nonce)`` with a
``secrets.token_hex(16)`` nonce, verified in constant time. The nonce stays
hidden until the end-of-game audit re-hashes every step; any mismatch (an
altered log or a post-commit move change) fails the audit → tamper_forfeit 0/0.
"""

from __future__ import annotations

import secrets
from typing import Any

from cipherchase.domain.canonical import canonical_json, sha256_hex
from cipherchase.exceptions import CryptoError

NONCE_BYTES = 16


class CommitReveal:
    @staticmethod
    def commit_of(payload: dict[str, Any], nonce: str) -> str:
        return sha256_hex(canonical_json(payload) + "|" + nonce)

    @staticmethod
    def seal(payload: dict[str, Any]) -> tuple[str, str]:
        """Return ``(commit, nonce)`` with a fresh cryptographic nonce."""
        nonce = secrets.token_hex(NONCE_BYTES)
        return CommitReveal.commit_of(payload, nonce), nonce

    @staticmethod
    def verify(payload: dict[str, Any], nonce: str, commit: str) -> None:
        """Raise ``CryptoError`` unless ``commit`` matches the re-hashed payload."""
        expected = CommitReveal.commit_of(payload, nonce)
        if not secrets.compare_digest(expected, commit):
            raise CryptoError(f"commit mismatch at nonce {nonce[:8]}…")


def audit_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-hash every ``{payload, nonce, commit}`` step; report pass/fail indices."""
    verified: list[int] = []
    failed: list[int] = []
    for index, record in enumerate(records):
        try:
            CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
            verified.append(index)
        except (CryptoError, KeyError):
            failed.append(index)
    return {"passed": not failed, "verified_steps": verified, "failed_steps": failed}
