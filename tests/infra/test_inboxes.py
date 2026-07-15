"""Thread-safe inbound queues (FR-B3, NFR-5 queue-not-drop)."""

from __future__ import annotations

import pytest

from cipherchase.exceptions import QueueFullError, TransportTimeoutError
from cipherchase.infra.inboxes import Inboxes


def test_put_and_get_turn_fifo() -> None:
    box = Inboxes(maxsize=10)
    box.put_turn({"step": 1})
    box.put_turn({"step": 2})
    assert box.get_turn(timeout=0.1) == {"step": 1}
    assert box.get_turn(timeout=0.1) == {"step": 2}


def test_get_turn_times_out_when_empty() -> None:
    box = Inboxes(maxsize=10)
    with pytest.raises(TransportTimeoutError):
        box.get_turn(timeout=0.01)


def test_control_and_audit_channels_are_separate() -> None:
    box = Inboxes(maxsize=10)
    box.put_control({"kind": "enable"})
    box.put_audit({"sender": "thief"})
    assert box.get_control(timeout=0.1) == {"kind": "enable"}
    assert box.get_audit(timeout=0.1) == {"sender": "thief"}


def test_bounded_queue_raises_rather_than_dropping() -> None:
    box = Inboxes(maxsize=1)
    box.put_turn({"step": 1})
    with pytest.raises(QueueFullError):
        box.put_turn({"step": 2})
