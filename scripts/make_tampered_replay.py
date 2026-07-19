#!/usr/bin/env python3
"""Build the TAMPERED replay fixture (MV-B3) — a forged step, machine-made.

Copies replay3d.json, forges one sealed payload's move, and re-runs the SAME
verifier the peers use — so the red shatter in the arena is real cryptography,
never hand-edited data.  Run:  uv run python scripts/make_tampered_replay.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.gui.replay_data import replay_verdict, verify_records  # noqa: E402

SRC = Path("docs/sample-run/replay3d.json")
OUT = Path("docs/sample-run/replay3d_tampered.json")

if __name__ == "__main__":
    data = json.loads(SRC.read_text())
    victim = len(data["records"]) // 2
    record = data["records"][victim]
    record["payload"]["move"] = "N" if record["payload"]["move"] != "N" else "S"  # forge
    data["verdicts"] = verify_records(data["records"])
    data["outcome"] = "tamper_forfeit"
    OUT.write_text(json.dumps(data))
    print(f"forged step {record['payload']['step']} -> {OUT}: {replay_verdict(data['records'])}")
