"""Deadline tracker + watchdog (FR-H3, F9) — no hang on a silent peer."""

from __future__ import annotations

from cipherchase.peer.deadline import Deadline
from cipherchase.peer.watchdog import Watchdog


def test_deadline_expires_after_timeout() -> None:
    clock = [0.0]
    dl = Deadline(timeout=30.0, now=lambda: clock[0])
    assert not dl.expired()
    assert dl.remaining() == 30.0
    clock[0] = 31.0
    assert dl.expired()
    assert dl.remaining() == 0.0


def test_deadline_reset_extends_the_window() -> None:
    clock = [0.0]
    dl = Deadline(timeout=10.0, now=lambda: clock[0])
    clock[0] = 9.0
    dl.reset()
    clock[0] = 15.0
    assert not dl.expired()  # reset at 9 → new deadline 19


def test_watchdog_expires_without_a_heartbeat() -> None:
    clock = [0.0]
    wd = Watchdog(timeout=60.0, now=lambda: clock[0])
    clock[0] = 30.0
    wd.beat()
    clock[0] = 80.0
    assert not wd.expired()  # 80 - 30 = 50 < 60
    clock[0] = 100.0
    assert wd.expired()  # 100 - 30 = 70 >= 60
