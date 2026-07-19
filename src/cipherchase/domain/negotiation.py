"""Negotiation agreement — reference wire shape (PRD_league_runtime §2.1).

``signed()`` → ``{terms, nonce, signature, identity}`` where the signature is
the frozen commit formula over the terms. ``verify_peer`` refuses on any terms
inequality or signature mismatch (no game); identity is captured, not compared.
``config_sha256`` stays the artifact/config lock used across reporting.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.canonical import canonical_json, sha256_hex
from cipherchase.domain.crypto import CommitReveal
from cipherchase.exceptions import CryptoError, HandshakeError


def config_sha256(game_json: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(game_json))


class Negotiation:
    def __init__(self, terms: dict[str, Any], identity: dict[str, Any]) -> None:
        self.terms = terms
        self.identity = identity

    def signed(self) -> dict[str, Any]:
        commit, nonce = CommitReveal.seal(self.terms)
        return {"terms": self.terms, "nonce": nonce, "signature": commit,
                "identity": self.identity}

    def verify_peer(self, message: dict[str, Any]) -> dict[str, Any]:
        """Return the peer's identity if terms match and the signature holds."""
        peer_terms = message.get("terms")
        if peer_terms != self.terms:
            raise HandshakeError("terms mismatch — no game (agree game.json pre-match)")
        try:
            CommitReveal.verify(peer_terms, message.get("nonce", ""), message.get("signature", ""))
        except CryptoError as exc:
            raise HandshakeError(f"agreement signature invalid: {exc}") from exc
        return message.get("identity", {})
