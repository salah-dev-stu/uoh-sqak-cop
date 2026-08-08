"""Thread-safe inbound message queues (FR-B3).

Four channels: turns, controls, audits, agreements. Bounded — overflow raises
``QueueFullError`` (backpressure, never drop, NFR-5). The runtime hot loop uses
the non-raising ``try_get_*`` variants.

Three drains, differing only in how much they spare, because an aborted turn
must never be consumed as live while a live agreement must never be discarded:
``drain_all`` (everything), ``drain_backlog`` (start of series — keeps an
agreement for the opening index), ``drain_stale`` (restart — keeps any agreement).
"""

from __future__ import annotations

import queue
from typing import Any

from cipherchase.exceptions import QueueFullError, TransportTimeoutError

Message = dict[str, Any]


class Inboxes:
    def __init__(self, maxsize: int) -> None:
        self._boxes: dict[str, queue.Queue[Message]] = {
            name: queue.Queue(maxsize) for name in ("turn", "control", "audit", "agreement")
        }

    def _put(self, name: str, item: Message) -> None:
        try:
            self._boxes[name].put_nowait(item)
        except queue.Full:
            # Name the channel and its depth: a peer whose agreement inbox is
            # full answers every probe while being unable to start any game, so
            # "at capacity" alone sends the operator looking at the network.
            raise QueueFullError(
                f"{name} inbox at capacity ({self._boxes[name].qsize()} queued) — "
                f"the reader is not draining this channel fast enough, or a peer "
                f"is pushing for a window we are not in") from None

    def _get(self, name: str, timeout: float) -> Message:
        try:
            return self._boxes[name].get(timeout=timeout)
        except queue.Empty:
            raise TransportTimeoutError(f"no {name} message before deadline") from None

    def _try_get(self, name: str, timeout: float) -> Message | None:
        try:
            return self._boxes[name].get(timeout=timeout)
        except queue.Empty:
            return None

    def drain_all(self) -> None:
        for box in self._boxes.values():
            self._drain(box)

    def drain_backlog(self, opening: int) -> None:
        """Start-of-series drain: clear stale traffic, KEEP a live agreement.

        A relaunch inherits whatever the peer queued during the run that failed,
        and a leftover declaring a high index will otherwise drive catch-up past
        the game. But draining agreements wholesale punishes the punctual peer:
        one that binds first and pushes a good opening agreement has it thrown
        away. The index is the discriminator — a fresh series opens at `opening`,
        so an agreement declaring that (or declaring nothing) is live.
        """
        for name in ("turn", "control", "audit"):
            self._drain(self._boxes[name])
        box = self._boxes["agreement"]
        live = [m for m in self._drained(box)
                if m.get("sub_game_number") in (None, opening)]
        for message in live:
            box.put(message)

    @staticmethod
    def _drained(box: queue.Queue) -> list[Message]:
        out: list[Message] = []
        while True:
            try:
                out.append(box.get_nowait())
            except queue.Empty:
                return out

    def drain_stale(self) -> None:
        """Restart drain: clear stale turns/controls/audits but NEVER a queued
        agreement — the faster-restarting peer's fresh handshake may already be in."""
        for name in ("turn", "control", "audit"):
            self._drain(self._boxes[name])

    @classmethod
    def _drain(cls, box: queue.Queue) -> None:
        cls._drained(box)

    # raising getters (legacy/tests) -------------------------------------------------
    def put_turn(self, msg: Message) -> None:
        self._put("turn", msg)

    def get_turn(self, timeout: float) -> Message:
        return self._get("turn", timeout)

    def put_control(self, msg: Message) -> None:
        self._put("control", msg)

    def get_control(self, timeout: float) -> Message:
        return self._get("control", timeout)

    def put_audit(self, msg: Message) -> None:
        self._put("audit", msg)

    def get_audit(self, timeout: float) -> Message:
        return self._get("audit", timeout)

    def put_agreement(self, msg: Message) -> None:
        self._put("agreement", msg)

    # non-raising poll variants (runtime hot loop) -----------------------------------
    def try_get_turn(self, timeout: float) -> Message | None:
        return self._try_get("turn", timeout)

    def try_get_control(self, timeout: float) -> Message | None:
        return self._try_get("control", timeout)

    def try_get_audit(self, timeout: float) -> Message | None:
        return self._try_get("audit", timeout)

    def try_get_agreement(self, timeout: float) -> Message | None:
        return self._try_get("agreement", timeout)
