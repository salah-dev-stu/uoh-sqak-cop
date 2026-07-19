"""FakeTransport loopback: A's sealed message is interpreted by B (grader path)."""

from __future__ import annotations

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import AuditPayload, TurnMessage
from cipherchase.infra.inboxes import Inboxes


def test_turn_from_a_is_interpreted_by_b() -> None:
    a, b = make_pair()
    sent = TurnMessage(step=1, sender="police", hint="closing in", commit="c0").to_dict()
    assert a.send_turn(sent)["ok"] is True
    got = TurnMessage.from_dict(b.poll_turn_or_none(timeout=0.5))
    assert got.sender == "police" and got.hint == "closing in" and got.commit == "c0"


def test_audit_control_and_agreement_route_to_their_channels() -> None:
    a, b = make_pair()
    a.send_audit(AuditPayload(sender="police", result_claim="capture").to_dict())
    a.send_control({"kind": "enable", "sender": "police"})
    a.exchange_agreement_push({"terms": {"board_size": 7}})
    assert b.poll_audit_or_none(timeout=0.5)["result_claim"] == "capture"
    assert b.poll_control_or_none(timeout=0.5)["kind"] == "enable"
    assert b.poll_agreement_or_none(timeout=0.5)["terms"]["board_size"] == 7


def test_polls_return_none_when_no_message() -> None:
    a, _ = make_pair()
    assert a.poll_turn_or_none(timeout=0.01) is None


def test_make_pair_gives_independent_inboxes() -> None:
    a, b = make_pair()
    assert isinstance(a.inboxes, Inboxes)
    assert a.inboxes is not b.inboxes
