"""Byzantine peers, live (F3/F4/F6): every cheat is caught by the runtime itself.

Each test plays a REAL loopback game where one side runs a scripted cheater
transport — a forged audit, a mid-game replay flood, an oversized hint. The
honest side must convict (tamper_forfeit) or shrug it off (idempotence) using
only the shipped machinery: no judge, correctness by construction.
"""

from __future__ import annotations

import copy
import threading
from pathlib import Path

from fakes.fake_transport import FakeTransport, Inboxes

from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 15,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 5, "index_patience_seconds": 3,
        "retry_interval_seconds": 0.05, "audit_send_timeout_seconds": 2}
    cfg.shared["network_and_league"]["num_games"] = 1
    return cfg


class ForgingTransport(FakeTransport):
    """Sends a doctored audit: one nonce nibble flipped in its own records."""

    def _send(self, tool, arg_key, message):
        if tool == "submit_audit" and message.get("records"):
            message = copy.deepcopy(message)
            nonce = message["records"][2]["nonce"]
            message["records"][2]["nonce"] = ("0" if nonce[0] != "0" else "1") + nonce[1:]
        return super()._send(tool, arg_key, message)


class ReplayingTransport(FakeTransport):
    """Every turn wire is sent TWICE — a replay flood."""

    def _send(self, tool, arg_key, message):
        out = super()._send(tool, arg_key, message)
        if tool == "receive_turn":
            super()._send(tool, arg_key, copy.deepcopy(message))
        return out


class ShoutingTransport(FakeTransport):
    """Hints inflated to 600 words — an oversized-payload probe."""

    def _send(self, tool, arg_key, message):
        if tool == "receive_turn" and message.get("hint"):
            message = {**message, "hint": " ".join(["blah"] * 600)}
        return super()._send(tool, arg_key, message)


def _play(cheater_cls):
    police_box, thief_box = Inboxes(100), Inboxes(100)
    honest = FakeTransport(police_box, thief_box)          # police stays honest
    cheat = cheater_cls(thief_box, police_box)             # the thief cheats
    out = {}
    threads = [
        threading.Thread(target=lambda: out.setdefault(
            "police", run_series(_fast(ConfigManager.load(CONFIG / "police")), "police", honest))),
        threading.Thread(target=lambda: out.setdefault(
            "thief", run_series(_fast(ConfigManager.load(CONFIG / "thief")), "thief", cheat))),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
        assert not thread.is_alive(), "byzantine game deadlocked"
    return out["police"].summaries[0], out["thief"].summaries[0]


def test_a_forged_audit_forfeits_the_forger() -> None:
    honest, _cheater = _play(ForgingTransport)
    assert honest["result"] == "tamper_forfeit"     # the honest side convicts…
    assert honest["winner"] == "police"             # …and the forger loses (0/0 rule)
    assert honest["audit"]["passed"] is False
    assert honest["audit"]["failed_steps"] == [2]   # localised to the doctored record


def test_a_replay_flood_changes_nothing() -> None:
    honest, cheater = _play(ReplayingTransport)
    assert honest["result"] in ("capture", "survival")
    assert honest["result"] == cheater["result"]    # both agree despite the flood
    assert honest["audit"]["passed"] is True        # idempotent handling, audit clean


def test_an_oversized_hint_neither_crashes_nor_stalls() -> None:
    honest, cheater = _play(ShoutingTransport)
    assert honest["result"] in ("capture", "survival")
    assert honest["audit"]["passed"] is True and cheater["audit"]["passed"] is True
