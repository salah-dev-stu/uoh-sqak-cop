"""Spectate stream (SH-2/3/4) — own-knowledge frames for the live arena.

A frame is constructible purely from the agent's OWN state: its position, its
belief grid, the barriers it knows, its last *received* hint, and the 8-hex head
of its latest sealed commit. It carries **no opponent true position, no opponent
belief, no sealed payload/nonce, and no own intent** (that stays sealed until
audit) — so streaming a match can never leak what makes the game zero-trust.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = 1


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def build_frame(rt: Any, phase: str, wire: dict | None = None,
                outcome: dict | None = None) -> dict[str, Any]:
    records = rt.book.records()
    hints = [h for h in rt.history if isinstance(h, dict) and "hint" in h]
    wire = wire or {}
    return {
        "spectate_schema": _SCHEMA, "turn": rt.step_number, "role": rt.role,
        "phase": phase, "me": list(rt.me.position), "belief": rt.belief.as_matrix(),
        "known_barriers": [list(b) for b in sorted(rt.barriers)],
        "last_hint": wire.get("hint") or (hints[-1]["hint"] if hints else ""),
        "last_intent": None,  # own intent is sealed; received intent unknown until audit
        "claims": {"capture_claim": wire.get("capture_claim"),
                   "claim_response": wire.get("claim_response"),
                   "win_claim": wire.get("win_claim")},
        "commit8": records[-1]["commit"][:8] if records else "",
        "sub_game": rt.sub_game_number, "outcome": outcome, "ts": _iso(),
    }


class JsonlListener:
    """Append one JSON frame per line; readers tolerate a torn final line (SH-8)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __call__(self, frame: dict[str, Any]) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(frame) + "\n")
