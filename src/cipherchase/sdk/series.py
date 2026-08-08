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


def catch_up(*, n: int, peer: int, settled: set[int] | None = None) -> int:
    """Move to the index the peer is on — unless we have already played it.

    Holding the index stops drift but introduces deadlock: if an asymmetric
    failure leaves us on 2 and them on 5, both hold and neither moves, so the
    peer that is behind converges on the other.

    "Forward only" was a proxy for the real rule and it failed live: stale
    agreements from an opponent's aborted run declared sub-games 3 and 4 while
    they were really on 2, and chasing the highest index stranded us at 6 for the
    rest of the session. The rule that was meant is **never revisit an index we
    have SETTLED** — going back to one we never played replays nothing.
    """
    if not peer or peer == n or peer in (settled or set()):
        return n
    return peer


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
