"""Equivocation: one step, two different commits (imreeyal's 3.13 point).

A retry repeats a step with the SAME commit and is simply dropped. A peer that
sends two DIFFERENT commits for one step has equivocated — it kept two stories
open and can reveal whichever suits the audit. Keying dedup on the step alone
drops the second silently, so the contradiction leaves no trace; keying on the
commit keeps both, which turns the divergence into evidence.

We do not act on it unilaterally — "reported, never a unilateral rewrite: the
logs decide" (rule 35) — we record it, sealed, so the audit can.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _cop(transport) -> PeerRuntime:
    rt = PeerRuntime(role="police", cfg=ConfigManager.load(CONFIG / "police"),
                     transport=transport, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    return rt


def _turn(step: int, commit: str) -> dict:
    return TurnMessage(step=step, sender="thief", commit=commit,
                       smell_grid={"3,3": 0.9}).to_dict()


def test_a_plain_retry_is_dropped_without_crying_foul() -> None:
    a, _b = make_pair()
    rt = _cop(a)
    rt.handle(_turn(1, "aa"))
    out = rt.handle(_turn(1, "aa"))  # same step, same commit — a retry
    assert out.duplicate is True and out.equivocation is None
    assert not [h for h in rt.history if h.get("equivocation")]


def test_two_commits_for_one_step_are_recorded_as_evidence() -> None:
    a, _b = make_pair()
    rt = _cop(a)
    rt.handle(_turn(1, "aa"))
    out = rt.handle(_turn(1, "bb"))  # same step, a DIFFERENT story
    assert out.duplicate is True, "we still refuse to act on it twice"
    assert out.equivocation == {"step": 1, "commits": ["aa", "bb"]}
    logged = [h for h in rt.history if h.get("equivocation")]
    assert logged == [{"equivocation": {"step": 1, "commits": ["aa", "bb"]}}]


def test_the_evidence_is_sealed_into_our_own_audit_trail() -> None:
    # Sealed like every other record, so our report carries proof we saw it and
    # the opponent cannot claim we invented it after the fact.
    a, _b = make_pair()
    rt = _cop(a)
    rt.handle(_turn(1, "aa"))
    rt.handle(_turn(1, "bb"))
    sealed = [r for r in rt.book.records() if r["payload"].get("type") == "equivocation"]
    assert len(sealed) == 1
    record = sealed[0]
    CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
    assert record["payload"]["commits"] == ["aa", "bb"]


def test_an_honest_series_records_nothing() -> None:
    a, _b = make_pair()
    rt = _cop(a)
    for step in (1, 2, 3):
        rt.handle(_turn(step, f"c{step}"))
    assert not [r for r in rt.book.records() if r["payload"].get("type") == "equivocation"]
