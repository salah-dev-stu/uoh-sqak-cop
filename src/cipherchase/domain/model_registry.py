"""Named-model registrations (SPEC §7) — what our `*_sha256` declarations mean.

A bare hash over an ad-hoc dict makes two correct implementations of the SAME
model refuse each other, so the league fixes one doc schema — ``{family, name,
params, example}`` — and every peer hashes the published doc identically.

The docs live beside this module in ``model_registry.json``, vendored from the
league interop kit (MIT, github.com/Imreec/copthief-league-protocol) with our
own ``multiplicative_cheb`` profile appended. We hash the shipped doc rather
than pasting a digest, and a test pins the result against the kit's own copy —
so a drift between our physics and our declaration fails in CI, not on match day.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from cipherchase.domain.canonical import canonical_json, sha256_hex

_PATH = Path(__file__).with_name("model_registry.json")


@lru_cache(maxsize=1)
def _docs() -> dict[str, dict[str, Any]]:
    registered = json.loads(_PATH.read_text(encoding="utf-8"))["registered"]
    return {doc["name"]: doc for doc in registered}


def registration(name: str) -> dict[str, Any] | None:
    return _docs().get(name)


def declared_hash(name: str) -> str:
    """The `<family>_sha256` we put on the wire, or "" for an unknown model.

    An unknown name declares nothing rather than something wrong: omission never
    refuses a game, whereas a bogus hash would refuse every conforming peer.
    """
    doc = _docs().get(name)
    return sha256_hex(canonical_json(doc)) if doc else ""
