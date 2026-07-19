"""Own FastMCP server: 4 reference tools enqueue to inboxes (FR-B1/B2/B3, F1)."""

from __future__ import annotations

import asyncio

import pytest

from cipherchase.exceptions import ProtocolError
from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_server import build_peer_server, dispatch

TOOLS = {"negotiate", "receive_turn", "submit_audit", "receive_control"}


def test_dispatch_routes_each_channel() -> None:
    box = Inboxes(maxsize=10)
    dispatch(box, "turn", {"step": 1})
    dispatch(box, "control", {"kind": "enable"})
    dispatch(box, "audit", {"sender": "t"})
    dispatch(box, "agreement", {"terms": {}})
    assert box.get_turn(0.1)["step"] == 1
    assert box.get_control(0.1)["kind"] == "enable"
    assert box.get_audit(0.1)["sender"] == "t"
    assert box.try_get_agreement(0.1) == {"terms": {}}


def test_dispatch_unknown_channel_raises_and_malformed_is_refused() -> None:
    with pytest.raises(ProtocolError):
        dispatch(Inboxes(maxsize=1), "bogus", {})
    assert dispatch(Inboxes(maxsize=1), "turn", "not-a-dict")["ok"] is False  # type: ignore[arg-type]


def test_server_registers_the_four_interop_tools_that_enqueue() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("police", box)
    assert mcp.name == "cipherchase-police"
    for name in TOOLS:
        tool = asyncio.run(mcp.get_tool(name))
        assert tool.name == name
        arg = "payload" if name == "submit_audit" else "message"
        ack = tool.fn(**{arg: {"sender": "x", "probe": name}})
        assert ack == {"ok": True}  # reference-style ack


def test_receive_turn_tool_enqueues_for_the_turn_loop() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("thief", box)
    tool = asyncio.run(mcp.get_tool("receive_turn"))
    assert tool.fn({"step": 7, "sender": "police"}) == {"ok": True}
    assert box.get_turn(0.1)["step"] == 7
