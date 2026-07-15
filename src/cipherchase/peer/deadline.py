"""Per-message deadline tracker (FR-H3). Clock injected for determinism."""

from __future__ import annotations

from collections.abc import Callable


class Deadline:
    def __init__(self, timeout: float, now: Callable[[], float]) -> None:
        self.timeout = timeout
        self.now = now
        self._deadline = now() + timeout

    def reset(self) -> None:
        self._deadline = self.now() + self.timeout

    def expired(self) -> bool:
        return self.now() >= self._deadline

    def remaining(self) -> float:
        return max(0.0, self._deadline - self.now())
