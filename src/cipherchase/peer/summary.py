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
from cipherchase.peer.sealing import now_iso

NO_AUDIT_RESULTS = {"timeout", "stopped", "error", "quit", "opponent_quit",
                    "handshake_failed", "restart"}


def _fsm_step(rt: Any, target: Any) -> None:
    """Advance the runtime FSM if legal — the terminal edge is tolerant (F9)."""
    machine = getattr(rt, "sm", None)
    if machine is not None and machine.can(target):
        machine.transition(target)


# The step-0 record types that may carry a peer's revision. Two spellings are in
# circulation — ours and the book-attached log shape (rule 53) — and anrbj666
# filed our commit correctly while we filed theirs as "unknown" for a whole
# series, purely because we read one name and they seal the other. Closed set:
# an unrecognised type must never be mined for a hash we would file as theirs.
STEP_ZERO_TYPES = ("system_spec", "step_zero")


def peer_commit(payload: dict[str, Any] | None) -> str:
    """The revision named by THEIR step-0 seal, or "" if they declared none.

    We already re-hash every record they reveal, so this hash arrives verified
    and is then thrown away — our result file said "unknown" for six sub-games
    whose commits had been on the wire throughout. Never invented on their
    behalf: an opponent who declares nothing is recorded as declaring nothing.
    """
    for record in (payload or {}).get("records", []):
        spec = record.get("payload", {})
        if spec.get("type") in STEP_ZERO_TYPES and spec.get("github_commit"):
            return str(spec["github_commit"])
    return ""


def finish(rt: Any, result: tuple[str, str], note: str = "") -> dict[str, Any]:
    from cipherchase.peer.state_machine import State

    _fsm_step(rt, State.TECHNICAL_LOSS if result[0] in NO_AUDIT_RESULTS else State.AUDIT)
    audit: dict[str, Any] = {"status": "skipped", "passed": None}
    final, their_commit = result, ""
    if result[0] not in NO_AUDIT_RESULTS:
        payload = AuditPayload(
            sender=rt.role, records=rt.book.records(), result_claim=result[0]
        ).to_dict()
        import contextlib

        with contextlib.suppress(Exception):  # best-effort — winner may be exiting
            rt.transport.send_audit(payload)
        theirs = rt.transport.poll_audit_or_none(rt.cfg.network["connect_timeout_seconds"])
        if theirs is not None:
            their_commit = peer_commit(theirs)
            verdict = audit_records(list(theirs.get("records", [])))
            audit = {"status": "done", "passed": verdict["passed"],
                     "failed_steps": verdict["failed_steps"]}
            if not verdict["passed"]:  # iron rule: forger loses regardless of board
                final = ("tamper_forfeit", rt.role)
    _fsm_step(rt, State.REPORTING)
    return {
        "result": final[0], "winner": final[1], "steps": rt.step_number,
        "sub_game_number": rt.sub_game_number, "role": rt.role,
        "game_id": rt.game_id, "game_uid": rt.game_uid, "audit": audit,
        "records": rt.book.records(), "history": rt.history, "note": note,
        # The opponent's own declaration, carried through to the report: rules
        # 37-38 make the game count a MUTUAL declaration, so we must file THEIR
        # number rather than a zero we invented on their behalf.
        "peer_identity": dict(getattr(rt, "peer_identity", {}) or {}),
        # Verified at the audit and carried to the report, so the result names
        # the revision that actually played on BOTH sides (anrbj666, instance 5).
        "peer_commit": their_commit,
        "started_at": getattr(rt, "started_at", ""), "ended_at": now_iso(),
        "fsm": getattr(rt, "sm", None).state.name if getattr(rt, "sm", None) else "",
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
