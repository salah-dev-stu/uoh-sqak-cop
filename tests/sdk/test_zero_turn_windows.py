"""A window where no turn was ever exchanged never became a game (imreeyal, s2).

Our sub-game 2 completed a handshake and then timed out having received nothing;
their side logged no contact at all for the same window. One peer thought a game
existed, the other did not — and because a timeout is a settlement, we advanced
the index while they retried theirs. That single 180s window opened the drift
that cost sub-games 2-6.

The handshake is two independent one-way pushes, so this asymmetry cannot be
timed out of existence. But it can be made harmless: settlement requires that a
game actually happened, and a window with ZERO turns is indistinguishable from
one where the handshake never landed. So it holds the index and is retried.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg, num_games=2):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 0.3,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 0.2,
        "retry_interval_seconds": 0.02, "audit_send_timeout_seconds": 0.2,
        "handshake_retries": 3}
    cfg.shared["network_and_league"]["num_games"] = num_games
    return cfg


def test_a_zero_turn_timeout_retries_the_same_index() -> None:
    a, b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"))
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.peer.terms import identity_from_config, terms_from_config
    # A peer that agrees and then says nothing at all — the s2 shape exactly.
    for _ in range(6):
        b.exchange_agreement_push(
            Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed())
    series = run_series(cfg, "police", a)
    zero = [s for s in series.summaries if s["result"] == "timeout" and s["steps"] == 0]
    assert len(zero) >= 2, "the silent window must be RETRIED, not spent"
    assert {s["sub_game_number"] for s in zero} == {1}, (
        "a window with no turns never became a game — hold the index, do not spend it")


def test_a_timeout_with_play_in_it_still_settles() -> None:
    # The narrow reading we explicitly do NOT want: a game that produced turns
    # and then went silent HAS a result, and must never be replayed.
    from cipherchase.sdk.series import settles
    assert settles({"result": "timeout", "steps": 7}) is True
    assert settles({"result": "timeout", "steps": 0}) is False
    assert settles({"result": "capture", "steps": 13}) is True
    assert settles({"result": "handshake_failed", "steps": 0}) is False
    assert settles({"result": "tamper_forfeit", "steps": 0}) is True
