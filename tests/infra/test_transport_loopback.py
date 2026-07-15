"""Milestone S2: a message from peer A is received + interpreted by peer B.

Uses the in-memory FakeTransport (no live server/HTTP) — the grader path.
"""

from __future__ import annotations

import pytest
from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import AuditPayload, TurnMessage
from cipherchase.exceptions import TransportTimeoutError
from cipherchase.infra.inboxes import Inboxes


def test_turn_from_a_is_interpreted_by_b() -> None:
    a, b = make_pair()
    sent = TurnMessage(step=1, sender="police", move="S", commit="c0").to_dict()
    ack = a.send_turn(sent)
    assert ack["ack"] is True

    got = TurnMessage.from_dict(b.poll_turn(timeout=0.5))
    assert got.sender == "police"
    assert got.move == "S"
    assert got.commit == "c0"


def test_audit_and_control_route_to_their_channels() -> None:
    a, b = make_pair()
    a.send_audit(AuditPayload(sender="police", result_claim="capture").to_dict())
    a.send_control({"kind": "enable", "sender": "police"})
    assert b.poll_audit(timeout=0.5)["result_claim"] == "capture"
    assert b.poll_control(timeout=0.5)["kind"] == "enable"


def test_poll_times_out_when_no_message() -> None:
    a, _ = make_pair()
    with pytest.raises(TransportTimeoutError):
        a.poll_turn(timeout=0.01)


def test_make_pair_gives_independent_inboxes() -> None:
    a, b = make_pair()
    assert isinstance(a.inboxes, Inboxes)
    assert a.inboxes is not b.inboxes
