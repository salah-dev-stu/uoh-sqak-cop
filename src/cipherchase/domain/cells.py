"""The ONE ``"row,col"`` wire codec (R2). Used by smell, belief, engine, viz data.

Scent crosses the wire as ``{"row,col": intensity}`` (F7); every module that
reads or writes those keys goes through here — no scattered f-strings.
"""

from __future__ import annotations

from cipherchase.constants import Cell


def cell_key(cell: Cell) -> str:
    return f"{cell[0]},{cell[1]}"


def parse_cell(key: str) -> Cell | None:
    """Parse ``"r,c"`` → ``(r, c)``; malformed input returns None (never raises)."""
    parts = key.split(",")
    if len(parts) != 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None
