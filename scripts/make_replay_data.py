#!/usr/bin/env python3
"""Capture a game as per-turn frames for the 3D replay (cop/thief/barriers/scent/belief).

Runs the real engine with instrumentation and writes docs/sample-run/replay3d.json.
Run:  uv run python scripts/make_replay_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.domain import rules  # noqa: E402
from cipherchase.domain.belief import BeliefGrid  # noqa: E402
from cipherchase.domain.board import Board  # noqa: E402
from cipherchase.domain.own_state import OwnState  # noqa: E402
from cipherchase.domain.rules import can_place_barrier  # noqa: E402
from cipherchase.domain.smell import SmellField  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402
from cipherchase.strategy.factory import load_brain  # noqa: E402


def capture() -> dict:
    cfg = ConfigManager.load("config/police")
    ba, mb, ph = (cfg.shared[k] for k in ("board_and_agents", "movement_and_barriers", "pheromones"))
    board = Board(ba["board_size"])
    strat, trust = cfg.private["strategy"], cfg.private["belief"]["smell_trust"]
    cop_brain = load_brain(strat["police_class"], board, params=strat)
    thief_brain = load_brain(strat["thief_class"], board, params=strat)
    cop, thief = OwnState("police", tuple(ba["cop_start"])), OwnState("thief", tuple(ba["thief_start"]))
    smell = SmellField(board.size, ph["grid_size"], ph["center_intensity"], ph["decay"], ph["falloff"])
    barriers: frozenset = frozenset()
    frames, outcome = [], "survival"
    for step in range(1, mb["max_moves"] + 1):
        smell.deposit(thief.position)
        smell.decay_all()
        cop_belief = BeliefGrid(board.size, trust)
        cop_belief.observe_smell(smell.snapshot())
        frames.append({
            "turn": step, "cop": list(cop.position), "thief": list(thief.position),
            "barriers": sorted([list(b) for b in barriers]),
            "scent": smell.snapshot(), "belief": cop_belief.as_matrix(),
        })
        decision = cop_brain.decide(cop, cop_belief, barriers)
        target = board.step(cop.position, decision.direction, barriers)
        if decision.barrier_cell and decision.barrier_cell != target and can_place_barrier(
            board, cop.position, decision.barrier_cell, barriers, mb["max_barriers"]
        ):
            barriers = barriers | {decision.barrier_cell}
        cop = cop.moved_to(target)
        if rules.is_capture(board, cop.position, thief.position, barriers,
                            require_cop_adjacent=mb["require_cop_adjacent"]):
            outcome = "capture"
            break
        tb = BeliefGrid(board.size, trust)
        tb.observe_smell({f"{cop.position[0]},{cop.position[1]}": ph["center_intensity"]})
        thief = thief.moved_to(board.step(thief.position, thief_brain.decide(thief, tb, barriers).direction, barriers))
    return {"size": board.size, "outcome": outcome, "frames": frames}


if __name__ == "__main__":
    data = capture()
    out = Path("docs/sample-run/replay3d.json")
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"wrote {out}: {len(data['frames'])} frames, outcome={data['outcome']}")
