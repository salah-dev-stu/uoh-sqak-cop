"""Heartbeat watchdog (FR-H3). A silent peer → expiry → technical loss, no hang."""

from __future__ import annotations

from collections.abc import Callable


class Watchdog:
    def __init__(self, timeout: float, now: Callable[[], float]) -> None:
        self.timeout = timeout
        self.now = now
        self._last = now()

    def beat(self) -> None:
        self._last = self.now()

    def expired(self) -> bool:
        return self.now() - self._last >= self.timeout
