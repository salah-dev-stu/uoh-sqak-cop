"""This peer's own FastMCP server (FR-B1, F1) — reference-compatible tools.

Four enqueue-only tools. Interop criticals (PRD_league_runtime §2.0):
``negotiate`` feeds the AGREEMENTS inbox and ``submit_audit``'s parameter is
named ``payload`` — the reference client calls it that way. The server runs in
a daemon thread for the whole series; the opponent URL carries ``/mcp``.
"""

from __future__ import annotations

import threading
from typing import Any

from fastmcp import FastMCP

from cipherchase.exceptions import ProtocolError
from cipherchase.infra.inboxes import Inboxes

Message = dict[str, Any]
_CHANNELS = {"turn": "put_turn", "control": "put_control", "audit": "put_audit",
             "agreement": "put_agreement"}


def dispatch(inboxes: Inboxes, kind: str, message: Message) -> Message:
    """Route ``message`` to the ``kind`` inbox; return the reference-style ack."""
    method = _CHANNELS.get(kind)
    if method is None:
        raise ProtocolError(f"unknown channel {kind!r}")
    if not isinstance(message, dict):
        return {"ok": False, "error": "malformed"}
    getattr(inboxes, method)(message)
    return {"ok": True}


def build_peer_server(role: str, inboxes: Inboxes) -> FastMCP:
    """The 4 interop tools for ``role`` — enqueue, ack, never process inline."""
    mcp: FastMCP = FastMCP(name=f"cipherchase-{role}")

    @mcp.tool
    def negotiate(message: Message) -> Message:
        return dispatch(inboxes, "agreement", message)

    @mcp.tool
    def receive_turn(message: Message) -> Message:
        return dispatch(inboxes, "turn", message)

    @mcp.tool
    def submit_audit(payload: Message) -> Message:  # param name is the contract
        return dispatch(inboxes, "audit", payload)

    @mcp.tool
    def receive_control(message: Message) -> Message:
        return dispatch(inboxes, "control", message)

    return mcp


def serve_params(config: Any) -> dict[str, Any]:
    """HTTP serving params from config (host/port never hardcoded, FR-E1).

    ``stateless_http`` — liberal-in-what-we-accept (league interop, warm-up
    finding vs najamjad): some peers POST raw JSON-RPC without the MCP
    initialize/session handshake; stateless mode serves them AND spec-full
    clients alike. Our own client stays fully session-negotiated either way.
    """
    return {"transport": "http", "host": config.network["host"], "port": config.my_port,
            "show_banner": False, "stateless_http": True}


def start_peer_server(role: str, config: Any) -> Inboxes:  # pragma: no cover (real socket)
    """Bind + serve in a daemon thread for the whole series; return the inboxes."""
    inboxes = Inboxes(config.queue_maxsize)
    mcp = build_peer_server(role, inboxes)
    thread = threading.Thread(
        target=lambda: mcp.run(**serve_params(config)), daemon=True, name=f"mcp-{role}"
    )
    thread.start()
    return inboxes
