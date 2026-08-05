"""One sealed TurnMessage per turn (PRD_league_runtime §2.3/§2.4).

Decide → apply (HOLD fallback — never stall) → seal the plaintext locally →
send ONE wire message: commit + hint + own smell trail + claims. The move,
intent, and nonce stay hidden until the end-of-game audit.
"""

from __future__ import annotations

from typing import Any

from cipherchase.constants import Direction
from cipherchase.domain.protocol import TurnMessage
from cipherchase.domain.rules import can_place_barrier
from cipherchase.exceptions import IllegalMoveError
from cipherchase.peer.sealing import move_payload, now_iso, trim_words


def take_turn(rt: Any, claim_response: dict[str, Any] | None) -> tuple[str, str] | None:
    """Play one turn; return a terminal ``(result, winner)`` or None."""
    rt.step_number += 1
    step = rt.step_number
    decision = rt.brain.decide(rt.me, rt.belief, rt.barriers)
    decision.intent, decision.hint = rt.talk_for(step, decision.direction)
    try:
        target = rt.board.step(rt.me.position, decision.direction, rt.barriers)
    except IllegalMoveError:  # HOLD fallback — never stall the loop
        target = rt.me.position
        decision.direction = Direction.STAY
    commit, _nonce = rt.book.seal(move_payload(step, rt.me, decision))
    barrier_placed = _maybe_barrier(rt, decision.barrier_cell, target)
    rt.me = rt.me.moved_to(target)
    rt.my_smell.decay_all()
    rt.my_smell.deposit(rt.me.position)
    win_claim, result = None, None
    if rt.role == "thief" and step >= rt.max_steps:
        win_claim, result = {"type": "survival"}, ("survival", "thief")
    message = TurnMessage(
        step=step, sender=rt.role, hint=trim_words(decision.hint, rt.hint_max_words),
        smell_grid=rt.my_smell.snapshot(), commit=commit, timestamp=now_iso(),
        barrier_placed=barrier_placed,
        capture_claim=_capture_claim(rt),
        claim_response=claim_response, win_claim=win_claim,
    )
    rt.transport.send_turn(message.to_dict())
    return result


def send_final(rt: Any, claim_response: dict[str, Any]) -> None:
    """The caught thief's mandatory last message: HOLD + 'You got me.'"""
    rt.step_number += 1
    from cipherchase.domain.brains import Decision

    decision = Decision(direction=Direction.STAY, intent="truth", hint="You got me.")
    commit, _nonce = rt.book.seal(move_payload(rt.step_number, rt.me, decision))
    message = TurnMessage(
        step=rt.step_number, sender=rt.role, hint="You got me.",
        smell_grid=rt.my_smell.snapshot(), commit=commit, timestamp=now_iso(),
        claim_response=claim_response,
    )
    rt.transport.send_turn(message.to_dict())


def _capture_claim(rt: Any) -> list[int] | None:
    """Ask "are you here?" on evidence, never on schedule.

    A claim names our post-move cell exactly, so an unconditional one hands the
    thief our position every turn under the hidden-position model. We claim when
    our belief puts the thief on the cell we occupy: if it is really there the
    game ends and the disclosure is free; if it is provably elsewhere, silence
    costs us nothing. A co-located thief emits its scent at our own cell, so the
    peak lands here and a camper is still challenged — including on a STAY turn,
    which is the case that cost us 25 unchallenged turns against najamjad.
    """
    if rt.role != "police":
        return None
    here = rt.me.position
    floor = float(rt.cfg.private["strategy"].get("claim_mass_threshold", 0.08))
    if rt.belief.most_likely() == here or rt.belief.mass_at(here) >= floor:
        return list(here)
    return None


def _maybe_barrier(rt: Any, q: Any, target: Any) -> list[int] | None:
    if rt.role != "police" or not q or q == target:
        return None
    if not can_place_barrier(rt.board, rt.me.position, q, rt.barriers, rt.barriers_max):
        return None
    rt.barriers = rt.barriers | {q}
    rt.me = rt.me.with_barrier(q)
    return list(q)
