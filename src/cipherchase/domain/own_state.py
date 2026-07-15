"""A peer's own observable state (FR-A1) — immutable, opponent-free.

Only the mover's own position/barriers/history live here; the opponent is
never stored as truth (that would break the zero-trust model). Every
transition returns a fresh instance.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from cipherchase.constants import Cell


@dataclass(frozen=True)
class OwnState:
    role: str
    position: Cell
    barriers: frozenset[Cell] = frozenset()
    turn: int = 0
    history: tuple[Cell, ...] = field(default_factory=tuple)

    def moved_to(self, cell: Cell) -> OwnState:
        return dataclasses.replace(self, position=cell, history=(*self.history, self.position))

    def with_barrier(self, cell: Cell) -> OwnState:
        return dataclasses.replace(self, barriers=self.barriers | {cell})

    def advanced(self) -> OwnState:
        return dataclasses.replace(self, turn=self.turn + 1)
