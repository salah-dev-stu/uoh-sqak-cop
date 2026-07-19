"""Strategic bluffing rule (F6/F8) — a pure predicate decides WHEN to lie.

The board never lies and the LLM never decides anything: this rule (pure Python)
picks the *intent*, and the trash-talk layer then dresses it in words. A cop
bluffs once it has closed the gap (feign a lost trail to bait a relaxed thief);
a thief bluffs only when cornered (misdirect its last escape). Everywhere else,
telling the truth costs nothing and keeps the honesty ledger clean (F6 audit).
"""

from __future__ import annotations

from cipherchase.constants import Cell
from cipherchase.domain.board import Board


def should_bluff(
    role: str, cop: Cell, thief: Cell, barriers: frozenset[Cell], board: Board,
    *, gap_threshold: int = 3,
) -> bool:
    if role == "police":
        return board.distance(cop, thief) <= gap_threshold
    if role == "thief":
        escapes = [n for n in board.neighbors(thief, barriers) if n != cop]
        return len(escapes) <= 1
    return False
