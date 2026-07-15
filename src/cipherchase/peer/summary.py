"""End-of-game mutual audit (FR-F3, F4).

Each peer re-hashes the OTHER's revealed records. Any mismatch means the log was
forged after commit → the forging side takes ``tamper_forfeit`` (0/0). Trust is
mathematical, not judgemental.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.board import Board
from cipherchase.domain.crypto import audit_records
from cipherchase.domain.physical_audit import physical_audit


def audit_opponent(audit_payload: dict[str, Any]) -> dict[str, Any]:
    return audit_records(audit_payload.get("records", []))


def full_audit(records: list[dict[str, Any]], board: Board) -> dict[str, Any]:
    """Hash-integrity AND physical-legality — a forfeit if either fails (F3/F4)."""
    hash_result = audit_records(records)
    physical_result = physical_audit(records, board)
    return {
        "passed": hash_result["passed"] and physical_result["passed"],
        "hash": hash_result,
        "physical": physical_result,
    }


def is_tamper_forfeit(audit_result: dict[str, Any]) -> bool:
    return not audit_result["passed"]
