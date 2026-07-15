"""Belief-heatmap render data (FR-G4, F12).

Turns a ``BeliefGrid.as_matrix()`` into per-cell shade in ``[0, 1]`` (peak
normalised) for the Live GUI. This is the peer's LOCAL belief only — never the
objective board.
"""

from __future__ import annotations

from typing import Any


def heatmap_cells(matrix: list[list[float]]) -> list[dict[str, Any]]:
    peak = max((value for row in matrix for value in row), default=0.0) or 1.0
    cells: list[dict[str, Any]] = []
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            cells.append(
                {"row": row_index, "col": col_index, "intensity": value, "shade": value / peak}
            )
    return cells
