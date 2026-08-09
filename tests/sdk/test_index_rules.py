"""The three pure rules that decide which sub-game index a peer plays next.

Settlement (did a game happen?), catch-up (whose index wins?), and patience
(how long is a window worth?) are plain functions with no transport, so they are
tested as arithmetic. Their series-level consequences live in
tests/sdk/test_zero_turn_windows.py; every case below is a live-match scar.
"""

from __future__ import annotations

from cipherchase.sdk.series import catch_up, keep_waiting, settles


def test_a_timeout_with_play_in_it_still_settles() -> None:
    # The narrow reading we explicitly do NOT want: a game that produced turns
    # and then went silent HAS a result, and must never be replayed. A window
    # with ZERO turns is indistinguishable from one where the handshake never
    # landed, so it holds the index instead of spending it (imreeyal, s2).
    assert settles({"result": "timeout", "steps": 7}) is True
    assert settles({"result": "timeout", "steps": 0}) is False
    assert settles({"result": "capture", "steps": 13}) is True
    assert settles({"result": "handshake_failed", "steps": 0}) is False
    assert settles({"result": "tamper_forfeit", "steps": 0}) is True


def test_a_peer_on_another_index_pulls_us_to_it() -> None:
    # imreeyal's point 2: if BOTH peers only hold, an asymmetric failure
    # deadlocks them on different indices instead of drifting — nobody moves.
    # The refusal carries the only evidence of who is out of step.
    assert catch_up(n=2, peer=5, settled=set()) == 5, "converge on their index"
    assert catch_up(n=3, peer=3, settled=set()) == 3
    assert catch_up(n=3, peer=0, settled=set()) == 3, "no declaration → nothing to learn"


def test_catch_up_may_return_to_an_index_we_never_settled() -> None:
    # Live against anrbj666: stale agreements from their aborted runs declared
    # sub-games 3 and 4 while they were really on 2. Catch-up trusted the highest
    # index as evidence they were ahead and chased us to 6, past the game. We
    # then drained their valid sub-game-2 pushes forever.
    #
    # "Forward only" was a proxy for the real rule, which is: never revisit an
    # index we have SETTLED. Moving back to one we never played replays nothing.
    assert catch_up(n=2, peer=5, settled=set()) == 5        # behind → converge
    assert catch_up(n=6, peer=2, settled={1}) == 2          # stale jump → come back
    assert catch_up(n=6, peer=2, settled={1, 2}) == 6       # 2 is played → never again
    assert catch_up(n=3, peer=0, settled={1}) == 3          # no signal → hold


def test_patience_at_one_index_is_measured_in_time_not_attempts() -> None:
    # imreeyal's offset: a zero-turn timeout costs the peer that suffers it a full
    # turn budget (180s), so the other side must be able to outwait one of those.
    # Our budget was 20 ATTEMPTS — and a refused agreement fails a window in
    # milliseconds, so 21 attempts burned in seconds. We gave up 5 seconds before
    # they arrived. Attempts are not a unit of patience; seconds are.
    p = {"patience": 240.0, "max_attempts": 500}
    assert keep_waiting(elapsed=0.4, attempts=21, **p), "21 instant refusals is not patience"
    assert keep_waiting(elapsed=200.0, attempts=400, **p), "still inside one turn budget"
    assert not keep_waiting(elapsed=241.0, attempts=3, **p), "time is what runs out"
    assert not keep_waiting(elapsed=1.0, attempts=501, **p), "but a hot loop is still capped"


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


def test_no_turns_means_no_game_whatever_the_label_says() -> None:
    # Tonight, twice, against ahk-yosi. The rule "a window with no turns never
    # became a game" was written as a test for result == "timeout", so every
    # OTHER zero-turn outcome settled and spent the index. Their peer died
    # before play; we recorded a zero-turn opponent_quit, scored it, advanced —
    # and then correctly refused to replay the index they were still sitting on.
    # Four dead sub-games from a predicate that was narrower than its own docstring.
    for label in ("timeout", "opponent_quit", "quit", "error", "stopped"):
        assert settles({"result": label, "steps": 0}) is False, label
        assert settles({"result": label, "steps": 4}) is True, label


def test_a_real_result_settles_even_at_step_zero() -> None:
    # A terminal verdict is a game whatever the step count: an audit forfeit can
    # land before either side moves, and it must never be replayed.
    assert settles({"result": "tamper_forfeit", "steps": 0}) is True
    assert settles({"result": "capture", "steps": 0}) is True
    assert settles({"result": "survival", "steps": 0}) is True
    assert settles({"result": "handshake_failed", "steps": 9}) is False
