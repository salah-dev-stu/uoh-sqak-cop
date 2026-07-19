"""Thread-safe inbound message queues (FR-B3).

Four channels: turns, controls, audits, agreements. Bounded — overflow raises
``QueueFullError`` (backpressure, never drop, NFR-5). The runtime hot loop uses
the non-raising ``try_get_*`` variants; ``drain_all`` clears stale messages
between sub-games/restarts so an aborted turn can never be consumed as live.
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
            raise QueueFullError(f"{name} inbox at capacity") from None

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
            while True:
                try:
                    box.get_nowait()
                except queue.Empty:
                    break

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
