"""Canonical JSON + SHA-256 — the ONE serialisation reused everywhere (R2).

The commit hash (FR-F1), the ``config_sha256`` signature (FR-I1), and the
mutual signature (FR-G1) all canonicalise through here so peers produce
byte-identical bytes. Changing this is an interop-breaking change.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no spaces, unicode preserved."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    """Hex SHA-256 digest of ``text`` encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
