"""Scent / stigmergy field (FR-D1, F7). 5×5, center 0.9, decay 0.10."""

from __future__ import annotations

import pytest

from cipherchase.domain.smell import SmellField


def _field() -> SmellField:
    return SmellField(board_size=7, grid_size=5, center_intensity=0.9, decay=0.1, falloff=0.7)


def test_deposit_center_and_falloff_ring() -> None:
    f = _field()
    f.deposit((3, 3))
    assert f.intensity_at((3, 3)) == pytest.approx(0.9)
    assert f.intensity_at((3, 4)) == pytest.approx(0.9 * 0.7)  # d=1
    assert f.intensity_at((1, 3)) == pytest.approx(0.9 * 0.7**2)  # d=2


def test_outside_5x5_window_is_zero() -> None:
    f = _field()
    f.deposit((3, 3))
    assert f.intensity_at((3, 0)) == 0.0  # Chebyshev d=3 > radius 2


def test_decay_shrinks_intensity() -> None:
    f = _field()
    f.deposit((3, 3))
    f.decay_all()
    assert f.intensity_at((3, 3)) == pytest.approx(0.9 * 0.9)  # (1-0.10)


def test_strongest_cell_and_empty_is_none() -> None:
    f = _field()
    assert f.strongest_cell() is None
    f.deposit((5, 5))
    assert f.strongest_cell() == (5, 5)


def test_snapshot_is_intensity_only_string_keys() -> None:
    f = _field()
    f.deposit((3, 3))
    snap = f.snapshot()
    assert "3,3" in snap
    assert isinstance(snap["3,3"], float)
    assert all("," in k for k in snap)  # no opponent coords, just "r,c" intensities


def test_absorb_merges_an_external_field() -> None:
    f = _field()
    f.absorb({"2,2": 0.5})
    assert f.intensity_at((2, 2)) == pytest.approx(0.5)


def test_absorb_drops_malformed_and_out_of_bounds_never_crashes() -> None:
    f = _field()
    f.absorb({"x,y": 0.5, "1,1": "bad", "9,9": 0.5, "-1,0": 0.5, "2,2": 0.4})  # type: ignore[dict-item]
    assert f.intensity_at((2, 2)) == pytest.approx(0.4)
    assert f.intensity_at((9, 9)) == 0.0


def test_absorb_gain_scales_incoming_intensity() -> None:
    f = SmellField(7, 5, 0.9, 0.1, 0.7, absorb_gain=0.5)
    f.absorb({"1,1": 0.8})
    assert f.intensity_at((1, 1)) == pytest.approx(0.4)


def test_intensity_never_negative_and_decays_to_zero() -> None:
    f = _field()
    f.deposit((3, 3))
    for _ in range(200):
        f.decay_all()
    assert f.intensity_at((3, 3)) == 0.0
