"""Inbound turn steps: read a message, check the reveal matches the commit."""

from __future__ import annotations

from typing import Any

from cipherchase.domain.protocol import TurnMessage


def receive_turn(transport: Any, timeout: float) -> TurnMessage:
    return TurnMessage.from_dict(transport.poll_turn(timeout))


def reveal_matches_commit(committed: TurnMessage, revealed: TurnMessage) -> bool:
    """The reveal must carry the same commit hash and a concrete move."""
    return committed.commit == revealed.commit and revealed.move is not None
