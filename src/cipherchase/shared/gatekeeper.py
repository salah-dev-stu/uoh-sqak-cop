"""The single API gatekeeper (NFR-3, F10).

EVERY external call — MCP, LLM, Gmail, subprocess — goes through ``execute()``,
which gates on the token bucket (DOS guard), backs off and retries rather than
dropping (queue-not-drop, NFR-5), retries designated errors (e.g. HTTP 429),
and records every call in a ledger. Wired, not decorative.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from cipherchase.exceptions import GateLimitError
from cipherchase.shared.rate_limiter import RateLimiter


class ApiGatekeeper:
    def __init__(
        self,
        limiter: Any,
        *,
        max_retries: int = 3,
        backoff: float = 5.0,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.limiter = limiter
        self.max_retries = max_retries
        self.backoff = backoff
        self.sleep = sleep or time.sleep
        self.ledger: list[dict[str, str]] = []

    def execute(
        self,
        fn: Callable[[], Any],
        *,
        service: str,
        action: str,
        retryable: tuple[type[BaseException], ...] = (),
    ) -> Any:
        attempts = 0
        while True:
            if not self.limiter.allow(service):
                attempts = self._backoff_or_fail(attempts, service, action, "rate_limited")
                continue
            try:
                result = fn()
            except retryable:
                attempts = self._backoff_or_fail(attempts, service, action, "error")
                continue
            self._record(service, action, "ok")
            return result

    def _backoff_or_fail(self, attempts: int, service: str, action: str, why: str) -> int:
        if attempts >= self.max_retries:
            self._record(service, action, why)
            raise GateLimitError(f"{service}:{action} {why} after {self.max_retries} retries")
        self.sleep(self.backoff)
        return attempts + 1

    def _record(self, service: str, action: str, status: str) -> None:
        self.ledger.append({"service": service, "action": action, "status": status})

    @classmethod
    def from_config(cls, config: Any, *, now: Callable[[], float], sleep: Any = None) -> ApiGatekeeper:
        limiter = RateLimiter(config.rate_limits, now)
        gate_cfg = config.shared["rate_limiter_gatekeeper"]
        return cls(
            limiter,
            max_retries=gate_cfg["max_retries"],
            backoff=gate_cfg["retry_backoff_sec"],
            sleep=sleep,
        )
