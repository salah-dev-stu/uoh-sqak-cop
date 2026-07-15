"""Symmetric mutual signature — identical on both peers (FR-G1, ADR-009)."""

from __future__ import annotations

from cipherchase.report.mutual_signature import mutual_signature

SYMMETRIC = {
    "game_uid": "abc123",
    "sub_game": 1,
    "outcome": "capture",
    "scores": {"police": 20, "thief": 5},
    "final_result": "police",
    "audit_verdict": "verified",
    "config_sha256": "deadbeef",
}


def test_both_peers_produce_identical_signature() -> None:
    # Peers differ in private data but agree on the symmetric outcome.
    police_view = mutual_signature(**SYMMETRIC)
    thief_view = mutual_signature(**{**SYMMETRIC, "scores": {"thief": 5, "police": 20}})
    assert police_view == thief_view


def test_signature_changes_with_the_outcome() -> None:
    assert mutual_signature(**SYMMETRIC) != mutual_signature(**{**SYMMETRIC, "outcome": "survival"})
