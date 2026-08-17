"""The opponent's revision has to reach the report, not just the audit."""

from __future__ import annotations

from cipherchase.sdk.settled import declared_commit, declared_commits


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


def test_the_sealed_record_wins_over_the_plaintext_identity() -> None:
    # anrbj666 run a two-channel declaration: the commit is sealed in the
    # step-0 record AND repeated in the negotiate identity block. The sealed
    # copy is inside the records our audit re-hashes, so it is the one that is
    # tamper-evident; the identity block is plaintext on the wire. Prefer the
    # seal, always.
    summaries = [{"peer_commit": "9347868b", "peer_identity": {"github_commit": "9347868b"}}]
    assert declared_commit(summaries) == "9347868b"


def test_the_identity_block_fills_in_when_no_seal_carried_it() -> None:
    # A peer whose step-0 we cannot read still declares it in plaintext. Filing
    # that beats filing "unknown" — it is their own statement either way, and
    # "unknown" should mean silence, not an unread channel.
    assert declared_commit([{"peer_commit": "", "peer_identity": {"github_commit": "2db31179"}}]) == "2db31179"
    assert declared_commit([{"peer_commit": ""}]) == "unknown"


def test_two_channels_disagreeing_is_evidence_not_a_coin_toss(capsys) -> None:
    # If a peer's sealed commit and its plaintext declaration differ, that is a
    # fact about them worth surfacing — the code they sealed is not the code
    # they announced. We file the SEALED one, because it is the tamper-evident
    # channel, and we say so out loud rather than silently picking a side.
    out = declared_commit([{"peer_commit": "9347868b",
                            "peer_identity": {"github_commit": "deadbeef"}}])
    assert out == "9347868b"
    printed = capsys.readouterr().out
    assert "9347868b" in printed and "deadbeef" in printed, printed


def test_a_role_split_opponent_gets_a_commit_per_sub_game() -> None:
    # anrbj666 run cop and thief from separate repos, so the revision that
    # played sub-game 1 is genuinely not the one that played sub-game 2. We
    # collapsed the series to a single hash — right for a one-tree opponent like
    # us, and a FALSE STATEMENT about theirs: we filed their thief commit
    # against their police windows. Worse than "unknown", because it names code
    # that did not play that sub-game and the column exists to be checked.
    from cipherchase.sdk.settled import declared_commits
    summaries = [
        {"sub_game_number": 1, "peer_commit": "9347868b"},
        {"sub_game_number": 2, "peer_commit": "2db31179"},
        {"sub_game_number": 3, "peer_commit": "9347868b"},
    ]
    assert declared_commits(summaries) == {1: "9347868b", 2: "2db31179", 3: "9347868b"}


def test_a_row_with_no_seal_falls_back_to_the_declaration_then_to_unknown() -> None:
    from cipherchase.sdk.settled import declared_commits
    # sub-game 2's audit never round-tripped (the last-window shape) — the
    # plaintext identity still speaks for it rather than leaving a hole.
    out = declared_commits([
        {"sub_game_number": 1, "peer_commit": "9347868b",
         "peer_identity": {"github_commit": "9347868b"}},
        {"sub_game_number": 2, "peer_commit": ""},
    ])
    assert out == {1: "9347868b", 2: "9347868b"}
    assert declared_commits([{"sub_game_number": 1, "peer_commit": ""}]) == {1: "unknown"}
