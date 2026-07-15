#!/usr/bin/env python3
"""OAT sensitivity analysis (excellence, FR-K4): how ``smell_trust`` sharpens belief.

For each smell_trust the thief's scent is deposited at many true cells, the cop's
Bayesian belief observes it, and we measure the mean localisation error (Manhattan
distance from the belief peak to the true cell). Headless (matplotlib Agg) →
docs/sample-run/sensitivity_smell_trust.png + a printed table.
Run:  uv run --with matplotlib python scripts/sensitivity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path("src")))
from cipherchase.domain.belief import BeliefGrid  # noqa: E402
from cipherchase.domain.board import Board  # noqa: E402
from cipherchase.domain.smell import SmellField  # noqa: E402

BOARD = Board(7)
TRUE_CELLS = [(r, c) for r in range(1, 6) for c in range(1, 6)]
SWEEP = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]


def mean_localisation_error(smell_trust: float) -> float:
    total = 0.0
    for cell in TRUE_CELLS:
        smell = SmellField(7, 5, 0.9, 0.1, 0.7)
        smell.deposit(cell)
        belief = BeliefGrid(7, smell_trust=smell_trust)
        belief.observe_smell(smell.snapshot())
        total += BOARD.distance(belief.most_likely(), cell)
    return total / len(TRUE_CELLS)


def main() -> int:
    errors = [mean_localisation_error(trust) for trust in SWEEP]
    print("smell_trust  mean_localisation_error(cells)")
    for trust, err in zip(SWEEP, errors, strict=True):
        print(f"{trust:>10}  {err:.3f}")
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(SWEEP, errors, "o-")
    ax.set_xlabel("smell_trust")
    ax.set_ylabel("mean localisation error (cells)")
    ax.set_title("OAT: belief accuracy vs smell_trust")
    fig.savefig(Path("docs/sample-run/sensitivity_smell_trust.png"), dpi=120, bbox_inches="tight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
