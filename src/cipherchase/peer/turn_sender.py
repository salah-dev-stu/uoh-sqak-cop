"""Outbound turn steps: commit first (nonce hidden), reveal after ack (FR-F2)."""

from __future__ import annotations

from typing import Any

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.sealing import SealBook


def send_commit(
    transport: Any,
    book: SealBook,
    *,
    step: int,
    sender: str,
    payload: dict[str, Any],
    hint: str = "",
    smell_grid: dict[str, float] | None = None,
) -> str:
    """Seal ``payload``, send only the commit hash; return the hidden nonce."""
    commit, nonce = book.seal(payload)
    message = TurnMessage(
        step=step, sender=sender, commit=commit, hint=hint, smell_grid=smell_grid or {}
    )
    transport.send_turn(message.to_dict())
    return nonce


def send_reveal(
    transport: Any,
    *,
    step: int,
    sender: str,
    commit: str,
    move: str,
    intent: str,
    hint: str = "",
) -> None:
    """Reveal the move + intent for a locked commit — the nonce stays hidden."""
    message = TurnMessage(
        step=step, sender=sender, commit=commit, move=move, intent=intent, hint=hint
    )
    transport.send_turn(message.to_dict())
