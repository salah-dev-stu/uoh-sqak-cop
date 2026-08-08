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

The rules themselves are tested as arithmetic in tests/sdk/test_index_rules.py;
what follows is what a whole series does with them.
"""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.negotiation import Negotiation
from cipherchase.peer.terms import identity_from_config, terms_from_config
from cipherchase.sdk.series import run_series
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _fast(cfg, num_games=2):
    cfg.private["network"] = {**cfg.private["network"], "turn_timeout_seconds": 0.3,
        "poll_interval_seconds": 0.02, "connect_timeout_seconds": 0.2, "index_patience_seconds": 3,
        "retry_interval_seconds": 0.02, "audit_send_timeout_seconds": 0.2,
        "handshake_retries": 3}
    cfg.shared["network_and_league"]["num_games"] = num_games
    return cfg


def _live_peer(a, b, signed):
    """A peer that re-pushes its agreement every window, like a real one.

    Priming the queue once would not do: a fresh series drains whatever was
    queued before it began, so a backlog can never stand in for a live peer.
    """
    original = a.poll_agreement_or_none

    def repushing(timeout):
        b.exchange_agreement_push(signed)
        return original(timeout)

    a.poll_agreement_or_none = repushing


def test_a_zero_turn_timeout_retries_the_same_index() -> None:
    a, b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"))
    # A peer that agrees and then says nothing at all — the s2 shape exactly.
    _live_peer(a, b, Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed())
    series = run_series(cfg, "police", a)
    zero = [s for s in series.summaries if s["result"] == "timeout" and s["steps"] == 0]
    assert len(zero) >= 2, "the silent window must be RETRIED, not spent"
    assert {s["sub_game_number"] for s in zero} == {1}, (
        "a window with no turns never became a game — hold the index, do not spend it")


def test_the_series_converges_on_a_peer_on_another_index() -> None:
    # End to end: a peer that keeps declaring sub-game 3 while we open at 1.
    # Holding alone would deadlock us at 1 forever.
    a, b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games=3)
    _live_peer(a, b, Negotiation(terms_from_config(cfg), identity_from_config(cfg),
                                 sub_game_number=3, role="thief").signed())
    series = run_series(cfg, "police", a)
    played = [s["sub_game_number"] for s in series.summaries]
    assert 3 in played, f"never converged on the peer's index: {played}"


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


def test_a_failed_window_reports_its_reason_as_it_happens(capsys) -> None:
    # A stalled series never ends, so a reason that only appears in the final
    # summary is unreachable exactly when it is needed. anrbj666 and we spent
    # half an hour reasoning about a refusal our own process had already made.
    a, _b = make_pair()  # nobody answers → every window fails
    cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games=1)
    cfg.private["network"]["index_patience_seconds"] = 1
    run_series(cfg, "police", a)
    out = capsys.readouterr().out
    assert "sub-game 1" in out and "handshake_failed" in out, out
    assert "agreement" in out, "the reason must be in the line, not just the verdict"


def test_a_series_drains_stale_agreements_before_it_starts() -> None:
    # A relaunch inherits whatever the peer queued during the run that failed.
    # Nothing in that backlog can be legitimate for a series that has not begun.
    a, b = make_pair()
    cfg = _fast(ConfigManager.load(CONFIG / "police"), num_games=1)
    for n in (3, 4, 5):                       # leftovers from an aborted run
        b.exchange_agreement_push(Negotiation(
            terms_from_config(cfg), identity_from_config(cfg),
            sub_game_number=n, role="thief").signed())
    series = run_series(cfg, "police", a)
    assert {s["sub_game_number"] for s in series.summaries} == {1}, (
        "a stale backlog must not decide which sub-game a fresh series opens on")
