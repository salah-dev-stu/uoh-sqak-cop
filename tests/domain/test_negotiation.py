"""config_sha256 lock (FR-I1). The Negotiation class is covered in tests/peer/."""

from __future__ import annotations

from cipherchase.domain.negotiation import config_sha256


def test_config_sha_is_key_order_independent() -> None:
    assert config_sha256({"a": 1, "b": 2}) == config_sha256({"b": 2, "a": 1})


def test_config_sha_changes_with_content() -> None:
    assert config_sha256({"a": 1}) != config_sha256({"a": 2})
