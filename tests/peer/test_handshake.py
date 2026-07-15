"""Pre-game handshake: exchange + lock the signed config (FR-I1, F14)."""

from __future__ import annotations

import pytest

from cipherchase.domain.negotiation import config_sha256
from cipherchase.exceptions import HandshakeError
from cipherchase.peer.handshake import perform_handshake


class _StubNegotiator:
    def __init__(self, reply: dict) -> None:
        self.reply = reply
        self.sent: dict | None = None

    def negotiate(self, message: dict) -> dict:
        self.sent = message
        return self.reply


def test_handshake_returns_shared_hash_on_agreement() -> None:
    cfg = {"board_size": 7, "scoring": {"capture_cop": 20}}
    stub = _StubNegotiator({"config": cfg, "config_sha256": config_sha256(cfg)})
    assert perform_handshake(stub, cfg) == config_sha256(cfg)
    assert stub.sent["config_sha256"] == config_sha256(cfg)  # we signed + sent ours


def test_handshake_rejects_config_mismatch() -> None:
    stub = _StubNegotiator({"config": {"board_size": 5}})
    with pytest.raises(HandshakeError):
        perform_handshake(stub, {"board_size": 7})


def test_handshake_rejects_missing_config() -> None:
    with pytest.raises(HandshakeError):
        perform_handshake(_StubNegotiator({}), {"board_size": 7})
