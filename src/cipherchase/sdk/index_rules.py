"""Which sub-game index a series plays next, and when one is spent.

Three pure rules, kept apart from the loop that applies them because each was
learned from a live match and each is tested as arithmetic:
``settles`` (did a game happen?), ``catch_up`` (whose index wins?), and
``keep_waiting`` (how long is one index worth?).
"""

from __future__ import annotations

from typing import Any

# A verdict the board produced: these settle even at step zero, because an
# audit forfeit can land before either peer moves and must never be replayed.
TERMINAL_RESULTS = ("capture", "survival", "tamper_forfeit")


def settles(summary: Any) -> bool:
    """Did a game actually happen in this window?

    A technical loss IS a settlement — it has a result and it is scored, so the
    index advances and the sub-game is never replayed. But a window that saw
    ZERO turns never became a game: from the opponent's side it is
    indistinguishable from a handshake that never landed, and they will retry
    their index while we spend ours. That asymmetry is what opened the drift
    against imreeyal — the handshake is two independent one-way pushes, so one
    peer can enter a game the other does not believe exists.

    Written first as `result == "timeout" and steps == 0`, which was narrower
    than the sentence above it: EVERY other zero-turn outcome — opponent_quit,
    quit, error, stopped — still settled and spent the index. Against ahk-yosi
    their peer died before play, we scored a zero-turn opponent_quit, advanced,
    and then correctly refused to replay the index they were still sitting on.
    Four dead sub-games. The question is "did turns happen", not "which label
    did we put on the silence".
    """
    if summary["result"] == "handshake_failed":
        return False  # no game began; the index is untouched whatever else is set
    if summary["result"] in TERMINAL_RESULTS:
        return True   # a real verdict is a game whatever the step count
    return summary["steps"] > 0


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
