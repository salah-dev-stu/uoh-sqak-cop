"""The single API gatekeeper (NFR-3, F10).

EVERY external call — MCP, LLM, Gmail, subprocess — goes through ``execute()``:
token-bucket gate (rate), concurrency semaphore, bounded-backlog DOS guard
(queue-not-drop backpressure, NFR-5), retryable-error backoff (HTTP 429), and a
ledger of every call. Wired, not decorative.
"""

from __future__ import annotations

import threading
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
        concurrent: int | None = None,
        queue_depth: int | None = None,
    ) -> None:
        self.limiter = limiter
        self.max_retries = max_retries
        self.backoff = backoff
        self.sleep = sleep or time.sleep
        self.concurrent = concurrent
        self.queue_depth = queue_depth
        self._sem = threading.BoundedSemaphore(concurrent) if concurrent else None
        self._waiting = 0
        self.ledger: list[dict[str, str]] = []

    def execute(
        self,
        fn: Callable[[], Any],
        *,
        service: str,
        action: str,
        retryable: tuple[type[BaseException], ...] = (),
    ) -> Any:
        if self.queue_depth is not None and self._waiting >= self.queue_depth:
            self._record(service, action, "dos_rejected")
            raise GateLimitError(f"{service}:{action} backlog over queue depth (DOS guard)")
        self._waiting += 1
        try:
            return self._run(fn, service, action, retryable)
        finally:
            self._waiting -= 1

    def _run(
        self,
        fn: Callable[[], Any],
        service: str,
        action: str,
        retryable: tuple[type[BaseException], ...],
    ) -> Any:
        attempts = 0
        while True:
            if not self.limiter.allow(service):
                attempts = self._backoff_or_fail(attempts, service, action, "rate_limited")
                continue
            if self._sem is not None:
                self._sem.acquire()
            try:
                result = fn()
            except retryable:
                attempts = self._backoff_or_fail(attempts, service, action, "error")
                continue
            finally:
                if self._sem is not None:
                    self._sem.release()
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
            concurrent=gate_cfg["concurrent_requests"],
            queue_depth=gate_cfg["queue_depth"],
        )
