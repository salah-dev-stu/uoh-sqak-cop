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


def test_the_start_of_series_backlog_drain_spares_a_punctual_peer() -> None:
    # Shipped mid-match against anrbj666 and never gated: the series-start drain
    # cleared EVERY inbox, agreements included. It fixed stale leftovers driving
    # catch-up and broke the opposite case — a peer that binds first and pushes
    # a perfectly good sub-game-1 agreement has it thrown away, so the punctual
    # side is the one that fails the window. drain_stale() already carried this
    # lesson for restarts ("NEVER a queued agreement"); start-of-series had to
    # learn it too.
    #
    # The discriminator is the index, not the clock: a fresh series opens at 1,
    # so an agreement declaring 1 (or declaring nothing) is live, and anything
    # above it is a leftover from a run that already advanced.
    boxes = Inboxes(maxsize=64)
    for n in (1, 3, 4, None):
        boxes.put_agreement({"sub_game_number": n} if n else {"group_id": "them"})
    boxes.put_turn({"step": 9})

    boxes.drain_backlog(opening=1)

    kept = []
    while (msg := boxes.try_get_agreement(timeout=0.01)) is not None:
        kept.append(msg.get("sub_game_number"))
    assert kept == [1, None], f"a live agreement for the opening index must survive: {kept}"
    assert boxes.try_get_turn(timeout=0.01) is None, "stale turns still go"
