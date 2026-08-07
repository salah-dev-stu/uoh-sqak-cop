"""Series driver — N sub-games, role alternation, fresh runtime each (§2.6)."""

from __future__ import annotations

import time
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


def settles(summary: Any) -> bool:
    """Did a game actually happen in this window?

    A technical loss IS a settlement — it has a result and it is scored, so the
    index advances and the sub-game is never replayed. But a window that saw
    ZERO turns never became a game: from the opponent's side it is
    indistinguishable from a handshake that never landed, and they will retry
    their index while we spend ours. That asymmetry is what opened the drift
    against imreeyal — the handshake is two independent one-way pushes, so one
    peer can enter a game the other does not believe exists.
    """
    if summary["result"] == "handshake_failed":
        return False
    return not (summary["result"] == "timeout" and summary["steps"] == 0)


def keep_waiting(*, elapsed: float, attempts: int, patience: float, max_attempts: int) -> bool:
    """Should we try this sub-game index again?

    Patience is TIME, not attempts. A zero-turn window costs the peer that
    suffers it a full turn budget, so a peer that did not suffer it must be able
    to outwait one — otherwise both sides obey every rule and simply run minutes
    apart. Counting attempts cannot express that: a refused agreement fails a
    window in milliseconds, so twenty "retries" evaporated in seconds and we quit
    five seconds before the opponent arrived.

    The attempt cap remains only as a hot-loop backstop, never as the budget.
    """
    return elapsed < patience and attempts <= max_attempts


def catch_up(*, n: int, peer: int) -> int:
    """Adopt a strictly-higher peer index. Forward only, or two peers ping-pong.

    Holding the index stops drift but introduces deadlock: if an asymmetric
    failure leaves us on 2 and them on 5, both of us hold and neither moves. The
    peer that is BEHIND catches up, so the series converges on one number without
    either side ever rewinding a sub-game that has already been played.
    """
    return max(n, peer)


def role_for(natural: str, sub_game_number: int) -> str:
    """Natural role on odd sub-games, swapped on even (both peers agree)."""
    flipped = "thief" if natural == "police" else "police"
    return natural if sub_game_number % 2 == 1 else flipped


def run_series(cfg: Any, natural_role: str, transport: Any, *, gate: Any = None,
               now: Any = None, listener: Any = None) -> SeriesResult:
    result = SeriesResult()
    num_games = int(cfg.shared["network_and_league"]["num_games"])
    retries = int(cfg.network.get("handshake_retries", 5))
    # Outwait one full turn budget of a peer stuck in a zero-turn window, plus
    # margin — the offset neither holding nor catch-up can close.
    patience = float(cfg.network.get("index_patience_seconds",
                                     cfg.network["turn_timeout_seconds"] + 60))
    clock = now or time.monotonic
    n, restarts, burned = 1, 0, 0
    opened = clock()
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
        if not settles(summary):
            ahead = catch_up(n=n, peer=runtime.peer_sub_game)
            if ahead != n:  # they are strictly ahead — converge instead of deadlocking
                n, burned, opened = ahead, 0, clock()
                continue
            burned += 1  # no game happened: RETRY the SAME sub-game — advancing the
            if keep_waiting(elapsed=clock() - opened, attempts=burned,
                            patience=patience, max_attempts=retries * 50):
                continue  # counter desyncs the two series (both play cop!)
            break  # opponent never appeared — no series, don't burn the schedule
        burned, opened = 0, clock()
        if summary["result"] == "restart" and restarts == 0:
            restarts, n = 1, 1  # auto-approved whole-series restart — replay once, ever
            transport.drain_stale()  # reference §2.6/§2.7: drain on restart — but never a queued agreement
            continue
        n += 1
    return result
