"""End-of-game mutual audit + live-match finish (FR-F3, F4, §2.5).

Each peer re-hashes the OTHER's revealed records — hash-only and lenient about
foreign payload schemas (the reference contract). Any mismatch → the forging
side takes ``tamper_forfeit``. ``finish`` runs the live audit exchange:
best-effort push, always read own inbox; timeout/error results skip the audit.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.board import Board
from cipherchase.domain.crypto import audit_records
from cipherchase.domain.physical_audit import physical_audit
from cipherchase.domain.protocol import AuditPayload

NO_AUDIT_RESULTS = {"timeout", "stopped", "error", "quit", "opponent_quit", "handshake_failed"}


def finish(rt: Any, result: tuple[str, str], note: str = "") -> dict[str, Any]:
    audit: dict[str, Any] = {"status": "skipped", "passed": None}
    final = result
    if result[0] not in NO_AUDIT_RESULTS:
        payload = AuditPayload(
            sender=rt.role, records=rt.book.records(), result_claim=result[0]
        ).to_dict()
        import contextlib

        with contextlib.suppress(Exception):  # best-effort — winner may be exiting
            rt.transport.send_audit(payload)
        theirs = rt.transport.poll_audit_or_none(rt.cfg.network["connect_timeout_seconds"])
        if theirs is not None:
            verdict = audit_records(list(theirs.get("records", [])))
            audit = {"status": "done", "passed": verdict["passed"],
                     "failed_steps": verdict["failed_steps"]}
            if not verdict["passed"]:  # iron rule: forger loses regardless of board
                final = ("tamper_forfeit", rt.role)
    return {
        "result": final[0], "winner": final[1], "steps": rt.step_number,
        "sub_game_number": rt.sub_game_number, "role": rt.role,
        "game_id": rt.game_id, "game_uid": rt.game_uid, "audit": audit,
        "records": rt.book.records(), "history": rt.history, "note": note,
    }


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
