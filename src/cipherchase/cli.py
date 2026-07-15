"""Command-line entry (R1) — parse args, call the SDK, print paths. No logic here.

``self-match`` plays a full offline game and writes the 4 JSON reports (the
grader's proof, 0 tokens, no keys). ``replay`` opens the Tkinter Replay Viewer.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from cipherchase.sdk.sdk import SimulationSdk
from cipherchase.shared.config import ConfigManager


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cipherchase")
    parser.add_argument("command", choices=["self-match", "replay"])
    parser.add_argument("--config", default="config/police")
    parser.add_argument("--out", default="logs")
    parser.add_argument("--log", default="")
    parser.add_argument("--at", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "replay":  # pragma: no cover (needs a display)
        from cipherchase.gui.replay import run_replay

        run_replay(args.log)
        return 0
    stamp = args.at or datetime.now(UTC).isoformat()
    cfg = ConfigManager.load(args.config)
    for path in SimulationSdk.write_reports(cfg, args.out, generated_at=stamp):
        print(path)
    return 0
