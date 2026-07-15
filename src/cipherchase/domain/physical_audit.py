"""Physical-claim audit (FR-F3, F4/F6).

The bluff *hint* may lie; the physical board may not. Each committed payload
carries the mover's own position, its barrier view, and its move — so we can
re-check that every revealed move was actually LEGAL on that board. Combined
with the hash audit (which forbids changing a committed move), a peer must
commit to a legal move or be caught → tamper_forfeit.
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Cell, Direction
from cipherchase.domain import rules
from cipherchase.domain.board import Board


def move_violations(records: list[dict[str, Any]], board: Board) -> list[int]:
    bad: list[int] = []
    for index, record in enumerate(records):
        payload = record.get("payload", {})
        try:
            pos: Cell = tuple(payload["state"]["pos"])  # type: ignore[assignment]
            barriers = frozenset(tuple(cell) for cell in payload["state"]["barriers"])
            direction = Direction(payload["move"])
        except (KeyError, ValueError, TypeError):
            bad.append(index)
            continue
        if not rules.is_legal_move(board, pos, direction, barriers):
            bad.append(index)
    return bad


def physical_audit(records: list[dict[str, Any]], board: Board) -> dict[str, Any]:
    violations = move_violations(records, board)
    return {"passed": not violations, "violations": violations}
