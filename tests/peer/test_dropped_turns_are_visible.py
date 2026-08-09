"""A turn we ignore must say so, with both indices (ahk-yosi, 2026-08-10).

They asked a fair question — "did our step-1 turn arrive, and what index were
you on?" — and we could not answer it. Our peer logs every inbound call as an
identical `POST /mcp` line with no tool name, and a turn dropped as duplicate or
malformed vanished without a word. So "you were silent" and "we ignored you"
look the same from our side, and the only team who could complete the picture
was the one holding the records we had discarded.

Same lesson as the refusal notes: a stalled series never reaches its summary, so
anything worth knowing has to be said as it happens.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _runtime(sub_game: int = 2):
    a, _b = make_pair()
    return PeerRuntime(role="police", cfg=ConfigManager.load(CONFIG / "police"),
                       transport=a, sub_game_number=sub_game)


def test_an_ignored_turn_names_the_sender_step_and_our_index(capsys) -> None:
    rt = _runtime(sub_game=2)
    rt.sm.transition(State.WAITING)
    # step 3 before step 1 — the shape of a peer on another index, or a stale echo
    rt.handle(TurnMessage(step=3, sender="thief", smell_grid={"1,1": 0.4}).to_dict())
    out = capsys.readouterr().out
    assert "ignored" in out and "thief" in out
    assert "step 3" in out, out          # what they sent
    assert "sub-game 2" in out, out      # where we were when it arrived


def test_a_turn_we_accept_prints_nothing(capsys) -> None:
    # Only the invisible case is worth a line; a played series must not narrate
    # every turn into the operator's log.
    rt = _runtime(sub_game=1)
    rt.sm.transition(State.WAITING)
    rt.handle(TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9}).to_dict())
    assert capsys.readouterr().out == ""


def test_reporting_a_malformed_wire_never_crashes_the_peer(capsys) -> None:
    # The malformed branch is precisely where the wire may not be a mapping, so
    # a reporter that assumes .get() turns a rejected message into a crash —
    # handing any peer a one-line denial of service against us.
    rt = _runtime(sub_game=1)
    rt.sm.transition(State.WAITING)
    assert rt.handle("garbage").malformed is True  # type: ignore[arg-type]
    assert "ignored malformed" in capsys.readouterr().out
