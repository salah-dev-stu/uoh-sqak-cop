"""Their step-0 seal names the code that played — keep it (anrbj666, instance 5).

We receive the opponent's revealed records at the audit, re-hash every one of
them, and then drop the payload. So our result file recorded
``{"anrbj666": "unknown"}`` in all six sub-games while their commits
(0a89b476 / 94ec6ca7) had been on the wire the whole time and had been VERIFIED
by us. A result nobody can pin to a revision is readable, not checkable.

Same defect class as our own stale counted-games count: a value carried
correctly right up to the place that publishes it, then released.
"""

from __future__ import annotations

from cipherchase.peer.summary import peer_commit

SPEC = {"step": 0, "type": "system_spec", "github_commit": "0a89b476", "group_name": "anrbj666"}


def test_the_opponents_commit_is_read_from_their_step_zero_seal() -> None:
    payload = {"sender": "thief", "records": [
        {"payload": {"step": 1, "move": "N"}, "nonce": "a", "commit": "c1"},
        {"payload": SPEC, "nonce": "b", "commit": "c0"},
    ]}
    assert peer_commit(payload) == "0a89b476"


def test_a_peer_that_declares_no_commit_is_not_invented_for() -> None:
    # An opponent whose step-0 omits the field, or sends it empty, gets an empty
    # string — never a guess, and never our own hash by accident.
    assert peer_commit({"records": [{"payload": {"step": 0, "type": "system_spec"}}]}) == ""
    assert peer_commit({"records": [{"payload": dict(SPEC, github_commit="")}]}) == ""
    assert peer_commit({"records": []}) == ""
    assert peer_commit({}) == ""
    assert peer_commit(None) == ""


def test_the_result_file_names_their_revision_not_unknown() -> None:
    # The whole point: the value must survive into the FILE. It was verified at
    # the audit and correct in memory in the shipped run too — and still landed
    # as "unknown" six times, because nothing carried it the last step.
    from cipherchase.report.league import subgame_rows
    summaries = [{"sub_game_number": 1, "role": "police", "result": "survival",
                  "winner": "thief", "steps": 34, "peer_commit": "0a89b476"}]
    rows = subgame_rows(summaries, "uoh-sqak", "anrbj666",
                        {"capture_cop": 20, "capture_thief": 5, "survival_cop": 5,
                         "survival_thief": 10, "tie_score": 2, "technical_loss": 0},
                        game_id="g", commits={"uoh-sqak": "d0bb80f7", "anrbj666": "0a89b476"})
    assert rows[0]["github_commit"] == {"uoh-sqak": "d0bb80f7", "anrbj666": "0a89b476"}


def test_a_step_zero_record_is_read_too() -> None:
    # anrbj666 seal theirs as {"type": "step_zero", "github_commit": ...} — the
    # book-attached log shape (rule 53, p.40) — while we seal "system_spec" and
    # read only that. So their commit was on the wire, verified by our audit,
    # and filed by us as "unknown" for six sub-games. Their reader already
    # accepts both spellings; ours now does too, because a type name is exactly
    # the thing two teams shipping independently cannot keep current.
    for kind in ("system_spec", "step_zero"):
        payload = {"records": [{"payload": {"step": 0, "type": kind,
                                            "github_commit": "9347868b"}}]}
        assert peer_commit(payload) == "9347868b", kind


def test_an_unknown_record_type_is_still_not_mined_for_a_commit() -> None:
    # The set stays closed. A record we do not recognise cannot contribute a
    # hash we would then file as if the opponent had declared it.
    assert peer_commit({"records": [{"payload": {"type": "control",
                                                 "github_commit": "deadbeef"}}]}) == ""
