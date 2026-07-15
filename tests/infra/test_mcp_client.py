"""Real MCP client transport — logic tested with an injected caller (FR-B3)."""

from __future__ import annotations

from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_client import McpTransport


def _record():
    calls: list[tuple[str, dict]] = []

    def caller(tool: str, message: dict) -> dict:
        calls.append((tool, message))
        return {"ack": True, "kind": "ok"}

    return calls, caller


def test_send_turn_calls_opponent_receive_turn_tool() -> None:
    calls, caller = _record()
    t = McpTransport("http://peer:8002", Inboxes(maxsize=10), caller=caller)
    ack = t.send_turn({"step": 1})
    assert ack["ack"] is True
    assert calls == [("receive_turn", {"step": 1})]


def test_send_maps_each_kind_to_its_tool() -> None:
    calls, caller = _record()
    t = McpTransport("http://peer", Inboxes(maxsize=10), caller=caller)
    t.send_control({"kind": "enable"})
    t.send_audit({"sender": "thief"})
    t.negotiate({"config": {}})
    assert [c[0] for c in calls] == ["receive_control", "submit_audit", "negotiate"]


def test_poll_reads_own_inboxes() -> None:
    _, caller = _record()
    box = Inboxes(maxsize=10)
    t = McpTransport("http://peer", box, caller=caller)
    box.put_turn({"step": 9})
    assert t.poll_turn(timeout=0.1)["step"] == 9
