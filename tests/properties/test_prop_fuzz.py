"""IC-11: the lenient wire boundary never crashes on hostile input (fuzz twin of §2.4)."""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair
from hypothesis import given
from hypothesis import strategies as st

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer import turn_handler
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager
from properties.strategies import json_values

CONFIG = Path(__file__).resolve().parents[2] / "config" / "police"
_hostile = st.dictionaries(
    st.text(max_size=15), json_values | st.binary(max_size=8).map(list), max_size=8)


def _runtime() -> PeerRuntime:
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=ConfigManager.load(CONFIG), transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    return rt


_RT = _runtime()  # one stub, reused: process may mutate step state, never raises


@given(_hostile)
def test_from_dict_raises_only_type_or_value(wire) -> None:
    try:
        msg = TurnMessage.from_dict(wire)
    except (TypeError, ValueError):
        return  # the only sanctioned failure modes — never KeyError/AttributeError
    assert isinstance(msg, TurnMessage)


@given(_hostile)
def test_process_never_raises_on_hostile_input(wire) -> None:
    out = turn_handler.process(_RT, wire)  # contract: malformed rejected, never a crash
    assert out is not None
