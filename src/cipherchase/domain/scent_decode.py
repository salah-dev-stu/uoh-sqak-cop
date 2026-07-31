"""ScentDecoder — near-oracle localisation from LEGAL information (WB §3).

The opponent's field evolves ``τ_t = min(1, (1−ρ)·τ_{t−1} + D_c)`` where
``D_c`` is the known deposit shape centred on their cell. A naive Δ-argmax is
clipped by the saturation cap, so we run a MATCHED FILTER: for every candidate
centre, predict the field and take the best L1 fit — exact even when the trail
saturates. Ambiguity (no centre fits) falls back to a PERSISTENT BeliefGrid,
diffused and observed across turns, never reset (the old phantom-trail bug).
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Cell
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.cells import cell_key, parse_cell

SHARP_TRUST = 1e6  # a decoded cell concentrates the belief onto one cell


class ScentDecoder:
    def __init__(self, size: int, smell_trust: float, alpha: float, pheromones: dict[str, Any],
                 fit_tolerance: float = 0.3) -> None:
        self.size = size
        self.radius = int(pheromones["grid_size"]) // 2
        self.emit = float(pheromones["center_intensity"])
        self.decay = float(pheromones["decay"])
        self.falloff = float(pheromones.get("falloff", 0.7))
        self.min_center = float(pheromones.get("min_center_intensity", 0.0))
        self.fit_tolerance = fit_tolerance
        self.grid = BeliefGrid(size, smell_trust, alpha)
        self._prev: dict[str, float] = {}
        self.last_decoded: Cell | None = None

    def _deposit_at(self, center: Cell, cell: Cell) -> float:
        dist = max(abs(cell[0] - center[0]), abs(cell[1] - center[1]))
        if dist > self.radius:
            return 0.0
        return self.emit * (self.falloff**dist)

    def _fit_error(self, center: Cell, current: dict[str, float], keys: set[str]) -> float:
        error = 0.0
        for key in keys:
            cell = parse_cell(key)
            if cell is None:
                continue
            residue = (1.0 - self.decay) * self._prev.get(key, 0.0)
            if residue < self.min_center:  # fields cull faint cells at decay time
                residue = 0.0
            predicted = min(1.0, residue + self._deposit_at(center, cell))
            error += abs(current.get(key, 0.0) - predicted)
        return error

    def decode(self, current: dict[str, float]) -> Cell | None:
        """Best-fit deposit centre, or None when no centre explains the field."""
        keys = set(current) | set(self._prev)
        if not keys:
            return None
        best_cell, best_err = None, float("inf")
        for row in range(self.size):
            for col in range(self.size):
                center = (row, col)
                window = {cell_key((r, c))
                          for r in range(max(0, row - self.radius),
                                         min(self.size, row + self.radius + 1))
                          for c in range(max(0, col - self.radius),
                                         min(self.size, col + self.radius + 1))}
                err = self._fit_error(center, current, keys | window)
                if err < best_err:
                    best_cell, best_err = center, err
        return best_cell if best_err <= self.fit_tolerance else None

    def fresh_peak(self, snapshot: dict[str, float]) -> Cell | None:
        """League-robust shortcut (najamjad warm-up finding): on fields that never
        saturate, the unique fresh-emit-intensity cell IS the opponent. Our own
        physics saturates old trail to 1.0 > emit, which rejects this path and
        keeps the matched filter in charge exactly where it is needed."""
        if not snapshot:
            return None
        peak = max(snapshot.values())
        if peak >= 1.0 or peak < self.emit - 1e-6:
            return None  # saturated trail or no fresh stamp → not this field style
        tops = [k for k, v in snapshot.items() if v >= peak - 1e-6]
        return parse_cell(tops[0]) if len(tops) == 1 else None

    def update(self, snapshot: dict[str, float]) -> BeliefGrid:
        """Fold one received snapshot into the persistent belief; return it."""
        self.grid.diffuse()
        self.last_decoded = self.fresh_peak(snapshot) or self.decode(snapshot)
        if self.last_decoded is not None:
            self.grid.observe_smell({cell_key(self.last_decoded): SHARP_TRUST})
        elif snapshot:
            self.grid.observe_smell(snapshot)
        self._prev = dict(snapshot)
        return self.grid
