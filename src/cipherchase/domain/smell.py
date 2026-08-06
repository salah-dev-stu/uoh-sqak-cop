"""Scent / stigmergy field (FR-D1, F7).

The thief deposits a 5×5 gradient (Chebyshev falloff) at its cell; every turn
the whole field decays ``τ ← max(0, (1−ρ)·τ)``. Scent is physical — it cannot
lie — and only the intensity map (``"row,col" -> float``) ever crosses the
wire, never the opponent's coordinates.
"""

from __future__ import annotations

from cipherchase.constants import Cell
from cipherchase.domain.cells import cell_key, parse_cell


class SmellField:
    def __init__(
        self,
        board_size: int,
        grid_size: int = 5,
        center_intensity: float = 0.9,
        decay: float = 0.1,
        falloff: float = 0.7,
        min_center: float = 1e-3,
        absorb_gain: float = 1.0,
        model: str = "multiplicative_cheb",
    ) -> None:
        self.board_size = board_size
        self.radius = grid_size // 2
        self.center_intensity = center_intensity
        self.decay = decay
        self.falloff = falloff
        self.min_center = min_center
        self.absorb_gain = absorb_gain
        # "subtractive_chebyshev_v1" is the league's CORE registration (SPEC §7):
        # linear falloff, subtractive decay, 3-decimal rounding, and only values
        # above zero on the wire. Selectable so a match can agree one and both
        # peers then emit the same physics.
        self.model = model
        self._field: dict[Cell, float] = {}

    @property
    def _subtractive(self) -> bool:
        return self.model == "subtractive_chebyshev_v1"

    def load(self, field: dict[str, float]) -> None:
        """Replace the field wholesale (fixtures and restarts)."""
        self._field = {c: float(v) for k, v in field.items()
                       if (c := parse_cell(k)) is not None}

    def deposit(self, center: Cell, intensity: float | None = None) -> None:
        peak = self.center_intensity if intensity is None else intensity
        step = peak / (self.radius + 1)
        for cell in self._window(center):
            dist = max(abs(cell[0] - center[0]), abs(cell[1] - center[1]))
            if self._subtractive:
                # Combine by MAX: a fresh deposit REFRESHES a cell rather than
                # stacking on it. The registration pins neither the combine rule
                # nor an upper clamp, so adding lets old trail climb past
                # emit_intensity — two peers declaring one hash, running
                # different physics. Agreed with imreeyal pending a kit fix.
                self._field[cell] = max(self._field.get(cell, 0.0),
                                        round(max(0.0, peak - step * dist), 3))
                continue
            delta = peak * (self.falloff**dist)
            self._field[cell] = min(1.0, self._field.get(cell, 0.0) + delta)

    def decay_all(self) -> None:
        faded: dict[Cell, float] = {}
        for cell, value in self._field.items():
            if self._subtractive:
                new = round(max(0.0, value - self.decay), 3)
                if new > 0.0:
                    faded[cell] = new
                continue
            new = max(0.0, (1.0 - self.decay) * value)
            if new >= self.min_center:
                faded[cell] = new
        self._field = faded

    def absorb(self, smell_map: dict[str, float]) -> None:
        """Merge a foreign field; malformed keys/values are dropped, never crash."""
        for key, value in smell_map.items():
            cell = parse_cell(key)
            if cell is None or not isinstance(value, int | float) or value <= 0.0:
                continue
            if not (0 <= cell[0] < self.board_size and 0 <= cell[1] < self.board_size):
                continue
            gained = self.absorb_gain * float(value)
            self._field[cell] = min(1.0, self._field.get(cell, 0.0) + gained)

    def intensity_at(self, cell: Cell) -> float:
        return self._field.get(cell, 0.0)

    def strongest_cell(self) -> Cell | None:
        if not self._field:
            return None
        return max(sorted(self._field), key=self._field.__getitem__)

    def snapshot(self) -> dict[str, float]:
        return {cell_key(cell): v for cell, v in self._field.items() if v > 0.0}

    def _window(self, center: Cell) -> list[Cell]:
        cells: list[Cell] = []
        for row in range(center[0] - self.radius, center[0] + self.radius + 1):
            for col in range(center[1] - self.radius, center[1] + self.radius + 1):
                if 0 <= row < self.board_size and 0 <= col < self.board_size:
                    cells.append((row, col))
        return cells
