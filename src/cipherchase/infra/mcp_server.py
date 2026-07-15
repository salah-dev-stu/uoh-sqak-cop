"""This peer's own FastMCP server (FR-B1). Each tool enqueues to inboxes.

There is NO central server (F1): every peer runs its own. The 4 interop-named
tools drop inbound messages into thread-safe queues (FR-B3) — never processed
inline — for the turn loop to consume.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from cipherchase.exceptions import ProtocolError
from cipherchase.infra.inboxes import Inboxes

Message = dict[str, Any]
_CHANNELS = {"turn": "put_turn", "control": "put_control", "audit": "put_audit"}


def dispatch(inboxes: Inboxes, kind: str, message: Message) -> Message:
    """Route ``message`` to the ``kind`` inbox; return a uniform ack."""
    method = _CHANNELS.get(kind)
    if method is None:
        raise ProtocolError(f"unknown channel {kind!r}")
    getattr(inboxes, method)(message)
    return {"ack": True, "kind": kind}


def build_peer_server(role: str, inboxes: Inboxes) -> FastMCP:
    """Build the FastMCP server exposing the 4 interop tools for ``role``."""
    mcp: FastMCP = FastMCP(name=f"cipherchase-{role}")

    @mcp.tool
    def negotiate(message: Message) -> Message:
        return dispatch(inboxes, "control", message)

    @mcp.tool
    def receive_turn(message: Message) -> Message:
        return dispatch(inboxes, "turn", message)

    @mcp.tool
    def submit_audit(message: Message) -> Message:
        return dispatch(inboxes, "audit", message)

    @mcp.tool
    def receive_control(message: Message) -> Message:
        return dispatch(inboxes, "control", message)

    return mcp
