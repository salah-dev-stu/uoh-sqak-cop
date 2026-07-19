"""Bayesian belief grid over the opponent's location (FR-C2, F7)."""

from __future__ import annotations

import pytest

from cipherchase.domain.belief import BeliefGrid


def _total(grid: BeliefGrid) -> float:
    return sum(sum(row) for row in grid.as_matrix())


def test_uniform_prior_sums_to_one() -> None:
    grid = BeliefGrid(7)
    assert grid.mass_at((0, 0)) == pytest.approx(1 / 49)
    assert _total(grid) == pytest.approx(1.0)


def test_observe_smell_boosts_scented_cells() -> None:
    grid = BeliefGrid(7, smell_trust=4.0)
    grid.observe_smell({"5,5": 0.9})
    assert grid.mass_at((5, 5)) > grid.mass_at((0, 0))
    assert _total(grid) == pytest.approx(1.0)


def test_most_likely_follows_the_scent() -> None:
    grid = BeliefGrid(7, smell_trust=4.0)
    grid.observe_smell({"5,5": 0.9, "5,4": 0.3})
    assert grid.most_likely() == (5, 5)


def test_exclude_zeroes_a_cell_and_renormalizes() -> None:
    grid = BeliefGrid(7)
    grid.exclude((0, 0))
    assert grid.mass_at((0, 0)) == 0.0
    assert _total(grid) == pytest.approx(1.0)


def test_diffuse_spreads_mass_to_neighbours() -> None:
    grid = BeliefGrid(7, alpha=0.5)
    for cell in [(r, c) for r in range(7) for c in range(7)]:
        grid.exclude(cell) if cell != (3, 3) else None
    # Now all mass at (3,3); diffusing must leak some to (2,3).
    before = grid.mass_at((2, 3))
    grid.diffuse()
    assert grid.mass_at((2, 3)) > before
    assert _total(grid) == pytest.approx(1.0)


def test_most_likely_deterministic_tie_break() -> None:
    grid = BeliefGrid(7)  # uniform → smallest (row,col) wins
    assert grid.most_likely() == (0, 0)


def test_excluding_every_cell_resets_to_uniform() -> None:
    grid = BeliefGrid(3)
    for cell in [(r, c) for r in range(3) for c in range(3)]:
        grid.exclude(cell)
    assert grid.mass_at((0, 0)) == pytest.approx(1 / 9)
    assert _total(grid) == pytest.approx(1.0)


def test_reweight_multiplies_then_renormalises() -> None:
    grid = BeliefGrid(3)  # uniform 1/9
    grid.reweight([(0, 0), (0, 1)], 4.0)  # boost two cells 4x
    assert grid.mass_at((0, 0)) == pytest.approx(grid.mass_at((0, 1)))
    assert grid.mass_at((0, 0)) > grid.mass_at((2, 2))
    assert _total(grid) == pytest.approx(1.0)


def test_reweight_by_one_is_a_no_op() -> None:
    grid = BeliefGrid(3)
    grid.observe_smell({"1,1": 0.5})
    before = grid.as_matrix()
    grid.reweight([(0, 0), (2, 2)], 1.0)
    assert grid.as_matrix() == before


def test_reweight_ignores_out_of_range_cells() -> None:
    grid = BeliefGrid(3)
    grid.reweight([(9, 9), (0, 0)], 3.0)  # (9,9) not on the board → skipped, no crash
    assert grid.mass_at((0, 0)) > grid.mass_at((2, 2))
    assert _total(grid) == pytest.approx(1.0)
