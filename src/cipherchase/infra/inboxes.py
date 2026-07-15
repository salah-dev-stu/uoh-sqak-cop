"""Thread-safe inbound message queues (FR-B3).

Inbound MCP messages are enqueued here by the server tools and consumed by the
turn loop — never processed inline. Queues are bounded: overflow raises
``QueueFullError`` (backpressure) rather than silently dropping (NFR-5).
"""

from __future__ import annotations

import queue
from typing import Any

from cipherchase.exceptions import QueueFullError, TransportTimeoutError

Message = dict[str, Any]


class Inboxes:
    """Separate FIFO queues for turn, control, and audit messages."""

    def __init__(self, maxsize: int) -> None:
        self._turns: queue.Queue[Message] = queue.Queue(maxsize)
        self._controls: queue.Queue[Message] = queue.Queue(maxsize)
        self._audits: queue.Queue[Message] = queue.Queue(maxsize)

    @staticmethod
    def _put(q: queue.Queue[Message], item: Message) -> None:
        try:
            q.put_nowait(item)
        except queue.Full:
            raise QueueFullError("inbox at capacity") from None

    @staticmethod
    def _get(q: queue.Queue[Message], timeout: float) -> Message:
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            raise TransportTimeoutError("no message before deadline") from None

    def put_turn(self, msg: Message) -> None:
        self._put(self._turns, msg)

    def get_turn(self, timeout: float) -> Message:
        return self._get(self._turns, timeout)

    def put_control(self, msg: Message) -> None:
        self._put(self._controls, msg)

    def get_control(self, timeout: float) -> Message:
        return self._get(self._controls, timeout)

    def put_audit(self, msg: Message) -> None:
        self._put(self._audits, msg)

    def get_audit(self, timeout: float) -> Message:
        return self._get(self._audits, timeout)
