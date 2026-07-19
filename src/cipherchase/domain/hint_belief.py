"""Bluff-aware fusion of the opponent's WORDS into belief (F6/F7). Pure Python.

The board never lies, but the free-text hint may (F6). So the cop treats a hint
as *soft evidence*: extract any cardinal claim, then nudge the belief cone toward
(or, for a proven liar, away from) it — scaled by a Beta honesty posterior.
``bluff_weight`` bounds the pull to ±weight; 0 disables the channel entirely, so
the mechanism is opt-in and can never override the hard scent/crypto evidence.
"""

from __future__ import annotations

from cipherchase.constants import DELTAS, Cell, Direction

_DIR_WORDS = {
    "north": Direction.N,
    "south": Direction.S,
    "east": Direction.E,
    "west": Direction.W,
}


class HonestyTracker:
    """Beta(alpha, beta) posterior over P(opponent hint is honest)."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0) -> None:
        self.alpha = alpha
        self.beta = beta

    def p_honest(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def record(self, honest: bool) -> None:
        if honest:
            self.alpha += 1.0
        else:
            self.beta += 1.0


def extract_claim(text: str) -> Direction | None:
    """First cardinal word in the hint → its direction, else None (no claim)."""
    lowered = text.lower()
    for word, direction in _DIR_WORDS.items():
        if word in lowered:
            return direction
    return None


def in_cone(source: Cell, cell: Cell, direction: Direction) -> bool:
    """True when ``cell`` lies in the ``direction`` half-plane from ``source``."""
    d_row, d_col = DELTAS[direction]
    return (cell[0] - source[0]) * d_row + (cell[1] - source[1]) * d_col > 0


def apply_hint(
    belief,
    source: Cell,
    claim: Direction | None,
    p_honest: float,
    *,
    bluff_weight: float,
    board_size: int,
) -> None:
    """Nudge the belief cone in ``claim`` by 1 + bluff_weight·(2·p_honest − 1)."""
    if claim is None or bluff_weight == 0.0:
        return
    factor = 1.0 + bluff_weight * (2.0 * p_honest - 1.0)
    if factor == 1.0:
        return
    cone = [(r, c) for r in range(board_size) for c in range(board_size)
            if in_cone(source, (r, c), claim)]
    belief.reweight(cone, factor)
