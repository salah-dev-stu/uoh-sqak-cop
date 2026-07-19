"""P1 wire substrate (PRD_league_runtime §2.0/§2.4): exact tools, exact keys."""

from __future__ import annotations

import asyncio

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import TurnMessage
from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_server import build_peer_server

WIRE_KEYS = {
    "step", "sender", "hint", "smell_grid", "commit", "timestamp",
    "barrier_placed", "capture_claim", "claim_response", "win_claim",
}


def test_turn_message_emits_exactly_the_reference_key_set() -> None:
    wire = TurnMessage(step=1, sender="thief", hint="hi", timestamp="2026-08-01T00:00:00Z").to_dict()
    assert set(wire) == WIRE_KEYS  # no move/intent/nonce — sealed until audit


def test_turn_message_parse_is_lenient_to_foreign_extras() -> None:
    msg = TurnMessage.from_dict(
        {"step": 3, "sender": "police", "alien": 1, "verdict": "x", "tokens_used": 9}
    )
    assert msg.step == 3 and msg.sender == "police"


def test_negotiate_tool_routes_to_the_agreements_inbox() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("police", box)
    tool = asyncio.run(mcp.get_tool("negotiate"))
    assert tool.fn({"terms": {}})["ok"] is True
    assert box.try_get_agreement(0.1) == {"terms": {}}


def test_submit_audit_tool_parameter_is_named_payload() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("thief", box)
    tool = asyncio.run(mcp.get_tool("submit_audit"))
    assert "payload" in tool.parameters["properties"]  # reference client sends {"payload": ...}
    assert tool.fn(payload={"sender": "police"})["ok"] is True
    assert box.try_get_audit(0.1)["sender"] == "police"


def test_try_get_returns_none_on_empty_and_drain_clears_everything() -> None:
    box = Inboxes(maxsize=10)
    assert box.try_get_turn(0.01) is None
    box.put_turn({"step": 1})
    box.put_control({"kind": "enable"})
    box.put_agreement({"terms": {}})
    box.drain_all()
    assert box.try_get_turn(0.01) is None
    assert box.try_get_control(0.01) is None
    assert box.try_get_agreement(0.01) is None


def test_fake_transport_supports_the_new_surface() -> None:
    a, b = make_pair()
    a.exchange_agreement_push({"terms": {"n": 1}})
    assert b.inboxes.try_get_agreement(0.1) == {"terms": {"n": 1}}
    a.send_turn({"step": 1, "sender": "thief"})
    assert b.poll_turn_or_none(0.1)["step"] == 1
    assert b.poll_turn_or_none(0.01) is None
    a.send_audit({"sender": "thief", "records": []})
    assert b.inboxes.try_get_audit(0.1)["sender"] == "thief"
