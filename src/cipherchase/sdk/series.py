"""Series driver — N sub-games, role alternation, fresh runtime each (§2.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cipherchase.peer.runtime import PeerRuntime


@dataclass
class SeriesResult:
    game_id: str = ""
    game_uid: str = ""
    summaries: list[dict[str, Any]] = field(default_factory=list)

    def wins_for(self, group_role: str) -> int:
        return sum(1 for s in self.summaries if s["winner"] == s["role"] == group_role)


def role_for(natural: str, sub_game_number: int) -> str:
    """Natural role on odd sub-games, swapped on even (both peers agree)."""
    flipped = "thief" if natural == "police" else "police"
    return natural if sub_game_number % 2 == 1 else flipped


def run_series(cfg: Any, natural_role: str, transport: Any, *, gate: Any = None,
               now: Any = None, listener: Any = None) -> SeriesResult:
    result = SeriesResult()
    num_games = int(cfg.shared["network_and_league"]["num_games"])
    n, restarts = 1, 0
    while n <= num_games:
        # NOTE: no drain here — a fast peer's next agreement may already be queued
        # (reference behaviour: drain only on explicit restart, §2.6/§2.7).
        runtime = PeerRuntime(
            role=role_for(natural_role, n), cfg=cfg, transport=transport,
            sub_game_number=n, gate=gate, now=now, listener=listener,
        )
        summary = runtime.run()
        result.game_id = result.game_id or summary["game_id"]
        result.game_uid = result.game_uid or summary["game_uid"]
        result.summaries.append(summary)
        if summary["result"] == "restart" and restarts == 0:
            restarts, n = 1, 1  # auto-approved whole-series restart — replay once, ever
            transport.drain_stale()  # reference §2.6/§2.7: drain on restart — but never a queued agreement
            continue
        n += 1
    return result
