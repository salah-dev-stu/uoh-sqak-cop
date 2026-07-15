"""Commit-reveal record bookkeeping (FR-F2)."""

from __future__ import annotations

from cipherchase.domain.crypto import CommitReveal
from cipherchase.peer.sealing import SealBook

PAYLOAD = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "N", "intent": "truth"}


def test_seal_records_the_step_and_returns_commit_nonce() -> None:
    book = SealBook()
    commit, nonce = book.seal(PAYLOAD)
    assert len(nonce) == 32
    CommitReveal.verify(PAYLOAD, nonce, commit)  # no raise
    assert book.records()[0]["payload"] == PAYLOAD


def test_audit_payload_carries_all_sealed_records() -> None:
    book = SealBook()
    book.seal(PAYLOAD)
    book.seal({**PAYLOAD, "step": 2, "move": "S"})
    payload = book.audit_payload(sender="police", result_claim="capture")
    assert payload.sender == "police"
    assert len(payload.records) == 2
    assert payload.result_claim == "capture"
