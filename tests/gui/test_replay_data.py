"""Replay Viewer verification core (FR-G5, F12) — Verified OK / TAMPERED."""

from __future__ import annotations

from cipherchase.gui.replay_data import replay_verdict, verify_records
from cipherchase.peer.sealing import SealBook

PAYLOAD = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "N", "intent": "truth"}


def _records() -> list[dict]:
    book = SealBook()
    book.seal(PAYLOAD)
    book.seal({**PAYLOAD, "step": 2, "move": "S"})
    return book.records()


def test_clean_log_verifies_every_step() -> None:
    steps = verify_records(_records())
    assert [s["status"] for s in steps] == ["Verified OK", "Verified OK"]
    assert replay_verdict(_records()) == "Verified OK"


def test_tampered_step_is_flagged() -> None:
    records = _records()
    records[1]["payload"]["move"] = "W"  # forged after commit
    steps = verify_records(records)
    assert steps[0]["status"] == "Verified OK"
    assert steps[1]["status"] == "TAMPERED"
    assert replay_verdict(records) == "TAMPERED"
