"""Sign + verify the shared game.json constitution (FR-I1, F14)."""

from __future__ import annotations

import pytest

from cipherchase.domain import negotiation
from cipherchase.exceptions import HandshakeError


def test_config_sha_is_key_order_independent() -> None:
    assert negotiation.config_sha256({"a": 1, "b": 2}) == negotiation.config_sha256(
        {"b": 2, "a": 1}
    )


def test_sign_agreement_embeds_matching_hash() -> None:
    signed = negotiation.sign_agreement({"board_size": 7})
    assert signed["config_sha256"] == negotiation.config_sha256({"board_size": 7})
    assert signed["config"] == {"board_size": 7}


def test_verify_agreement_returns_shared_hash_on_match() -> None:
    cfg = {"board_size": 7, "scoring": {"capture_cop": 20}}
    shared = negotiation.verify_agreement(cfg, dict(cfg))
    assert shared == negotiation.config_sha256(cfg)


def test_verify_agreement_rejects_mismatch() -> None:
    with pytest.raises(HandshakeError):
        negotiation.verify_agreement({"board_size": 7}, {"board_size": 5})
