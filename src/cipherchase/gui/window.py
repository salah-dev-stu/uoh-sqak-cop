"""Live GUI (FR-G4, F12) — belief heatmap + turn banner, LOCAL truth only.

The pure ``banner_text`` is unit-tested; ``run_live`` renders with Tkinter and
is excluded from coverage (it needs a display — screenshots are captured by
running it manually, per the README).
"""

from __future__ import annotations

from typing import Any

from cipherchase.gui.heatmap import heatmap_cells


def banner_text(role: str, step: int, believed_cell: tuple[int, int]) -> str:
    return f"{role} · step {step} · belief peak {believed_cell}"


def run_live(role: str, matrix: list[list[float]], step: int, cell_px: int = 64) -> Any:  # pragma: no cover
    import tkinter as tk

    root = tk.Tk()
    root.title(f"CipherChase — {role} (local belief)")
    size = len(matrix)
    canvas = tk.Canvas(root, width=size * cell_px, height=size * cell_px)
    canvas.pack()
    for cell in heatmap_cells(matrix):
        shade = int(255 * (1.0 - cell["shade"]))
        x0, y0 = cell["col"] * cell_px, cell["row"] * cell_px
        canvas.create_rectangle(
            x0, y0, x0 + cell_px, y0 + cell_px, fill=f"#ff{shade:02x}{shade:02x}"
        )
    peak = max(heatmap_cells(matrix), key=lambda c: c["shade"])
    tk.Label(root, text=banner_text(role, step, (peak["row"], peak["col"]))).pack()
    root.mainloop()
    return root
