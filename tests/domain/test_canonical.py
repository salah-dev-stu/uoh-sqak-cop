"""Canonical JSON + SHA-256 (PLAN §8.1) — byte-exact, interop-critical."""

from __future__ import annotations

from cipherchase.domain.canonical import canonical_json, sha256_hex


def test_canonical_json_sorts_keys_and_is_compact() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_json_keeps_unicode_not_escaped() -> None:
    assert canonical_json({"x": "é"}) == '{"x":"é"}'


def test_canonical_json_nested_deterministic() -> None:
    obj = {"z": [3, 1], "a": {"n": 1, "m": 2}}
    assert canonical_json(obj) == '{"a":{"m":2,"n":1},"z":[3,1]}'


def test_sha256_hex_known_vector() -> None:
    # SHA-256("abc") — standard test vector.
    assert sha256_hex("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
