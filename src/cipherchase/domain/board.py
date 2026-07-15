"""Pure 7×7 grid geometry (FR-A1/A2). No I/O; size is injected from config."""

from __future__ import annotations

from cipherchase.constants import DELTAS, MOVE_ORDER, Cell, Direction
from cipherchase.exceptions import IllegalMoveError


class Board:
    """Orthogonal grid of ``size × size`` cells, origin top-left (row, col)."""

    def __init__(self, size: int, moves: list[Direction] | None = None) -> None:
        self.size = size
        self.moves = list(moves) if moves is not None else list(MOVE_ORDER)

    def in_bounds(self, cell: Cell) -> bool:
        row, col = cell
        return 0 <= row < self.size and 0 <= col < self.size

    def distance(self, a: Cell, b: Cell) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def target_of(self, cell: Cell, direction: Direction) -> Cell:
        d_row, d_col = DELTAS[direction]
        return (cell[0] + d_row, cell[1] + d_col)

    def step(self, cell: Cell, direction: Direction, barriers: frozenset[Cell]) -> Cell:
        """Return the destination of a legal move, else raise ``IllegalMoveError``."""
        target = self.target_of(cell, direction)
        if not self.in_bounds(target):
            raise IllegalMoveError(f"{direction.value} from {cell} leaves the board")
        if target in barriers and target != cell:
            raise IllegalMoveError(f"{direction.value} from {cell} hits a barrier")
        return target

    def neighbors(self, cell: Cell, barriers: frozenset[Cell]) -> list[Cell]:
        """Adjacent, in-bounds, unblocked cells (excludes STAY)."""
        result: list[Cell] = []
        for direction in self.moves:
            if direction is Direction.STAY:
                continue
            target = self.target_of(cell, direction)
            if self.in_bounds(target) and target not in barriers:
                result.append(target)
        return result

    def legal_moves(self, cell: Cell, barriers: frozenset[Cell]) -> list[Direction]:
        """Directions (deterministic order, STAY always legal) that are playable."""
        legal: list[Direction] = []
        for direction in self.moves:
            if direction is Direction.STAY:
                legal.append(direction)
                continue
            target = self.target_of(cell, direction)
            if self.in_bounds(target) and target not in barriers:
                legal.append(direction)
        return legal
