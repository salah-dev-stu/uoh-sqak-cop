"""Milestone S6: commit → reveal (nonce hidden) → mutual audit end to end."""

from __future__ import annotations

from fakes.fake_transport import make_pair

from cipherchase.peer.sealing import SealBook
from cipherchase.peer.summary import audit_opponent, is_tamper_forfeit
from cipherchase.peer.turn_handler import receive_turn, reveal_matches_commit
from cipherchase.peer.turn_sender import send_commit, send_reveal

PAYLOAD = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "S", "intent": "truth"}


def test_commit_hides_move_then_reveal_and_audit_pass() -> None:
    a, b = make_pair()
    book = SealBook()

    nonce = send_commit(a, book, step=1, sender="police", payload=PAYLOAD)
    committed = receive_turn(b, timeout=0.5)
    assert committed.commit  # B sees a hash...
    assert committed.move is None and nonce not in committed.to_dict().values()  # ...not the move/nonce

    send_reveal(a, step=1, sender="police", commit=committed.commit, move="S", intent="truth")
    revealed = receive_turn(b, timeout=0.5)
    assert revealed.move == "S"
    assert reveal_matches_commit(committed, revealed)

    a.send_audit(book.audit_payload("police", "survival").to_dict())
    result = audit_opponent(b.poll_audit(timeout=0.5))
    assert result["passed"] is True


def test_tampered_reveal_is_caught_by_audit_as_forfeit() -> None:
    a, b = make_pair()
    book = SealBook()
    send_commit(a, book, step=1, sender="police", payload=PAYLOAD)
    audit = book.audit_payload("police", "capture").to_dict()
    audit["records"][0]["payload"]["move"] = "N"  # forge the move after committing
    assert is_tamper_forfeit(audit_opponent(audit)) is True
