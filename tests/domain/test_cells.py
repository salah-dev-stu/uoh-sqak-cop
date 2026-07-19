"""One "r,c" codec for the whole codebase (IH-20, R2)."""

from __future__ import annotations

from cipherchase.domain.cells import cell_key, parse_cell


def test_round_trip() -> None:
    assert cell_key((2, 3)) == "2,3"
    assert parse_cell("2,3") == (2, 3)


def test_malformed_returns_none() -> None:
    assert parse_cell("x,y") is None
    assert parse_cell("7") is None
    assert parse_cell("") is None
