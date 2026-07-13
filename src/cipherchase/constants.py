"""Shared enums and coordinate constants (no duplication — R2).

``Cell`` is ``(row, col)`` with origin top-left (PLAN §8.1). ``MOVE_ORDER`` is
frozen ``[N, S, E, W, STAY]`` so replay/audit byte-order is deterministic.
Direction values are the single-letter wire tokens.
"""

from __future__ import annotations

from enum import Enum

Cell = tuple[int, int]


class Direction(Enum):
    N = "N"
    S = "S"
    E = "E"
    W = "W"
    STAY = "STAY"


class Outcome(Enum):
    CAPTURE = "capture"
    SURVIVAL = "survival"
    TIE = "tie"
    TECHNICAL_LOSS = "technical_loss"


# Deterministic move order (interop-critical) and (row, col) deltas.
MOVE_ORDER: list[Direction] = [
    Direction.N,
    Direction.S,
    Direction.E,
    Direction.W,
    Direction.STAY,
]

DELTAS: dict[Direction, Cell] = {
    Direction.N: (-1, 0),
    Direction.S: (1, 0),
    Direction.E: (0, 1),
    Direction.W: (0, -1),
    Direction.STAY: (0, 0),
}
