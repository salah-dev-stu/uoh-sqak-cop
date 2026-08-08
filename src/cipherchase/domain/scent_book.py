"""`multiplicative_book_v1` — the book's figure-4 kernel and its update law.

One file per locked model: the two locks disagree about what a turn IS, and each
physics is easier to check against its registration whole than as branches
inside a shared class.

    tau' = clamp((1 - rho) * tau + kernel_delta, 0, center_intensity)

The evaluation order is pinned rather than incidental — the kit's ordering probe
shows `tau - rho * tau + delta` disagrees with this in floating point on ordinary
values, so the expression is part of the lock and is spelled as registered.

Pinned against the kit's own `scent_book_v3` vectors (MIT,
github.com/Imreec/copthief-league-protocol).
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Cell

# Book v3.0.0 figure 4, printed values, verbatim lookup.
KERNEL = [[0.04, 0.14, 0.2, 0.14, 0.04], [0.14, 0.42, 0.62, 0.42, 0.14], [0.2, 0.62, 0.9, 0.62, 0.2], [0.14, 0.42, 0.62, 0.42, 0.14], [0.04, 0.14, 0.2, 0.14, 0.04]]


def kernel_at(field: Any, center: Cell) -> dict[Cell, float]:
    """The 5x5 kernel laid over the board, clipped at the edges."""
    out: dict[Cell, float] = {}
    for row_offset, row in enumerate(KERNEL):
        for col_offset, delta in enumerate(row):
            cell = (center[0] - field.radius + row_offset,
                    center[1] - field.radius + col_offset)
            if 0 <= cell[0] < field.board_size and 0 <= cell[1] < field.board_size:
                out[cell] = delta
    return out


def book_turn(field: Any, center: Cell | None) -> None:
    """One FULL turn: decay every cell and add the kernel, in one expression."""
    rho, cap = field.decay, field.center_intensity
    deltas = {} if center is None else kernel_at(field, center)
    faded: dict[Cell, float] = {}
    for cell in set(field.cells()) | set(deltas):
        tau = (1 - rho) * field.intensity_at(cell) + deltas.get(cell, 0.0)
        value = min(max(tau, 0.0), cap)
        if value > 0.0:
            faded[cell] = value
    field.replace(faded)
