"""End-of-game mutual audit (FR-F3, F4).

Each peer re-hashes the OTHER's revealed records. Any mismatch means the log was
forged after commit → the forging side takes ``tamper_forfeit`` (0/0). Trust is
mathematical, not judgemental.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.crypto import audit_records


def audit_opponent(audit_payload: dict[str, Any]) -> dict[str, Any]:
    return audit_records(audit_payload.get("records", []))


def is_tamper_forfeit(audit_result: dict[str, Any]) -> bool:
    return not audit_result["passed"]
