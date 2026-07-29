"""Transport surface shared by the real MCP client and the test fake (R2).

Polling reads THIS peer's own inboxes (non-raising on the hot loop); sending is
delegated to ``_send``. ``submit_audit`` travels with arg key ``payload`` —
the reference contract (PRD_league_runtime §2.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cipherchase.infra.inboxes import Inboxes

Message = dict[str, Any]


class BaseTransport(ABC):
    def __init__(self, inboxes: Inboxes) -> None:
        self.inboxes = inboxes

    @abstractmethod
    def _send(self, tool: str, arg_key: str, message: Message) -> Message:
        """Deliver ``message`` to the opponent's ``tool``; return its ack."""

    # outbound ------------------------------------------------------------------
    def send_turn(self, message: Message) -> Message:
        return self._send("receive_turn", "message", message)

    def send_control(self, message: Message) -> Message | None:
        try:  # advisory channel — best-effort, never blocks the game
            return self._send("receive_control", "message", message)
        except Exception:
            return None

    def send_audit(self, message: Message) -> Message:
        return self._send("submit_audit", "payload", message)

    def exchange_agreement_push(self, signed: Message) -> Message:
        return self._send("negotiate", "message", signed)

    # inbound (non-raising, hot loop) ------------------------------------------
    def poll_turn_or_none(self, timeout: float) -> Message | None:
        return self.inboxes.try_get_turn(timeout)

    def poll_control_or_none(self, timeout: float) -> Message | None:
        return self.inboxes.try_get_control(timeout)

    def poll_audit_or_none(self, timeout: float) -> Message | None:
        return self.inboxes.try_get_audit(timeout)

    def poll_agreement_or_none(self, timeout: float) -> Message | None:
        return self.inboxes.try_get_agreement(timeout)

    def drain_inboxes(self) -> None:
        self.inboxes.drain_all()

    def drain_stale(self) -> None:
        self.inboxes.drain_stale()
