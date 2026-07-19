#!/usr/bin/env python3
"""Train the tabular Q-learning cop vs an archetype mix → policy + learning curve.

Run:  uv run python scripts/train_qbrain.py
Writes analysis/qbrain_policy.json (policy + curve) and analysis/qbrain_learning.png.
Deterministic (seeded). The move logic is pure Python (F8); RL only shapes the cop.
The curve is the artifact — QBrain climbs toward the greedy ceiling, and ApexCop's
search (not learning) is what breaks past it (README §4).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, "src")
from cipherchase.domain.belief import BeliefGrid  # noqa: E402
from cipherchase.domain.board import Board  # noqa: E402
from cipherchase.domain.own_state import OwnState  # noqa: E402
from cipherchase.domain.rules import is_capture  # noqa: E402
from cipherchase.strategy.factory import load_brain  # noqa: E402
from cipherchase.strategy.qbrain import MOVES, N_STATES, encode_state  # noqa: E402

PKG = "cipherchase.strategy"
# Train vs the capturable archetypes (an equal-speed cop can't corner a perfect
# evader without barriers — that ceiling is ApexCop's job, not the Q-cop's). With a
# sparse reward the curve climbs visibly as the tabular policy learns pursuit.
THIEVES = [f"{PKG}.archetypes:RandomThief", f"{PKG}.archetypes:NaiveEdgeThief",
           f"{PKG}.archetypes:StillThief"]
B = Board(7)
EPISODES, WINDOW, MAX_TURNS = 12000, 100, 35
ALPHA, GAMMA, EPS = 0.2, 0.92, 0.3
NONE: frozenset = frozenset()


def _belief(cell):
    grid = BeliefGrid(7, smell_trust=1e6)
    grid.observe_smell({f"{cell[0]},{cell[1]}": 1.0})
    return grid


def _thief_step(brain, thief, cop):
    direction = brain._pick_move(OwnState("thief", thief), _belief(cop), NONE)
    return B.step(thief, direction, NONE)


def _start(rng):
    while True:
        cop = (rng.randrange(7), rng.randrange(7))
        thief = (rng.randrange(7), rng.randrange(7))
        if abs(cop[0] - thief[0]) + abs(cop[1] - thief[1]) >= 4:
            return cop, thief


def train():
    rng = random.Random(7)
    q = [[0.0] * 5 for _ in range(N_STATES)]
    thieves = [load_brain(t, B, {}, rng) for t in THIEVES]
    curve, wins = [], 0
    for ep in range(1, EPISODES + 1):
        thief_brain = thieves[ep % len(thieves)]
        cop, thief = _start(rng)
        captured = False
        for _ in range(MAX_TURNS):
            s = encode_state(cop, thief, B)
            legal = B.legal_moves(cop, NONE)
            a = MOVES.index(rng.choice(legal)) if rng.random() < EPS else q[s].index(max(q[s]))
            new_cop = B.step(cop, MOVES[a], NONE) if MOVES[a] in legal else cop
            if is_capture(B, new_cop, thief, NONE):
                q[s][a] += ALPHA * (10.0 - q[s][a])
                captured = True
                break
            thief = _thief_step(thief_brain, thief, new_cop)
            reward = -0.1  # sparse: only capture pays, so learning is visible over episodes
            s2 = encode_state(new_cop, thief, B)
            q[s][a] += ALPHA * (reward + GAMMA * max(q[s2]) - q[s][a])
            cop = new_cop
        wins += captured
        if ep % WINDOW == 0:
            curve.append(round(100 * wins / WINDOW, 1))
            wins = 0
    return [q[s].index(max(q[s])) for s in range(N_STATES)], curve


def _plot(curve, out: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    plt.figure(figsize=(7, 4))
    plt.plot([i * WINDOW for i in range(1, len(curve) + 1)], curve, color="#25e0ff", linewidth=2)
    plt.xlabel("training episodes")
    plt.ylabel(f"capture rate % ({WINDOW}-episode window)")
    plt.title("QBrain — tabular Q-learning curve (vs archetype mix)")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(out / "qbrain_learning.png", dpi=110)


def main() -> int:
    policy, curve = train()
    out = Path("analysis")
    out.mkdir(exist_ok=True)
    (out / "qbrain_policy.json").write_text(json.dumps({"policy": policy, "curve": curve}, indent=1))
    _plot(curve, out)
    print(f"policy: {len(policy)} states · window capture {curve[0] if curve else 0}% → "
          f"{curve[-1] if curve else 0}%")
    print("wrote analysis/qbrain_policy.json + analysis/qbrain_learning.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
