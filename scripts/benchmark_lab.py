#!/usr/bin/env python3
"""Win-rate benchmark lab (WB §6) — the evidence behind the strategy claims.

Runs the cop×thief matrix through the REAL engine (randomized starts ≥4 apart,
seeded, Dec-POMDP-legal information both sides). Markdown table to stdout.
Run:  uv run python scripts/benchmark_lab.py [--fast]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.constants import Outcome  # noqa: E402
from cipherchase.sdk.game_loop import run_game  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402

PKG = "cipherchase.strategy"
COPS = {
    "PoliceBrain": f"{PKG}.police_heuristic:PoliceBrain",
    "HerderCop": f"{PKG}.police_herder:HerderCop",
}
THIEVES = {
    "ThiefBrain": f"{PKG}.thief_heuristic:ThiefBrain",
    "EvaderV2": f"{PKG}.thief_evader_v2:EvaderBrain",
    "NaiveEdge": f"{PKG}.archetypes:NaiveEdgeThief",
    "Random": f"{PKG}.archetypes:RandomThief",
    "Still": f"{PKG}.archetypes:StillThief",
}


def run_cell(cop_spec: str, thief_spec: str, games: int) -> tuple[float, float]:
    captures, turns_total = 0, 0
    for i in range(games):
        cfg = ConfigManager.load("config/police")
        rng = random.Random(1000 + i)
        while True:
            cop = (rng.randrange(7), rng.randrange(7))
            thief = (rng.randrange(7), rng.randrange(7))
            if abs(cop[0] - thief[0]) + abs(cop[1] - thief[1]) >= 4:
                break
        cfg.shared["board_and_agents"]["cop_start"] = list(cop)
        cfg.shared["board_and_agents"]["thief_start"] = list(thief)
        cfg.private["play"]["seed"] = i
        cfg.private["strategy"]["police_class"] = cop_spec
        cfg.private["strategy"]["thief_class"] = thief_spec
        result = run_game(cfg)
        if result.outcome is Outcome.CAPTURE:
            captures += 1
            turns_total += result.turns
    rate = 100.0 * captures / games
    return rate, (turns_total / captures) if captures else 0.0


def main() -> int:
    games = 8 if "--fast" in sys.argv else 60
    print(f"capture-rate % (mean turns) · N={games}/cell · randomized starts\n")
    print("| cop \\ thief | " + " | ".join(THIEVES) + " |")
    print("|---" * (len(THIEVES) + 1) + "|")
    for cop_name, cop_spec in COPS.items():
        row = [cop_name]
        for thief_spec in THIEVES.values():
            rate, turns = run_cell(cop_spec, thief_spec, games)
            row.append(f"{rate:.1f} ({turns:.1f})" if rate else "0.0")
        print("| " + " | ".join(row) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
