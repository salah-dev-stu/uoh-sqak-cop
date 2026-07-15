"""Commit-Reveal + mutual audit (FR-F1/F3, F3/F4). Byte-exact, interop-frozen."""

from __future__ import annotations

import hashlib
import json

import pytest

from cipherchase.domain.crypto import CommitReveal, audit_records
from cipherchase.exceptions import CryptoError

PAYLOAD = {"step": 1, "state": {"pos": [0, 0], "barriers": []}, "move": "N", "intent": "truth"}


def test_commit_matches_independent_sha256_golden_vector() -> None:
    nonce = "ab" * 16  # 32 hex chars
    canon = json.dumps(PAYLOAD, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    expected = hashlib.sha256((canon + "|" + nonce).encode("utf-8")).hexdigest()
    assert CommitReveal.commit_of(PAYLOAD, nonce) == expected


def test_seal_then_verify_round_trip() -> None:
    commit, nonce = CommitReveal.seal(PAYLOAD)
    assert len(nonce) == 32
    CommitReveal.verify(PAYLOAD, nonce, commit)  # no raise


def test_verify_rejects_wrong_nonce_or_tampered_payload() -> None:
    commit, nonce = CommitReveal.seal(PAYLOAD)
    with pytest.raises(CryptoError):
        CommitReveal.verify(PAYLOAD, "00" * 16, commit)
    tampered = {**PAYLOAD, "move": "S"}
    with pytest.raises(CryptoError):
        CommitReveal.verify(tampered, nonce, commit)


def _record(payload: dict) -> dict:
    commit, nonce = CommitReveal.seal(payload)
    return {"payload": payload, "nonce": nonce, "commit": commit}


def test_audit_passes_clean_log() -> None:
    records = [_record(PAYLOAD), _record({**PAYLOAD, "step": 2, "move": "S"})]
    result = audit_records(records)
    assert result["passed"] is True
    assert result["failed_steps"] == []


def test_audit_fails_a_post_commit_move_change() -> None:
    records = [_record(PAYLOAD), _record({**PAYLOAD, "step": 2})]
    records[1]["payload"]["move"] = "W"  # altered after commit → hash mismatch
    result = audit_records(records)
    assert result["passed"] is False
    assert 1 in result["failed_steps"]
