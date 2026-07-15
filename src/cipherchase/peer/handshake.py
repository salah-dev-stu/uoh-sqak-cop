"""Pre-game handshake — exchange + lock the signed game.json (FR-I1, F14).

Both peers sign their config and swap it via the ``negotiate`` tool; the match
only proceeds if the two constitutions are byte-identical (verified hash).
"""

from __future__ import annotations

from typing import Any, Protocol

from cipherchase.domain.negotiation import sign_agreement, verify_agreement
from cipherchase.exceptions import HandshakeError


class Negotiator(Protocol):
    def negotiate(self, message: dict[str, Any]) -> dict[str, Any]: ...


def perform_handshake(transport: Negotiator, local_config: dict[str, Any]) -> str:
    """Return the shared config hash once both peers agree, else raise."""
    reply = transport.negotiate(sign_agreement(local_config))
    remote = reply.get("config")
    if remote is None:
        raise HandshakeError("negotiate reply carried no config")
    return verify_agreement(local_config, remote)
