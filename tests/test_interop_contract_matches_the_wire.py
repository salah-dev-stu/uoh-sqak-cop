"""The contract we HAND OUT must be the terms we actually send.

We published docs/INTEROP-CONTRACT.md with a terms block that had drifted from
config on four values (min_center_intensity, setting, hint_max_words,
axis_origin_corner). Team ahk-yosi read it, found their own stack already
matched us on all four, and politely offered to "adopt" our documented numbers
— which would have replaced four correct values with four wrong ones. Their
verify_peer compares terms by exact dict equality, so the first handshake would
have failed on every one of them.

A prose document describing bytes is a cache, and this one was stale. The terms
block is now checked against terms_from_config, so the document cannot drift
from the wire without failing the build.
"""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.peer.terms import terms_from_config
from cipherchase.shared.config import ConfigManager

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "INTEROP-CONTRACT.md"


def published_terms() -> dict:
    """The `terms` object as an opponent reads it out of our contract."""
    text = CONTRACT.read_text()
    start = text.index('"terms":') + len('"terms":')
    depth, end = 0, None
    for i, ch in enumerate(text[start:], start):
        depth += (ch == "{") - (ch == "}")
        if depth == 0 and ch == "}":
            end = i + 1
            break
    assert end is not None, "the contract's terms block is not brace-balanced"
    return json.loads(text[start:end])


def test_the_published_terms_are_the_terms_we_put_on_the_wire() -> None:
    wire = terms_from_config(ConfigManager.load(ROOT / "config" / "thief"))
    published = published_terms()
    assert published == wire, (
        "docs/INTEROP-CONTRACT.md would make an opponent negotiate terms we do "
        f"not send:\n  published: {json.dumps(published, sort_keys=True)}\n"
        f"  wire:      {json.dumps(wire, sort_keys=True)}")


def test_both_roles_publish_the_same_terms() -> None:
    # The terms are the shared contract; a per-role difference would mean the
    # two halves of one team negotiate different games.
    police = terms_from_config(ConfigManager.load(ROOT / "config" / "police"))
    thief = terms_from_config(ConfigManager.load(ROOT / "config" / "thief"))
    assert police == thief
