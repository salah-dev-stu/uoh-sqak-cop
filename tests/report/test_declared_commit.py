"""The opponent's revision has to reach the report, not just the audit."""

from __future__ import annotations

from cipherchase.sdk.settled import declared_commit


def test_the_first_sub_game_that_revealed_it_answers_for_the_series() -> None:
    # Sub-game 1's audit never round-tripped (the peer that settles first exits
    # before the other's audit returns — seen in the imreeyal series), so the
    # value is missing from that row and present in the rest.
    assert declared_commit([{"peer_commit": ""}, {"peer_commit": "0a89b476"},
                            {"peer_commit": "0a89b476"}]) == "0a89b476"


def test_an_opponent_who_never_declared_is_recorded_as_unknown() -> None:
    # "unknown" must mean THEIR silence. It meant our dropped value for six
    # sub-games against anrbj666, which is the whole reason this exists.
    assert declared_commit([{"peer_commit": ""}, {}]) == "unknown"
    assert declared_commit([]) == "unknown"
