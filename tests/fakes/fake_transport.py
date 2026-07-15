"""In-memory FakeTransport — loopback delivery without any live server/HTTP.

``_send`` routes into the *peer's* inboxes exactly as the peer's FastMCP tools
would, so peer logic can be tested deterministically (grader path, ADR-010).
"""

from __future__ import annotations

from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_server import dispatch
from cipherchase.infra.transport_base import BaseTransport, Message

# Reverse of SEND_TOOL: opponent tool name -> the inbox channel it feeds.
_TOOL_CHANNEL = {
    "receive_turn": "turn",
    "receive_control": "control",
    "submit_audit": "audit",
    "negotiate": "control",
}


class FakeTransport(BaseTransport):
    def __init__(self, inboxes: Inboxes, peer_inboxes: Inboxes) -> None:
        super().__init__(inboxes)
        self.peer_inboxes = peer_inboxes

    def _send(self, tool: str, message: Message) -> Message:
        return dispatch(self.peer_inboxes, _TOOL_CHANNEL[tool], message)


def make_pair(maxsize: int = 100) -> tuple[FakeTransport, FakeTransport]:
    """Two transports wired to each other's inboxes (A↔B loopback)."""
    a_box, b_box = Inboxes(maxsize), Inboxes(maxsize)
    return FakeTransport(a_box, b_box), FakeTransport(b_box, a_box)
