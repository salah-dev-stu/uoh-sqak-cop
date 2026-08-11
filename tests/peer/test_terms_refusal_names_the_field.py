"""A terms refusal must name the field, not the category (vibecode, 2026-08-12).

We refused vibecode's agreements with "terms mismatch — no game (agree
game.json pre-match)" while every term we captured off the wire was identical
to ours. The message told us the category and nothing else, so we could not
tell a real value difference from a type difference, an extra key, or a bug in
our own comparison — mid-match, with the clock running.

This is the instrument we told two other teams to build. "Constitution
mismatch" ends nothing; "hint_max_words 15 vs 30" ends the investigation.
"""

from __future__ import annotations

from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError

IDENT = {"group_id": "them"}


def _refuse(theirs: dict) -> str:
    ours = Negotiation({"board_size": 7, "max_steps": 35}, IDENT)
    try:
        ours.verify_peer({"terms": theirs, "nonce": "x", "signature": "y"})
    except HandshakeError as exc:
        return str(exc)
    raise AssertionError("a terms difference must refuse")


def test_a_differing_value_is_named_with_both_sides() -> None:
    message = _refuse({"board_size": 7, "max_steps": 30})
    assert "max_steps" in message and "35" in message and "30" in message, message
    assert "board_size" not in message, "only the fields that DIFFER are named"


def test_a_missing_or_extra_field_is_named_too() -> None:
    missing = _refuse({"board_size": 7})
    assert "max_steps" in missing and "absent" in missing.lower(), missing
    extra = _refuse({"board_size": 7, "max_steps": 35, "setting": "New York"})
    assert "setting" in extra, extra


def test_identical_terms_reach_the_signature_check_instead() -> None:
    # The case that cost us tonight: if the terms really are equal, the refusal
    # must come from somewhere else and say so, never from the terms comparison.
    message = _refuse({"board_size": 7, "max_steps": 35})
    assert "terms mismatch" not in message, message
    assert "signature" in message.lower(), message


def test_a_non_object_terms_field_is_described_not_crashed_on() -> None:
    # A peer sending terms as a string or null must get a refusal, never an
    # exception from the code that explains the refusal — the diff runs on the
    # error path, which is exactly where a second failure is worst.
    assert "not an object" in _refuse(None)
    assert "str" in _refuse("7x7")
