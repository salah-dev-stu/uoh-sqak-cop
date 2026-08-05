"""Rules 46/47 concessions — the ending only the THIEF can see (SPEC §3.1).

Enclosure is a property of the thief's hidden cell, so the cop cannot infer it.
A thief that settles CAPTURE silently leaves the cop to time out and report
TIMEOUT: one sub-game, two honest descriptions, which App-E rule 35 scores 0/0
for BOTH teams. So the concession must reach the wire.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _thief(transport) -> PeerRuntime:
    cfg = ConfigManager.load(CONFIG / "thief")
    rt = PeerRuntime(role="thief", cfg=cfg, transport=transport, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    return rt


def test_thief_concedes_a_rule_47_enclosure_on_the_wire() -> None:
    a, _b = make_pair()
    rt = _thief(a)
    assert rt.me.position == (3, 3)
    rt.barriers = frozenset({(2, 3), (4, 3), (3, 2)})  # three walls already down
    out = rt.handle(  # the cop's fourth barrier closes the box
        TurnMessage(step=1, sender="police", barrier_placed=[3, 4]).to_dict())
    assert out.result == ("capture", "police")
    assert out.claim_response == {"claim": [3, 3], "caught": True}
    sent = [w for (_t, _k, w) in a.sent if (w.get("claim_response") or {}).get("caught")]
    assert sent, "an enclosure the cop cannot see MUST be announced, not settled silently"
    assert sent[-1]["claim_response"]["claim"] == [3, 3]


def test_thief_concedes_a_rule_46_barrier_on_its_own_cell() -> None:
    a, _b = make_pair()
    rt = _thief(a)
    out = rt.handle(TurnMessage(step=1, sender="police", barrier_placed=[3, 3]).to_dict())
    assert out.result == ("capture", "police")
    assert out.claim_response["claim"] == [3, 3]


def test_an_open_exit_is_not_a_concession() -> None:
    a, _b = make_pair()
    rt = _thief(a)
    rt.barriers = frozenset({(2, 3), (4, 3)})
    out = rt.handle(TurnMessage(step=1, sender="police", barrier_placed=[3, 2]).to_dict())
    assert out.result is None, "one legal move left is not an enclosure"
    assert not [w for (_t, _k, w) in a.sent if (w.get("claim_response") or {}).get("caught")]


def test_police_settles_capture_on_a_concession_naming_another_cell() -> None:
    # A concession names the THIEF's cell, not the cell the cop claimed — the cop
    # must settle on it all the same (it is the shape a boxed-in thief sends).
    a, _b = make_pair()
    cfg = ConfigManager.load(CONFIG / "police")
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    out = rt.handle(TurnMessage(
        step=1, sender="thief",
        claim_response={"claim": [6, 6], "caught": True}).to_dict())
    assert out.result == ("capture", "police")
