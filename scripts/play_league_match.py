#!/usr/bin/env python3
"""Play a COUNTED league match and persist the full evidence (F14).

Run:  uv run python scripts/play_league_match.py <opponent-group> <role>
Runs the live peer series (real MCP, config-driven), then writes the complete
series record — every sub-game summary incl. sealed records and audit verdicts —
to docs/league/<group>/series_<uid>.json for the repo, and prints the tally.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
from cipherchase.sdk.sdk import SimulationSdk  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402


def main() -> int:
    group, role = sys.argv[1], sys.argv[2]
    cfg = ConfigManager.load(f"config/{role}")
    listener = None
    if len(sys.argv) > 3:  # optional live spectate spool (own-knowledge frames only)
        from cipherchase.sdk.spectate import JsonlListener
        listener = JsonlListener(sys.argv[3])
    outcome = SimulationSdk.run_peer(cfg, natural_role=role, listener=listener)
    out = Path("docs/league") / group
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"series_{outcome['game_uid'][:8]}_{role}.json"
    path.write_text(json.dumps(outcome, indent=1))
    print(f"\nseries record → {path}")
    for sub in outcome["sub_games"]:
        print(f"  sub {sub['sub_game_number']} ({sub['role']}): "
              f"{sub['result']}/{sub['winner']} · audit {sub['audit']['status']}"
              f"{' PASSED' if sub['audit'].get('passed') else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
