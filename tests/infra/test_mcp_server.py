"""Own FastMCP server: 4 tools enqueue to inboxes (FR-B1/B2/B3, F1)."""

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
    assert box.get_turn(0.1)["step"] == 1
    assert box.get_control(0.1)["kind"] == "enable"
    assert box.get_audit(0.1)["sender"] == "t"


def test_dispatch_unknown_channel_raises() -> None:
    with pytest.raises(ProtocolError):
        dispatch(Inboxes(maxsize=1), "bogus", {})


def test_server_registers_the_four_interop_tools_that_enqueue() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("police", box)
    assert mcp.name == "cipherchase-police"
    for name in TOOLS:
        tool = asyncio.run(mcp.get_tool(name))
        assert tool.name == name
        ack = tool.fn({"sender": "x", "kind_probe": name})
        assert ack["ack"] is True


def test_receive_turn_tool_enqueues_for_the_turn_loop() -> None:
    box = Inboxes(maxsize=10)
    mcp = build_peer_server("thief", box)
    tool = asyncio.run(mcp.get_tool("receive_turn"))
    ack = tool.fn({"step": 7, "sender": "police"})
    assert ack == {"ack": True, "kind": "turn"}
    assert box.get_turn(0.1)["step"] == 7
