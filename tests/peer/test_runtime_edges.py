"""P1 robustness edges (§4): every failure is a result, never a crash/hang."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from fakes.fake_transport import make_pair

from cipherchase.constants import Direction
from cipherchase.domain.brains import Decision
from cipherchase.domain.negotiation import Negotiation
from cipherchase.domain.protocol import TurnMessage
from cipherchase.exceptions import ConfigError, IllegalMoveError
from cipherchase.peer import summary
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.sealing import SealBook
from cipherchase.peer.state_machine import State
from cipherchase.peer.terms import identity_from_config, terms_from_config, validate_terms
from cipherchase.sdk.sdk import SimulationSdk
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _cfg(role: str = "police") -> ConfigManager:
    cfg = ConfigManager.load(CONFIG / role)
    cfg.private["network"] = {
        **cfg.private["network"], "turn_timeout_seconds": 5,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 0.2,
        "retry_interval_seconds": 0.02, "audit_send_timeout_seconds": 1,
    }
    return cfg


def _push_agreement(via, cfg: ConfigManager) -> None:
    via.exchange_agreement_push(
        Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed()
    )


def test_handshake_timeout_yields_handshake_failed_summary() -> None:
    a, _b = make_pair()  # nobody ever answers
    out = PeerRuntime(role="police", cfg=_cfg(), transport=a, sub_game_number=1).run()
    assert out["result"] == "handshake_failed"
    assert out["audit"]["status"] == "skipped"


def test_quit_control_ends_the_game_without_hanging() -> None:
    a, b = make_pair()
    cfg = _cfg()
    _push_agreement(b, cfg)
    b.send_control({"kind": "quit", "sender": "thief"})
    out = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1).run()
    assert out["result"] == "opponent_quit" and out["winner"] == "police"


def test_illegal_brain_move_falls_back_to_hold() -> None:
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=_cfg(), transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    with patch.object(rt.board, "step", side_effect=IllegalMoveError("boom")):
        assert rt.take_turn(None) is None
    assert rt.book.records()[-1]["payload"]["move"] == Direction.STAY.value  # HOLD sealed


def test_malformed_wire_is_rejected_not_crashed() -> None:
    rt = PeerRuntime(role="police", cfg=_cfg(), transport=make_pair()[0], sub_game_number=1)
    assert rt.handle("garbage").malformed is True  # type: ignore[arg-type]
    assert rt.handle({"step": "NaN-ish", "sender": 3}).malformed is True


def test_loop_skips_garbage_then_processes_the_real_message() -> None:
    a, _b = make_pair()
    cfg = _cfg()
    a.inboxes.put_agreement(
        Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed()
    )  # agreement waiting in MY OWN inbox
    a.inboxes.put_turn({"totally": "garbage"})  # malformed → skipped, loop continues
    a.inboxes.put_turn(TurnMessage(step=1, sender="thief", win_claim={"type": "survival"}).to_dict())
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    out = rt.run()
    assert out["result"] == "survival" and out["winner"] == "thief"
    assert any(h.get("malformed") for h in rt.history)


def test_audit_push_failure_is_suppressed_and_tamper_forfeits() -> None:
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=_cfg(), transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    book = SealBook()
    book.seal({"step": 1, "state": {"pos": [3, 3], "barriers": []}, "move": "N", "intent": "truth"})
    records = book.records()
    records[0]["payload"]["move"] = "S"  # forged after commit
    a.inboxes.put_audit({"sender": "thief", "records": records, "result_claim": "survival"})
    with patch.object(rt.transport, "send_audit", side_effect=ConnectionError("gone")):
        out = summary.finish(rt, ("survival", "thief"))
    assert out["result"] == "tamper_forfeit" and out["winner"] == "police"


def test_validate_terms_fails_fast_on_missing_source() -> None:
    cfg = _cfg()
    del cfg.shared["world"]
    with pytest.raises(ConfigError):
        validate_terms(cfg)


def test_run_peer_with_injected_transport_plays_a_series() -> None:
    police_cfg, thief_cfg = _cfg("police"), _cfg("thief")
    for cfg in (police_cfg, thief_cfg):
        cfg.private["network"]["connect_timeout_seconds"] = 5
    a, b = make_pair()
    out: dict = {}
    threads = [
        threading.Thread(target=lambda: out.update(
            p=SimulationSdk.run_peer(police_cfg, natural_role="police", transport=a))),
        threading.Thread(target=lambda: out.update(
            t=SimulationSdk.run_peer(thief_cfg, natural_role="thief", transport=b))),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
        assert not t.is_alive()
    assert out["p"]["game_uid"] == out["t"]["game_uid"]
    assert out["p"]["sub_games"][0]["result"] in ("capture", "survival")


def test_best_effort_control_send_and_drain() -> None:
    a, b = make_pair()
    with patch.object(a, "_send", side_effect=ConnectionError("down")):
        assert a.send_control({"kind": "status"}) is None  # advisory — never raises
    b.send_turn({"step": 1, "sender": "x"})
    b.drain_inboxes()
    assert b.inboxes.try_get_turn(0.01) is None


def test_far_barrier_suggestion_is_refused() -> None:
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=_cfg(), transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    with patch.object(rt.brain, "decide",
                      return_value=Decision(direction=Direction.STAY, barrier_cell=(6, 6))):
        rt.take_turn(None)
    assert a.sent[-1][2]["barrier_placed"] is None  # non-adjacent → not placed
