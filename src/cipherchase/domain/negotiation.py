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


_MODELS = ("scent_model_sha256", "info_mode_sha256")


class Negotiation:
    def __init__(
        self, terms: dict[str, Any], identity: dict[str, Any], *,
        sub_game_number: int | None = None, role: str = "", game_uid: str = "",
        scent_model_sha256: str = "", info_mode_sha256: str = "",
    ) -> None:
        self.terms = terms
        self.identity = identity
        # Declared context (SPEC §3.7). Terms equality cannot catch a role
        # collision or a sub-game desync — those hand you a perfect handshake
        # and a deadlock. Declaring costs nothing and refuses early.
        self.context: dict[str, Any] = {
            "sub_game_number": sub_game_number, "role": role, "game_uid": game_uid,
            "scent_model_sha256": scent_model_sha256, "info_mode_sha256": info_mode_sha256,
        }
        self.context = {k: v for k, v in self.context.items() if v not in (None, "")}

    def signed(self) -> dict[str, Any]:
        commit, nonce = CommitReveal.seal(self.terms)
        return {"terms": self.terms, "nonce": nonce, "signature": commit,
                "identity": self.identity, **self.context}

    def verify_peer(self, message: dict[str, Any]) -> dict[str, Any]:
        """Return the peer's identity if terms match and the signature holds."""
        peer_terms = message.get("terms")
        if peer_terms != self.terms:
            raise HandshakeError("terms mismatch — no game (agree game.json pre-match)")
        try:
            CommitReveal.verify(peer_terms, message.get("nonce", ""), message.get("signature", ""))
        except CryptoError as exc:
            raise HandshakeError(f"agreement signature invalid: {exc}") from exc
        self._check_context(message)
        return message.get("identity", {})

    def _check_context(self, message: dict[str, Any]) -> None:
        """Refuse a declared contradiction; an omission is never a refusal."""
        mine, role = self.context, self.context.get("role")
        if role and (theirs := message.get("role")) and theirs == role:
            raise HandshakeError(f"role collision — both peers declared {role}")
        for key, label in (("sub_game_number", "sub-game"), ("game_uid", "game_uid")):
            ours, peer = mine.get(key), message.get(key)
            if ours is not None and peer is not None and ours != peer:
                raise HandshakeError(f"{label} disagreement: ours {ours!r} vs theirs {peer!r}")
        for key in _MODELS:
            ours, peer = mine.get(key), message.get(key)
            if ours and peer and ours != peer:
                raise HandshakeError(f"declared model differs ({key}): {ours} vs {peer}")
