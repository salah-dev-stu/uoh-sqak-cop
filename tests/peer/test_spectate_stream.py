"""Spectate wiring (SH-1/3/19): cadence, no-truth-leak, crash isolation."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
_ALLOWED = {"spectate_schema", "turn", "role", "phase", "me", "belief", "known_barriers",
            "last_hint", "last_intent", "claims", "commit8", "sub_game", "outcome", "ts"}


def _rt(role, transport, listener=None):
    rt = PeerRuntime(role=role, cfg=ConfigManager.load(CONFIG / role),
                     transport=transport, sub_game_number=1, listener=listener)
    rt.sm.transition(State.WAITING)
    return rt


def test_one_frame_per_send_and_per_processed_receive_only() -> None:
    frames: list = []
    a, _b = make_pair()
    rt = _rt("police", a, frames.append)
    rt.take_turn(None)
    assert [f["phase"] for f in frames] == ["sent"]
    rt.handle(TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9}).to_dict())
    assert frames[-1]["phase"] == "received"
    n = len(frames)
    rt.handle(TurnMessage(step=1, sender="thief").to_dict())  # duplicate step → nothing
    rt.handle({"garbage": True})                              # malformed → nothing
    assert len(frames) == n


def test_a_raising_listener_never_breaks_the_match() -> None:
    def boom(_frame):
        raise RuntimeError("spectator blew up")
    a, _b = make_pair()
    out = _rt("police", a, boom).run()          # no opponent → handshake_failed
    assert out["result"]                        # a summarised result, not a crash


def _fast(cfg):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 15,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 5, "index_patience_seconds": 3,
        "retry_interval_seconds": 0.05, "audit_send_timeout_seconds": 2}
    cfg.shared["network_and_league"]["num_games"] = 1
    return cfg


def test_full_loopback_stream_leaks_no_opponent_ground_truth() -> None:
    cop_f, thief_f = [], []
    a, b = make_pair()
    sides = [("police", cop_f, a), ("thief", thief_f, b)]
    threads = [threading.Thread(target=lambda r, lst, t: run_series(
        _fast(ConfigManager.load(CONFIG / r)), r, t, listener=lst.append), args=s)
        for s in sides]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
        assert not t.is_alive()
    assert cop_f and thief_f
    for f in cop_f + thief_f:
        assert set(f) <= _ALLOWED                       # no stray opponent/nonce fields
        blob = json.dumps(f)
        assert "nonce" not in blob and "thief_belief" not in blob
        assert '"move"' not in blob                     # sealed payload never streamed
