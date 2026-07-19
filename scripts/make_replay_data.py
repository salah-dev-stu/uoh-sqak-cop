#!/usr/bin/env python3
"""Capture a game as per-turn frames for the 3D replay — via the engine hook.

No second engine: this is a thin consumer of ``run_game(on_frame=...)`` (IH-19).
Run:  uv run python scripts/make_replay_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.sdk.game_loop import run_game  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402


def capture(config_dir: str = "config/police") -> dict:
    from cipherchase.gui.replay_data import verify_records

    cfg = ConfigManager.load(config_dir)
    frames: list[dict] = []
    result = run_game(cfg, on_frame=frames.append)
    return {
        "viz_schema": 2,
        "size": cfg.shared["board_and_agents"]["board_size"],
        "outcome": result.outcome.value,
        "frames": frames,
        "records": result.records,
        "verdicts": verify_records(result.records),
    }


if __name__ == "__main__":
    data = capture()
    out = Path("docs/sample-run/replay3d.json")
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"wrote {out}: {len(data['frames'])} frames, outcome={data['outcome']}")
