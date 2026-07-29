"""Process one incoming sealed turn (PRD_league_runtime §2.4).

Lenient at the boundary (foreign extras filtered, malformed rejected without a
crash), idempotent on duplicate steps, honest on claims — the audit reveals the
sealed truth anyway, so lying in a ``claim_response`` only convicts you.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cipherchase.domain.hint_belief import apply_hint, extract_claim, in_cone
from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.turn_sender import send_final


@dataclass
class Incoming:
    result: tuple[str, str] | None = None
    claim_response: dict[str, Any] | None = None
    duplicate: bool = False
    malformed: bool = False


def _fuse_hint(rt: Any, hint: str | None, prev_peak: Any) -> None:
    """Calibrate the opponent's honesty on its LAST claim, then nudge belief (F6/F7)."""
    if rt.bluff_weight <= 0.0:
        return
    new_peak = rt.belief.most_likely()
    if rt.last_claim is not None:  # did the peak actually move the way they said?
        rt.honesty.record(in_cone(prev_peak, new_peak, rt.last_claim))
    rt.last_claim = extract_claim(hint or "")
    apply_hint(rt.belief, new_peak, rt.last_claim, rt.honesty.p_honest(),
               bluff_weight=rt.bluff_weight, board_size=rt.board.size)


def process(rt: Any, wire: dict[str, Any]) -> Incoming:
    try:
        msg = TurnMessage.from_dict(dict(wire))
        step = int(msg.step)
    except (TypeError, ValueError, AttributeError):
        rt.history.append({"malformed": True})
        return Incoming(malformed=True)
    if step <= rt.last_seen_step:
        return Incoming(duplicate=True)
    if rt.last_seen_step == 0 and step != 1:
        # Strict alternation: a fresh game's first inbound step is ALWAYS 1. Anything
        # later is a stale echo of an aborted game (series restart) — never let it
        # poison last_seen_step or real turns become "duplicates".
        return Incoming(duplicate=True)
    rt.last_seen_step = step
    if msg.barrier_placed:
        rt.barriers = rt.barriers | {tuple(msg.barrier_placed)}
    prev_peak = rt.belief.most_likely()
    rt.belief = rt.decoder.update(msg.smell_grid or {})  # matched-filter localisation (WB §3)
    _fuse_hint(rt, msg.hint, prev_peak)
    rt.history.append({"step": step, "from": msg.sender, "hint": msg.hint})
    claim_response = None
    if msg.capture_claim is not None and rt.role == "thief":
        caught = tuple(msg.capture_claim) == rt.me.position
        claim_response = {"claim": list(msg.capture_claim), "caught": caught}
        if caught:
            send_final(rt, claim_response)
            return Incoming(result=("capture", "police"), claim_response=claim_response)
    if rt.role == "police" and msg.claim_response and msg.claim_response.get("caught"):
        return Incoming(result=("capture", "police"))
    if msg.win_claim:
        win_type = str(msg.win_claim.get("type", "unknown"))
        return Incoming(result=(win_type, rt.opp_role))
    return Incoming(claim_response=claim_response)
