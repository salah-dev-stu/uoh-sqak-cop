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


def test_a_peer_strictly_ahead_pulls_us_forward_never_backward() -> None:
    # imreeyal's point 2: if BOTH peers only hold, an asymmetric failure deadlocks
    # them on different indices instead of drifting — nobody moves. The refusal
    # itself carries the only evidence of who is out of step, so a peer that is
    # behind catches up. Forward only, or two peers ping-pong forever.
    from cipherchase.sdk.series import catch_up
    assert catch_up(n=2, peer=5) == 5, "behind → adopt their index"
    assert catch_up(n=5, peer=2) == 5, "ahead → never rewind"
    assert catch_up(n=3, peer=3) == 3
    assert catch_up(n=3, peer=0) == 3, "no declaration → nothing to learn"


def test_the_refusal_reports_which_index_the_peer_declared() -> None:
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.exceptions import HandshakeError
    terms, ident = {"board_size": 7}, {"group_id": "them"}
    ours = Negotiation(terms, ident, sub_game_number=2, role="police")
    theirs = Negotiation(terms, ident, sub_game_number=5, role="thief").signed()
    try:
        ours.verify_peer(theirs)
    except HandshakeError as exc:
        assert exc.peer_sub_game == 5, "the refusal must say where THEY are"
    else:
        raise AssertionError("a sub-game disagreement must refuse")


def test_the_series_converges_on_a_peer_that_is_ahead() -> None:
    # End to end: a peer stuck declaring sub-game 3 while we open at 1. Holding
    # alone would deadlock us at 1 forever; we adopt their index and play on.
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.peer.terms import identity_from_config, terms_from_config
    a, b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games=3)
    for _ in range(8):
        b.exchange_agreement_push(Negotiation(
            terms_from_config(cfg), identity_from_config(cfg),
            sub_game_number=3, role="thief").signed())
    series = run_series(cfg, "police", a)
    played = [s["sub_game_number"] for s in series.summaries]
    assert 3 in played, f"never caught up to the peer's index: {played}"
    assert max(played) == 3 and min(played) == 1, "forward only, no rewind"


def test_a_failed_window_reports_why_not_just_that_it_failed() -> None:
    # 26 refused handshakes told us nothing tonight: "handshake_failed" 26 times,
    # with the reason captured per-summary and then dropped from everything we
    # print or persist. "No agreement arrived" and "terms mismatch" are entirely
    # different bugs, and the opponent cannot see our side either way.
    from cipherchase.sdk.sdk import SimulationSdk
    a, _b = make_pair()  # nobody ever answers
    cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games=1)
    out = SimulationSdk.run_peer(cfg, natural_role="police", transport=a)
    failed = [s for s in out["sub_games"] if s["result"] == "handshake_failed"]
    assert failed, "the window failed"
    assert failed[0]["note"], "and the reason must survive into what we print"
    assert "agreement" in failed[0]["note"].lower()
