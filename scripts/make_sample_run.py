#!/usr/bin/env python3
"""Regenerate docs/sample-run — BOTH sides of ONE offline game (F11 evidence).

One seeded self-match → the police AND thief artifact quartets (identical sealed
records, byte-identical symmetric mutual signature, role-scoped game_ids), plus
the 3D replay, the machine-forged tampered fixture, and the GUI proof PNGs.
Prints the tamper-sweep N for the committed log — the README "N mutations,
N caught" line and this number must move in the same commit (IC-6 guard).
Run:  uv run python scripts/make_sample_run.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.report import emit  # noqa: E402
from cipherchase.sdk.sdk import SimulationSdk  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402

OUT = Path("docs/sample-run")


def main() -> int:
    for old in OUT.glob("*.json"):
        if old.name.split("_")[0] in ("declaration", "config", "log", "result"):
            old.unlink()
    police = ConfigManager.load("config/police")
    thief = ConfigManager.load("config/thief")
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    ours, theirs = SimulationSdk.run_self_match_both(
        police, thief, generated_at=stamp, opponent="uoh-sqak")
    paths = emit.write_all(OUT, list(ours.values()) + list(theirs.values()))
    for path in paths:
        print("wrote", path)
    for script in ("make_replay_data.py", "make_tampered_replay.py", "make_visuals.py"):
        subprocess.run([sys.executable, f"scripts/{script}"], check=True)
    log = next(p for p in paths if p.name.startswith("log_") and "police" in p.name)
    records = json.loads(log.read_text())["records"]
    n = len(records) * 10 + sum(len(set(r["commit"])) for r in records)
    print(f"\nsample log: {log.name} · {len(records)} records · tamper-sweep N = {n}")
    print(f"README must state exactly:  {n} mutations, {n} caught")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
