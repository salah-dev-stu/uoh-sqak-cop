"""Rule 49 links block, and who actually earns the diversity reward.

Both found by diffing our filed friendly against anrbj666's worked example of a
filed counted series. The links delta is theirs; the diversity delta is ours,
and it only diverges in the case the reward exists for — a counted first
meeting — so a friendly could never have surfaced it.
"""

from __future__ import annotations

from cipherchase.report.links import diversity, links_block

OURS = {"cop": "https://github.com/salah-dev-stu/uoh-sqak-cop",
        "thief": "https://github.com/salah-dev-stu/uoh-sqak-thief"}
THEIRS = {"cop": "https://github.com/alonengel/P2P-Police",
          "thief": "https://github.com/alonengel/P2P-Thief"}


def test_the_links_block_names_the_siblings_and_both_teams_repos() -> None:
    # Ours carried {"cop": ..., "thief": ...} — our own two repos and nothing
    # else. A filed result is meant to be navigable by someone holding only it:
    # the other three artifact kinds by name, and BOTH teams' code.
    block = links_block(game_id="anrbj666-vs-uoh-sqak", own="uoh-sqak",
                        opponent="anrbj666", own_repos=OURS, peer_repos=THEIRS)
    assert block == {
        "config": "config_anrbj666-vs-uoh-sqak_g<NN>.json",
        "declaration": "declaration_anrbj666-vs-uoh-sqak.json",
        "log": "log_anrbj666-vs-uoh-sqak_g<NN>.json",
        "result": "result_anrbj666-vs-uoh-sqak.json",
        "github": {"uoh-sqak": OURS, "anrbj666": THEIRS},
    }


def test_an_opponent_who_declared_no_repos_gets_an_empty_entry_not_a_guess() -> None:
    block = links_block(game_id="g", own="us", opponent="them",
                        own_repos=OURS, peer_repos={})
    assert block["github"] == {"us": OURS, "them": {}}


def test_only_the_winner_earns_the_diversity_reward() -> None:
    # OURS was dict.fromkeys((own, opponent), first_meeting and counted) — the
    # same boolean for both teams. The reward is 10 points for WINNING against a
    # new opponent, so the side that lost the series never earned it. A friendly
    # is counted=False, both False, and the bug is invisible; the first counted
    # first-meeting would have put a false True in the loser's column.
    assert diversity(("us", "them"), winner="us", first_meeting=True,
                     counted=True) == {"us": True, "them": False}
    assert diversity(("us", "them"), winner="them", first_meeting=True,
                     counted=True) == {"us": False, "them": True}


def test_no_reward_without_a_counted_first_meeting_or_a_winner() -> None:
    both_false = {"us": False, "them": False}
    assert diversity(("us", "them"), winner="us", first_meeting=True,
                     counted=False) == both_false, "friendlies award nothing"
    assert diversity(("us", "them"), winner="us", first_meeting=False,
                     counted=True) == both_false, "a rematch is not a new opponent"
    assert diversity(("us", "them"), winner=None, first_meeting=True,
                     counted=True) == both_false, "a drawn series has no winner"
