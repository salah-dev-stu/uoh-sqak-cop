#!/usr/bin/env python3
"""Win-rate benchmark lab (WB §6) — the evidence behind the strategy claims.

Runs the cop×thief matrix through the REAL engine (randomized starts ≥4 apart,
seeded, Dec-POMDP-legal information both sides). Markdown table + an Elo ladder
(every game is a rated match, K=16, base 1000) to stdout — the committed artifact
lives at analysis/benchmark_results.md.
Run:  uv run python scripts/benchmark_lab.py [--fast]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.analysis.stats import elo_update, wilson_interval  # noqa: E402
from cipherchase.constants import Outcome  # noqa: E402
from cipherchase.sdk.game_loop import run_game  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402

PKG = "cipherchase.strategy"
COPS = {
    "PoliceBrain": f"{PKG}.police_heuristic:PoliceBrain",
    "HerderCop": f"{PKG}.police_herder:HerderCop",
    "Expectimax": f"{PKG}.police_expectimax:PoliceExpectimax",
    "ApexCop": f"{PKG}.apex_cop:ApexCop",
}
THIEVES = {
    "ThiefBrain": f"{PKG}.thief_heuristic:ThiefBrain",
    "EvaderV2": f"{PKG}.thief_evader_v2:EvaderBrain",
    "NaiveEdge": f"{PKG}.archetypes:NaiveEdgeThief",
    "Random": f"{PKG}.archetypes:RandomThief",
    "Still": f"{PKG}.archetypes:StillThief",
}


def run_cell(cop: tuple[str, str], thief: tuple[str, str], games: int, outcomes: list) -> str:
    (cop_name, cop_spec), (thief_name, thief_spec) = cop, thief
    captures = 0
    for i in range(games):
        cfg = ConfigManager.load("config/police")
        rng = random.Random(1000 + i)
        while True:
            c = (rng.randrange(7), rng.randrange(7))
            t = (rng.randrange(7), rng.randrange(7))
            if abs(c[0] - t[0]) + abs(c[1] - t[1]) >= 4:
                break
        cfg.shared["board_and_agents"]["cop_start"] = list(c)
        cfg.shared["board_and_agents"]["thief_start"] = list(t)
        cfg.private["play"]["seed"] = i
        cfg.private["strategy"]["police_class"] = cop_spec
        cfg.private["strategy"]["thief_class"] = thief_spec
        won = run_game(cfg).outcome is Outcome.CAPTURE
        captures += won
        outcomes.append((cop_name, thief_name, won))
    lo, hi = wilson_interval(captures, games)
    rate = 100.0 * captures / games
    if not captures:
        return f"0.0 [0-{hi * 100:.0f}]"
    return f"{rate:.0f} [{lo * 100:.0f}-{hi * 100:.0f}]"


def elo_ladder(outcomes: list, epochs: int = 10) -> dict[str, float]:
    """Order-independent ratings: iterate epochs over a seeded shuffle of all games."""
    elo = dict.fromkeys(list(COPS) + list(THIEVES), 1000.0)
    rng = random.Random(0)
    for _ in range(epochs):
        replay = outcomes[:]
        rng.shuffle(replay)
        for cop_name, thief_name, won in replay:
            elo[cop_name], elo[thief_name] = elo_update(
                elo[cop_name], elo[thief_name], winner_first=won)
    return elo


def main() -> int:
    games = 8 if "--fast" in sys.argv else 60
    outcomes: list = []
    print(f"capture-rate % [95% Wilson CI] · N={games}/cell · randomized starts · seeded\n")
    print("| cop \\ thief | " + " | ".join(THIEVES) + " |")
    print("|---" * (len(THIEVES) + 1) + "|")
    for cop in COPS.items():
        row = [cop[0]] + [run_cell(cop, thief, games, outcomes) for thief in THIEVES.items()]
        print("| " + " | ".join(row) + " |")
    print(f"\nElo ladder ({len(outcomes)} rated games, K=16, base 1000, 10 shuffled epochs):\n")
    print("| brain | Elo |")
    print("|---|---|")
    for name, rating in sorted(elo_ladder(outcomes).items(), key=lambda kv: -kv[1]):
        print(f"| {name} | {rating:.0f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
