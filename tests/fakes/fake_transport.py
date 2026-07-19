"""In-memory FakeTransport — loopback delivery without any live server/HTTP.

Mirrors the real transport surface (incl. the ``payload`` audit arg key and the
agreements channel) by routing straight into the peer's inboxes (ADR-010).
"""

from __future__ import annotations

from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_server import dispatch
from cipherchase.infra.transport_base import BaseTransport, Message

# opponent tool name -> the inbox channel it feeds (reference-compatible)
_TOOL_CHANNEL = {
    "receive_turn": "turn",
    "receive_control": "control",
    "submit_audit": "audit",
    "negotiate": "agreement",
}


class FakeTransport(BaseTransport):
    def __init__(self, inboxes: Inboxes, peer_inboxes: Inboxes) -> None:
        super().__init__(inboxes)
        self.peer_inboxes = peer_inboxes
        self.sent: list[tuple[str, str, Message]] = []  # (tool, arg_key, message) taps

    def _send(self, tool: str, arg_key: str, message: Message) -> Message:
        self.sent.append((tool, arg_key, message))
        return dispatch(self.peer_inboxes, _TOOL_CHANNEL[tool], message)


def make_pair(maxsize: int = 100) -> tuple[FakeTransport, FakeTransport]:
    """Two transports wired to each other's inboxes (A↔B loopback)."""
    a_box, b_box = Inboxes(maxsize), Inboxes(maxsize)
    return FakeTransport(a_box, b_box), FakeTransport(b_box, a_box)
