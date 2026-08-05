"""When the cop asks "are you here?" — and when asking is just a free gift.

A `capture_claim` names our cop's post-move cell exactly, so under the hidden
position model an unconditional claim hands the thief our cop's location every
turn for the whole game. Claiming only on MOVE turns is the opposite mistake: a
thief that camps under a STAYing cop is never challenged (it cost us 25 turns
against najamjad).

So we claim on evidence, not on schedule: whenever our belief says the thief may
be on the cell we occupy. When the thief really is there the claim ends the game
and reveals nothing that matters; when it is provably elsewhere we say nothing.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _cop(transport) -> PeerRuntime:
    rt = PeerRuntime(role="police", cfg=ConfigManager.load(CONFIG / "police"),
                     transport=transport, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    return rt


def _claims(sent) -> list:
    return [w.get("capture_claim") for (_t, _k, w) in sent if w.get("sender") == "police"]


def test_the_cop_challenges_the_cell_its_belief_puts_the_thief_on() -> None:
    a, _b = make_pair()
    rt = _cop(a)
    rt.take_turn(None)
    here = rt.me.position
    rt.belief.reweight([here], 1e6)  # the thief is right here, we think
    rt.take_turn(None)
    assert _claims(a.sent)[-1] == list(rt.me.position)


def test_the_cop_does_not_donate_its_position_when_the_thief_is_far() -> None:
    a, _b = make_pair()
    rt = _cop(a)
    for _ in range(3):
        rt.belief.reweight([(6, 6)], 1e9)  # all the mass in the far corner
        rt.take_turn(None)
    assert _claims(a.sent)[-1] is None, "a claim the thief cannot answer is a free gift"


def test_a_thief_camped_under_a_staying_cop_is_still_challenged() -> None:
    # The najamjad regression, kept: co-location must be challenged even on a
    # STAY turn. Evidence-gated claiming must not reintroduce that blindness —
    # a co-located thief emits its scent at OUR cell, so belief peaks there.
    a, _b = make_pair()
    rt = _cop(a)
    seen = []
    for _ in range(4):
        rt.belief.reweight([rt.me.position], 1e6)
        rt.take_turn(None)
        seen.append(_claims(a.sent)[-1])
    assert all(claim is not None for claim in seen), "co-location is never silent"


def test_the_thief_never_claims() -> None:
    a, _b = make_pair()
    rt = PeerRuntime(role="thief", cfg=ConfigManager.load(CONFIG / "thief"),
                     transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    assert [w.get("capture_claim") for (_t, _k, w) in a.sent] == [None]
