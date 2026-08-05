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
    parser.add_argument("command", choices=["self-match", "replay", "peer", "verify"])
    parser.add_argument("--config", default="config/police")
    parser.add_argument("--role", choices=["police", "thief"], default="police")
    parser.add_argument("--out", default="logs")
    parser.add_argument("--log", default="")
    parser.add_argument("--at", default="")
    # Naming the opponent group turns a peer run into a reported league series.
    parser.add_argument("--opponent", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify":  # offline re-audit of any log — no keys, no network
        from cipherchase.report.verify import render, verify_log

        report = verify_log(args.log)
        print(render(report))
        return 0 if report["verdict"] == "Verified OK" else 1
    if args.command == "replay":  # pragma: no cover (needs a display)
        from cipherchase.gui.replay import run_replay

        run_replay(args.log)
        return 0
    cfg = ConfigManager.load(args.config)
    if args.command == "peer":  # pragma: no cover — live sockets (interop test drives it)
        import json

        from cipherchase.sdk.league_reports import write_league_series

        outcome = SimulationSdk.run_peer(cfg, natural_role=args.role)
        print(json.dumps({k: outcome[k] for k in ("game_id", "game_uid", "sub_games")}))
        if args.opponent:  # a counted league series reports the game it PLAYED
            stamp = args.at or datetime.now(UTC).isoformat()
            for path in write_league_series(cfg, outcome, args.out, generated_at=stamp,
                                            opponent=args.opponent):
                print(path)
        return 0
    stamp = args.at or datetime.now(UTC).isoformat()
    for path in SimulationSdk.write_reports(cfg, args.out, generated_at=stamp):
        print(path)
    return 0
