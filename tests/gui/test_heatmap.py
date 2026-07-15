"""Belief-heatmap render data (FR-G4, F12) — local truth only."""

from __future__ import annotations

from cipherchase.gui.heatmap import heatmap_cells


def test_cells_cover_the_grid_with_normalized_shade() -> None:
    matrix = [[0.0, 0.5], [1.0, 0.0]]
    cells = heatmap_cells(matrix)
    assert len(cells) == 4
    peak = next(c for c in cells if c["intensity"] == 1.0)
    assert peak["shade"] == 1.0
    assert peak["row"] == 1 and peak["col"] == 0


def test_all_zero_matrix_does_not_divide_by_zero() -> None:
    cells = heatmap_cells([[0.0, 0.0]])
    assert all(c["shade"] == 0.0 for c in cells)
