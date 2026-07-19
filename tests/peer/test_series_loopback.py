"""Milestone core: a full live series over FakeTransport — F1/F2/F9 in motion."""

from __future__ import annotations

import threading
from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.sdk.series import SeriesResult, role_for, run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg: ConfigManager, num_games: int) -> ConfigManager:
    cfg.private["network"] = {
        **cfg.private["network"], "turn_timeout_seconds": 15,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 5,
        "retry_interval_seconds": 0.05, "audit_send_timeout_seconds": 2,
    }
    cfg.shared["network_and_league"]["num_games"] = num_games
    return cfg


def _play(num_games: int) -> tuple[SeriesResult, SeriesResult]:
    police_cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games)
    thief_cfg = _fast(ConfigManager.load(CONFIG / "thief"), num_games)
    a, b = make_pair()
    out: dict[str, SeriesResult] = {}

    def side(name: str, cfg: ConfigManager, natural: str, transport) -> None:
        out[name] = run_series(cfg, natural, transport)

    threads = [
        threading.Thread(target=side, args=("police", police_cfg, "police", a)),
        threading.Thread(target=side, args=("thief", thief_cfg, "thief", b)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
        assert not t.is_alive(), "series deadlocked"
    return out["police"], out["thief"]


def test_role_alternation_rule() -> None:
    assert role_for("police", 1) == "police"
    assert role_for("police", 2) == "thief"
    assert role_for("thief", 2) == "police"


def test_full_two_sub_game_series_loopback() -> None:
    police_side, thief_side = _play(2)
    assert len(police_side.summaries) == len(thief_side.summaries) == 2
    # byte-identical agreement lock: both sides derived the same ids
    assert police_side.game_uid == thief_side.game_uid
    assert police_side.game_id == thief_side.game_id
    for a_sum, b_sum in zip(police_side.summaries, thief_side.summaries, strict=True):
        assert {a_sum["role"], b_sum["role"]} == {"police", "thief"}  # roles swap in sync
        assert a_sum["result"] == b_sum["result"]  # agreed outcome
        assert a_sum["result"] in ("capture", "survival")
        assert a_sum["audit"]["passed"] is True and b_sum["audit"]["passed"] is True
    # role swap across sub-games
    assert police_side.summaries[0]["role"] != police_side.summaries[1]["role"]
    assert 0 <= police_side.wins_for("police") <= 2


def test_timeout_is_a_technical_win_and_skips_audit() -> None:
    cfg = _fast(ConfigManager.load(CONFIG / "police"), 1)
    cfg.private["network"]["turn_timeout_seconds"] = 0.2
    cfg.private["network"]["connect_timeout_seconds"] = 1
    a, b = make_pair()
    from cipherchase.peer.runtime import PeerRuntime

    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    # opponent pushes its agreement but then goes silent forever
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.peer.terms import identity_from_config, terms_from_config

    b.exchange_agreement_push(Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed())
    result = rt.run()
    assert (result["result"], result["winner"]) == ("timeout", "police")
    assert result["audit"]["status"] == "skipped"
