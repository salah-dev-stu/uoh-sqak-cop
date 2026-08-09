"""What a filed result says about the files and repositories around it.

Rule 49 makes the result self-navigating: the other three artifact kinds by
sibling filename, and BOTH teams' repositories. Kept apart from scoring because
neither of these reaches the mutual signature — they describe the filing, not
the game.
"""

from __future__ import annotations

from typing import Any

Json = dict[str, Any]


def links_block(*, game_id: str, own: str, opponent: str,
                own_repos: Json, peer_repos: Json) -> Json:
    """Rule 49: the filed result must be navigable from itself alone.

    The other three artifact kinds by sibling FILENAME (``g<NN>`` stands for the
    sub-game, which is per-file), plus BOTH teams' repositories. Ours carried our
    own two repos and no filenames, so a reader holding only the result could
    reach neither the evidence beside it nor the opponent's code.

    The opponent's repos come from the identity THEY signed at the handshake —
    never invented here, exactly like their counted-games count.
    """
    return {
        "config": f"config_{game_id}_g<NN>.json",
        "declaration": f"declaration_{game_id}.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": f"result_{game_id}.json",
        "github": {own: dict(own_repos), opponent: dict(peer_repos)},
    }


def diversity(groups: tuple[str, str], *, winner: str | None,
              first_meeting: bool, counted: bool) -> Json:
    """Who earned the 10-point diversity bonus: the WINNER of a counted first
    meeting, and nobody else. A drawn series has no winner and awards none."""
    earned = bool(counted and first_meeting and winner)
    return {group: earned and group == winner for group in groups}
