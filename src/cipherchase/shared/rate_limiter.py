"""Token-bucket rate limiter (NFR-4). Limits live in config, never code.

``tokens ← min(capacity, tokens + Δt·rate)``; a call is allowed iff a whole
token is available. The clock is injected so tests stay deterministic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class TokenBucket:
    def __init__(self, capacity: int, refill_per_minute: float, now: Callable[[], float]) -> None:
        self.capacity = float(capacity)
        self.rate = refill_per_minute / 60.0
        self.now = now
        self.tokens = float(capacity)
        self._last = now()

    def allow(self) -> bool:
        moment = self.now()
        self.tokens = min(self.capacity, self.tokens + (moment - self._last) * self.rate)
        self._last = moment
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    def __init__(self, limits: dict[str, dict[str, Any]], now: Callable[[], float]) -> None:
        self._buckets = {
            service: TokenBucket(cfg["capacity"], cfg["requests_per_minute"], now)
            for service, cfg in limits.items()
        }

    def allow(self, service: str) -> bool:
        return self._buckets[service].allow()
