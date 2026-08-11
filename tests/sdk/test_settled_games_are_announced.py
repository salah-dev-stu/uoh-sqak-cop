"""A sub-game that PLAYS must say so (vibecode, 2026-08-12).

Our series printed a line only when a window FAILED. A played sub-game emitted
nothing at all, so a healthy series and a dead one produced the same output:
silence. Reading that silence as "nothing is happening", we killed a live peer
mid-sub-game-5 — destroying four settled games, with audits already verified by
both sides, that only the opponent could later prove had existed.

The failure-only log was itself the bug. Success needs a voice.
"""

from __future__ import annotations

import threading
from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg, num_games=1):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 15,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 5,
        "index_patience_seconds": 3, "retry_interval_seconds": 0.05,
        "audit_send_timeout_seconds": 2}
    cfg.shared["network_and_league"]["num_games"] = num_games
    cfg.private["scent"] = {**cfg.private.get("scent", {}), "model": "multiplicative_cheb"}
    return cfg


def test_a_played_sub_game_prints_its_result(capsys) -> None:
    police = _fast(ConfigManager.load(CONFIG / "police"))
    thief = _fast(ConfigManager.load(CONFIG / "thief"))
    a, b = make_pair()
    threads = [threading.Thread(target=lambda: run_series(police, "police", a)),
               threading.Thread(target=lambda: run_series(thief, "thief", b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    out = capsys.readouterr().out
    # Every SETTLED window now announces itself with its result, length, winner
    # and audit verdict. Before this, only failures spoke, so a series that was
    # working looked exactly like one that was not.
    settled = [ln for ln in out.splitlines() if "steps)" in ln]
    assert settled, f"a settled sub-game must announce itself:\n{out}"
    assert "winner" in settled[0] and "audit" in settled[0], settled[0]
