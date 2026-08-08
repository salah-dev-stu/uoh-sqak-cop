"""Which windows of a live series count as sub-games that were played.

A series records every handshake retry, and a window that never became a game
must contribute no row: the opponent has none for it either, so reporting one
puts a sub-game in our file that is absent from theirs.
"""

from __future__ import annotations

from typing import Any

from cipherchase.sdk.series import settles

Json = dict[str, Any]


def settled_summaries(summaries: list[Json]) -> list[Json]:
    """One row per sub-game — the outcome it settled on, not its retries.

    A live series records every handshake retry, so a window that waited out 25
    attempts contributes 25 summaries. Reported verbatim they become 25 result
    rows, while the opponent's file carries one: the mutual signature is then
    computed over lists that cannot agree, and the single field both teams must
    match is the one guaranteed to differ.

    A window that never became a game contributes NO row — the opponent has no
    row for it either, since from their side it never happened. Reporting it as
    a 0/0 result would put a sub-game in our file that is absent from theirs.
    """
    latest: dict[int, Json] = {}
    for summary in summaries:
        latest[summary["sub_game_number"]] = summary  # last write wins = the settled one
    return [latest[n] for n in sorted(latest) if settles(latest[n])]


def declared_commit(summaries: list[Json]) -> str:
    """The opponent's step-0 revision, taken from whichever sub-game revealed it.

    A peer that crashes before one audit still declares the same hash in the
    others, so the first non-empty answer is the series' answer. "unknown" is
    reserved for an opponent who genuinely never told us — it is a record of
    their silence, not a placeholder for our own dropped value.
    """
    return next((s["peer_commit"] for s in summaries if s.get("peer_commit")), "unknown")
