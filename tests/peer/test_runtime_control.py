"""Control channel in the live runtime: enable/status/restart/quit + sealed history."""

from __future__ import annotations

import threading
from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import ControlMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg, num_games=1):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 15,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 5,
        "retry_interval_seconds": 0.05, "audit_send_timeout_seconds": 2}
    cfg.shared["network_and_league"]["num_games"] = num_games
    return cfg


def _loopback(num_games=1, prime=None):
    police_cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games)
    thief_cfg = _fast(ConfigManager.load(CONFIG / "thief"), num_games)
    a, b = make_pair()
    if prime:
        prime(a, b)
    out = {}
    threads = [
        threading.Thread(target=lambda: out.setdefault("p", run_series(police_cfg, "police", a))),
        threading.Thread(target=lambda: out.setdefault("t", run_series(thief_cfg, "thief", b))),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
        assert not thread.is_alive()
    return out["p"], out["t"]


def test_both_peers_enable_exchange_status_and_audits_still_verify() -> None:
    police, thief = _loopback()
    for side in (police, thief):
        summary = side.summaries[0]
        assert summary["audit"]["passed"] is True  # control records don't break the audit
        control = [r for r in summary["records"] if r["payload"].get("type") == "control"]
        kinds = {r["payload"]["kind"] for r in control}
        assert "enable" in kinds and "status" in kinds  # the channel really ran, sealed


def test_opponent_restart_replays_the_series_from_sub_game_one() -> None:
    fired = {"done": False}
    real_take = PeerRuntime.take_turn

    def take_and_restart(self, claim_response):
        # after our first move of sub-game 1, the POLICE side asks for a restart
        if self.role == "police" and self.step_number >= 1 and not fired["done"]:
            fired["done"] = True
            self.control.send_restart()
        return real_take(self, claim_response)

    PeerRuntime.take_turn = take_and_restart
    try:
        police, thief = _loopback(num_games=1)
    finally:
        PeerRuntime.take_turn = real_take
    # the thief honoured the auto-approved restart, then both replayed to a result
    assert police.summaries[-1]["result"] in ("capture", "survival")
    assert thief.summaries[-1]["result"] in ("capture", "survival")
    assert any(s["result"] == "restart" for s in thief.summaries)  # the restart is on record


def test_bare_quit_control_still_ends_the_game() -> None:
    a, _b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"))
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.peer.terms import identity_from_config, terms_from_config
    _b.exchange_agreement_push(
        Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed())
    _b.send_control(ControlMessage(kind="quit", sender="thief", status="QUIT").to_dict())
    out = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1).run()
    assert (out["result"], out["winner"]) == ("opponent_quit", "police")


def test_fresh_game_rejects_a_stale_echo_before_step_one() -> None:
    # Strict alternation → the FIRST inbound step of any (re)started game is 1.
    # A late echo from an aborted game (a series restart) must be ignored WITHOUT
    # poisoning last_seen_step, or the real turns become "duplicates" (deadlock).
    from cipherchase.domain.protocol import TurnMessage as Turn
    from cipherchase.peer.state_machine import State
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=_fast(ConfigManager.load(CONFIG / "police")),
                     transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    stale = rt.handle(Turn(step=3, sender="thief", smell_grid={"1,1": 0.4}).to_dict())
    assert stale.duplicate is True and rt.last_seen_step == 0
    fresh = rt.handle(Turn(step=1, sender="thief", smell_grid={"3,3": 0.9}).to_dict())
    assert fresh.duplicate is False and rt.last_seen_step == 1
