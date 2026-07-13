"""Shared coordinate/direction constants (PLAN §8.1 interop freeze)."""

from __future__ import annotations

from cipherchase.constants import DELTAS, MOVE_ORDER, Direction, Outcome


def test_move_order_is_frozen_nsew_stay() -> None:
    # Byte-stable order matters for replay/audit (Interop Freeze).
    assert MOVE_ORDER == [
        Direction.N,
        Direction.S,
        Direction.E,
        Direction.W,
        Direction.STAY,
    ]


def test_direction_wire_values_are_letters() -> None:
    assert Direction.N.value == "N"
    assert Direction.STAY.value == "STAY"


def test_deltas_are_orthogonal_row_col() -> None:
    assert DELTAS[Direction.N] == (-1, 0)
    assert DELTAS[Direction.S] == (1, 0)
    assert DELTAS[Direction.E] == (0, 1)
    assert DELTAS[Direction.W] == (0, -1)
    assert DELTAS[Direction.STAY] == (0, 0)


def test_outcome_members() -> None:
    assert {o.name for o in Outcome} == {"CAPTURE", "SURVIVAL", "TIE", "TECHNICAL_LOSS"}
