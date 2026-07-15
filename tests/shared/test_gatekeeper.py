"""ApiGatekeeper.execute() — the one gate for every external call (NFR-3/5, F10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cipherchase.exceptions import GateLimitError
from cipherchase.shared.config import ConfigManager
from cipherchase.shared.gatekeeper import ApiGatekeeper

CONFIG = Path(__file__).resolve().parents[2] / "config"


class _Limiter:
    def __init__(self, verdicts: list[bool]) -> None:
        self.verdicts = verdicts
        self.calls = 0

    def allow(self, service: str) -> bool:
        verdict = self.verdicts[min(self.calls, len(self.verdicts) - 1)]
        self.calls += 1
        return verdict


def test_execute_runs_and_records_when_allowed() -> None:
    gate = ApiGatekeeper(_Limiter([True]), sleep=lambda _s: None)
    assert gate.execute(lambda: 42, service="mcp", action="send_turn") == 42
    assert gate.ledger[-1] == {"service": "mcp", "action": "send_turn", "status": "ok"}


def test_execute_backs_off_then_raises_when_throttled() -> None:
    slept: list[float] = []
    gate = ApiGatekeeper(_Limiter([False]), max_retries=2, backoff=5.0, sleep=slept.append)
    with pytest.raises(GateLimitError):
        gate.execute(lambda: 1, service="gmail", action="send")
    assert slept == [5.0, 5.0]  # queued/backed-off, never silently dropped


def test_execute_retries_a_retryable_error_then_succeeds() -> None:
    calls = [0]

    def flaky() -> str:
        calls[0] += 1
        if calls[0] < 2:
            raise RuntimeError("HTTP 429")
        return "ok"

    gate = ApiGatekeeper(_Limiter([True]), max_retries=3, sleep=lambda _s: None)
    assert gate.execute(flaky, service="gmail", action="send", retryable=(RuntimeError,)) == "ok"
    assert calls[0] == 2


def test_from_config_builds_a_working_gatekeeper() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    gate = ApiGatekeeper.from_config(cfg, now=lambda: 0.0, sleep=lambda _s: None)
    assert gate.execute(lambda: "ok", service="mcp", action="ping") == "ok"
