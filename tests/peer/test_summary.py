"""End-of-game mutual audit → tamper_forfeit (FR-F3, F4)."""

from __future__ import annotations

from cipherchase.domain.board import Board
from cipherchase.peer.sealing import SealBook
from cipherchase.peer.summary import audit_opponent, full_audit, is_tamper_forfeit

PAYLOAD = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "N", "intent": "truth"}


def _clean_audit() -> dict:
    book = SealBook()
    book.seal(PAYLOAD)
    book.seal({**PAYLOAD, "step": 2, "move": "S"})
    return book.audit_payload("thief", "survival").to_dict()


def test_clean_opponent_log_passes_audit() -> None:
    result = audit_opponent(_clean_audit())
    assert result["passed"] is True
    assert is_tamper_forfeit(result) is False


def test_tampered_opponent_log_triggers_forfeit() -> None:
    audit = _clean_audit()
    audit["records"][1]["payload"]["move"] = "W"  # altered after commit
    result = audit_opponent(audit)
    assert result["passed"] is False
    assert is_tamper_forfeit(result) is True


def test_full_audit_catches_a_hash_valid_but_illegal_move() -> None:
    # A move that is off-board but correctly hashed: hash passes, physical fails.
    book = SealBook()
    book.seal({"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "N", "intent": "truth"})
    result = full_audit(book.records(), Board(7))
    assert result["hash"]["passed"] is True
    assert result["physical"]["passed"] is False
    assert is_tamper_forfeit(result) is True
