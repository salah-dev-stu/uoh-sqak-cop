"""Signed control channel — the reference contract, plus an audit trail it lacks.

Wire-compatible with the reference peer's opt-in bidirectional channel
(``ControlMessage{kind, sender, sub_game_number, status, step_budget}``; kinds
``enable``/``status``/``restart``/``quit``; active only once BOTH sides enabled;
status broadcast on change only; restart auto-approved when active). Our upgrade:
every control message — sent AND received — is commit-SEALED into the audit
book, so nobody can later lie about who paused, who quit, or when ("you stalled"
becomes a checkable claim, not an argument). The wire bytes stay reference-plain;
only OUR book gains the sealed history.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.protocol import ControlMessage
from cipherchase.peer.sealing import SealBook

QUIT = "QUIT"


class ControlLink:
    def __init__(self, role: str, transport: Any, book: SealBook) -> None:
        self.role, self.transport, self.book = role, transport, book
        self.i_enabled = False
        self.peer_enabled = False
        self.opponent: dict[str, Any] = {"status": "-", "sub_game_number": None,
                                         "step_budget": None}
        self.opponent_quit = False
        self._pending_restart = False
        self._last_status_key: tuple | None = None
        self._step = 0

    @property
    def active(self) -> bool:
        return self.i_enabled and self.peer_enabled

    def _seal(self, direction: str, msg: ControlMessage) -> None:
        self._step += 1
        self.book.seal({"step": self._step, "type": "control", "direction": direction,
                        "kind": msg.kind, "sender": msg.sender, "status": msg.status,
                        "sub_game_number": msg.sub_game_number})

    def _send(self, kind: str, **fields: Any) -> None:
        msg = ControlMessage(kind=kind, sender=self.role, **fields)
        self._seal("sent", msg)
        self.transport.send_control(msg.to_dict())

    def enable(self) -> None:
        self.i_enabled = True
        self._send("enable")

    def broadcast_status(self, status: str, *, sub_game_number: int, step_budget: float) -> None:
        key = (status, round(step_budget or 0.0, 2))
        if not self.i_enabled or key == self._last_status_key:
            return  # opt-in only, and never spam the wire with unchanged status
        self._last_status_key = key
        self._send("status", status=status, sub_game_number=sub_game_number,
                   step_budget=step_budget)

    def send_restart(self) -> None:
        self._send("restart")
        if self.active:  # the requester restarts too (whole-series semantics)
            self._pending_restart = True

    def send_quit(self) -> None:
        self._send("quit", status=QUIT)

    def take_pending_restart(self) -> bool:
        pending, self._pending_restart = self._pending_restart, False
        return pending

    def drain(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while (raw := self.transport.poll_control_or_none(0.0)) is not None:
            msg = ControlMessage.from_dict(raw)
            self._seal("received", msg)
            events.append(self._handle(msg))
        return events

    def _handle(self, msg: ControlMessage) -> dict[str, Any]:
        if msg.kind == "enable":
            self.peer_enabled = True
            return {"type": "control_enable", "sender": msg.sender}
        if msg.kind == "status":
            self.opponent = {"status": msg.status, "sub_game_number": msg.sub_game_number,
                             "step_budget": msg.step_budget}
            return {"type": "control_status", **self.opponent}
        if msg.kind == "restart":
            if self.active:  # auto-approve only once both sides opted in
                self._pending_restart = True
            return {"type": "control_restart", "granted": self.active}
        if msg.kind == "quit":
            self.opponent["status"] = QUIT
            self.opponent_quit = True
            return {"type": "control_quit", "sender": msg.sender}
        return {"type": "control_unknown", "kind": msg.kind}
