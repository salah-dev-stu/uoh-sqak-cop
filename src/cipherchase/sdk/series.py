"""Series driver — N sub-games, role alternation, fresh runtime each (§2.6)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cipherchase.peer.runtime import PeerRuntime
from cipherchase.sdk.index_rules import (  # re-exported: the rules live next door
    catch_up,
    keep_waiting,
    settles,
)


@dataclass
class SeriesResult:
    game_id: str = ""
    game_uid: str = ""
    summaries: list[dict[str, Any]] = field(default_factory=list)

    def wins_for(self, group_role: str) -> int:
        return sum(1 for s in self.summaries if s["winner"] == s["role"] == group_role)


def opponent_url_for(net: dict, *, our_role: str) -> str:
    """Which address to dial this sub-game.

    A role-split opponent runs cop and thief as separate services, so the peer we
    face alternates with our own role: their COP answers on the windows where we
    are thief. One address for a whole series dials the wrong service on half of
    it, and the wrong service ANSWERS — so it surfaces as a refusal rather than
    as a connection error, which is the harder shape to diagnose.
    """
    theirs = "police" if our_role == "thief" else "thief"
    return net.get(f"opponent_url_{theirs}") or net["opponent_url"]


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
    # A relaunch inherits whatever the peer queued during the run that failed,
    # and a stale agreement declaring a high index will otherwise drive catch-up.
    # Index-aware: a peer that binds first and pushes a good opening agreement
    # keeps it — draining wholesale failed the punctual side (see Inboxes).
    transport.drain_backlog(opening=n)
    opened = clock()
    while n <= num_games:
        # NOTE: no drain here — a fast peer's next agreement may already be queued
        # (reference behaviour: drain only on explicit restart, §2.6/§2.7).
        role = role_for(natural_role, n)
        transport.opponent_url = opponent_url_for(cfg.network, our_role=role)
        runtime = PeerRuntime(
            role=role, cfg=cfg, transport=transport,
            sub_game_number=n, gate=gate, now=now, listener=listener,
        )
        summary = runtime.run()
        result.game_id = result.game_id or summary["game_id"]
        result.game_uid = result.game_uid or summary["game_uid"]
        result.summaries.append(summary)
        if settles(summary):
            # Say it. A failure-only log makes a healthy series and a dead one
            # look identical, and we killed a live peer mid-series on the
            # strength of that silence — four settled games, audits verified
            # both sides, gone.
            audit = (summary.get("audit") or {}).get("passed")
            print(f"  sub-game {n}: {summary['result']} ({summary['steps']} steps), "
                  f"winner {summary['winner']}, audit {audit}")
        if not settles(summary):
            # Surface it NOW. A stalled series never reaches its summary, so a
            # reason held until the end is unreachable exactly when both teams
            # are staring at silence trying to work out whose half is broken.
            print(f"  sub-game {n}: {summary['result']} — {summary.get('note', '')}")
            ahead = catch_up(n=n, peer=runtime.peer_sub_game,
                             settled={s["sub_game_number"] for s in result.summaries
                                      if settles(s)})
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
