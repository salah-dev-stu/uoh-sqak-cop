"""Transport interface shared by the real MCP client and the test fake (R2).

Polling always reads THIS peer's own inboxes; sending is delegated to the
concrete ``_send`` (real HTTP tool call, or in-memory routing in tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cipherchase.infra.inboxes import Inboxes

Message = dict[str, Any]

# Interop tool names for each outbound message kind.
SEND_TOOL = {"turn": "receive_turn", "control": "receive_control", "audit": "submit_audit"}


class BaseTransport(ABC):
    def __init__(self, inboxes: Inboxes) -> None:
        self.inboxes = inboxes

    @abstractmethod
    def _send(self, tool: str, message: Message) -> Message:
        """Deliver ``message`` to the opponent's ``tool``; return its ack."""

    def send_turn(self, message: Message) -> Message:
        return self._send(SEND_TOOL["turn"], message)

    def send_control(self, message: Message) -> Message:
        return self._send(SEND_TOOL["control"], message)

    def send_audit(self, message: Message) -> Message:
        return self._send(SEND_TOOL["audit"], message)

    def negotiate(self, message: Message) -> Message:
        return self._send("negotiate", message)

    def poll_turn(self, timeout: float) -> Message:
        return self.inboxes.get_turn(timeout)

    def poll_control(self, timeout: float) -> Message:
        return self.inboxes.get_control(timeout)

    def poll_audit(self, timeout: float) -> Message:
        return self.inboxes.get_audit(timeout)
