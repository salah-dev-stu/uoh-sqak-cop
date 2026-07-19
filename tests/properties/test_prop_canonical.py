"""IC-8: canonical_json is key-order independent and idempotent through a parse."""

from __future__ import annotations

import json

from hypothesis import given

from cipherchase.domain.canonical import canonical_json, sha256_hex
from properties.strategies import payloads


def _reordered(obj):
    """Rebuild dicts with their items reversed (recursively) — a different key order."""
    if isinstance(obj, dict):
        return {k: _reordered(v) for k, v in reversed(list(obj.items()))}
    if isinstance(obj, list):
        return [_reordered(v) for v in obj]
    return obj


@given(payloads)
def test_key_order_does_not_change_canonical_bytes(payload) -> None:
    assert canonical_json(payload) == canonical_json(_reordered(payload))


@given(payloads)
def test_canonical_survives_a_parse_cycle(payload) -> None:
    once = canonical_json(payload)
    assert json.loads(once) == payload
    assert canonical_json(json.loads(once)) == once  # idempotent through parse


@given(payloads)
def test_hash_follows_canonical_equality(payload) -> None:
    assert sha256_hex(canonical_json(payload)) == sha256_hex(canonical_json(_reordered(payload)))
