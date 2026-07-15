"""Bayesian belief grid over the opponent's cell (FR-C2).

Prior is uniform. ``observe_smell`` multiplies each cell by a likelihood
``1 + smell_trust·τ(c)`` (only the opponent's scent-intensity field crosses the
wire — F7); ``exclude`` zeroes an impossible cell; ``diffuse`` leaks mass to
orthogonal neighbours to model the opponent moving. All ops renormalise.
"""

from __future__ import annotations

from cipherchase.constants import DELTAS, Cell, Direction


class BeliefGrid:
    def __init__(self, size: int, smell_trust: float = 4.0, alpha: float = 0.85) -> None:
        self.size = size
        self.smell_trust = smell_trust
        self.alpha = alpha
        cells = [(r, c) for r in range(size) for c in range(size)]
        self._p: dict[Cell, float] = {cell: 1.0 / len(cells) for cell in cells}

    def mass_at(self, cell: Cell) -> float:
        return self._p[cell]

    def observe_smell(self, smell_grid: dict[str, float]) -> None:
        for cell in self._p:
            tau = smell_grid.get(f"{cell[0]},{cell[1]}", 0.0)
            self._p[cell] *= 1.0 + self.smell_trust * tau
        self._normalize()

    def exclude(self, cell: Cell) -> None:
        self._p[cell] = 0.0
        self._normalize()

    def diffuse(self) -> None:
        updated: dict[Cell, float] = {}
        for cell in self._p:
            neighbours = self._neighbours(cell)
            leak = sum(self._p[n] for n in neighbours) / len(neighbours) if neighbours else 0.0
            updated[cell] = self.alpha * self._p[cell] + (1.0 - self.alpha) * leak
        self._p = updated
        self._normalize()

    def most_likely(self) -> Cell:
        best: Cell = (0, 0)
        best_mass = -1.0
        for cell in sorted(self._p):
            if self._p[cell] > best_mass:
                best, best_mass = cell, self._p[cell]
        return best

    def as_matrix(self) -> list[list[float]]:
        return [[self._p[(r, c)] for c in range(self.size)] for r in range(self.size)]

    def _neighbours(self, cell: Cell) -> list[Cell]:
        out: list[Cell] = []
        for direction in (Direction.N, Direction.S, Direction.E, Direction.W):
            d_row, d_col = DELTAS[direction]
            nb = (cell[0] + d_row, cell[1] + d_col)
            if 0 <= nb[0] < self.size and 0 <= nb[1] < self.size:
                out.append(nb)
        return out

    def _normalize(self) -> None:
        total = sum(self._p.values())
        if total <= 0.0:
            uniform = 1.0 / len(self._p)
            self._p = dict.fromkeys(self._p, uniform)
            return
        for cell in self._p:
            self._p[cell] /= total
