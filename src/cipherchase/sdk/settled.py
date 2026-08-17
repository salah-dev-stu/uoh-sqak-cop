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
    """The opponent's revision, preferring the SEALED channel over plaintext.

    A peer may say it twice — sealed in the step-0 record (inside the records
    our audit re-hashes, therefore tamper-evident) and again in the negotiate
    identity block (plaintext on the wire). anrbj666 run both; reading only one
    channel is how we filed "unknown" for a whole series.

    The seal wins. The identity block fills in when no seal carried it, because
    "unknown" should mean the peer was silent, not that we read the wrong
    channel. And when both spoke and DISAGREE, that is a fact about them — the
    code they sealed is not the code they announced — so we file the sealed one
    and say so rather than silently picking a side.

    A peer that crashes before one audit still declares the same hash in the
    others, so the first non-empty answer is the series' answer.
    """
    sealed = next((s["peer_commit"] for s in summaries if s.get("peer_commit")), "")
    spoken = str(peer_declaration(summaries).get("github_commit", "") or "")
    if sealed and spoken and sealed != spoken:
        print(f"  peer commit CHANNELS DISAGREE — sealed {sealed}, declared {spoken}; "
              f"filing the sealed one (the audit-verified channel)")
    return sealed or spoken or "unknown"


def peer_declaration(summaries: list[Json]) -> Json:
    """The identity block the opponent signed at the handshake.

    Everything we file ABOUT them comes from here — their counted-games count,
    their repositories — so that our report never invents a fact on their
    behalf. An opponent who declared nothing yields an empty mapping.
    """
    return next((s["peer_identity"] for s in summaries if s.get("peer_identity")), {})


def own_counted_total(*, declared: int, counted: bool) -> int:
    """OUR counted-series total including this one — from what we DECLARE.

    Symmetric with how we compute the opponent's: their declaration plus this
    game if it counts. We were instead using a per-directory ledger count of
    games against THIS opponent, which is a different quantity and reads 0 in
    any fresh output directory — so our filed result understated us while the
    opponent's file, reading the number we signed at the handshake, had it right.
    """
    return declared + (1 if counted else 0)
