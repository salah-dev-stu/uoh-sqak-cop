"""Per-sub-game negotiation handshake (PRD_league_runtime §2.1, F5/F14).

Push our signed ``{terms, nonce, signature, identity}`` (transport retries
until the peer is up), read the peer's from our agreements inbox, verify terms
equality + signature, capture identity, derive the shared game ids.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.game_ids import derive_game_ids
from cipherchase.domain.model_registry import declared_hash
from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError
from cipherchase.peer.terms import identity_from_config, terms_from_config


def _who(message: dict[str, Any]) -> str:
    """Name the sender of an agreement — group, declared role, declared index."""
    ident = message.get("identity") or {}
    return (f"{ident.get('group_id', '?')} (role {message.get('role', '?')}, "
            f"sub-game {message.get('sub_game_number', '?')})")


def _attributed(message: dict[str, Any]) -> dict[str, Any]:
    """Tag the message so any refusal downstream can say WHO it refused."""
    return {**message, "_who": _who(message)}


def _await_opponent(rt: Any) -> dict[str, Any]:
    """Read agreements until the EXPECTED opponent answers, or the budget ends.

    Our endpoint is public and unauthenticated, so anyone still holding the URL
    can push an agreement — a peer we once practised against, with a stale config,
    is enough. Consuming a stranger's agreement costs a whole window and teaches
    us nothing, so we discard it and keep listening inside the same budget. That
    turns third-party traffic into noise instead of a denial of service.
    """
    expected = str(rt.cfg.private["game"].get("opponent_group_id", "") or "")
    deadline = rt.now() + float(rt.cfg.network["connect_timeout_seconds"])
    strangers: list[str] = []
    drained: list[str] = []
    ahead = 0
    while (remaining := deadline - rt.now()) > 0:
        message = rt.transport.poll_agreement_or_none(min(remaining, 0.5))
        if message is None:
            continue
        sender = str((message.get("identity") or {}).get("group_id", ""))
        if expected and sender and sender != expected:
            strangers.append(_who(message))  # not ours — discard, keep the window
            continue
        theirs = message.get("sub_game_number")
        if theirs is not None and theirs != rt.sub_game_number:
            # Their OTHER window, re-pushing. Consuming one of these per window
            # drains slower than a peer pushes, so a bounded inbox fills and then
            # refuses everyone — the correct counterpart included. Drain at poll
            # speed instead, but keep the highest index so catch-up still fires.
            ahead = max(ahead, int(theirs))
            drained.append(_who(message))
            continue
        return message
    seen = f"; discarded {len(strangers)} from {sorted(set(strangers))}" if strangers else ""
    if drained:  # their OTHER windows, drained so they cannot fill our inbox
        seen += f"; drained {len(drained)} from {sorted(set(drained))}"
    error = HandshakeError(
        f"no agreement received from {expected or 'the peer'} before the deadline{seen}")
    error.peer_sub_game = ahead
    raise error


def negotiate(rt: Any) -> dict[str, Any]:
    scent = rt.cfg.private.get("scent", {}).get("model", "multiplicative_cheb")
    neg = Negotiation(
        terms_from_config(rt.cfg), identity_from_config(rt.cfg),
        sub_game_number=rt.sub_game_number, role=rt.role,
        scent_model_sha256=declared_hash(scent), info_mode_sha256=declared_hash("belief"),
    )
    try:
        rt.transport.exchange_agreement_push(neg.signed())
    except Exception as exc:  # a handshake needs BOTH directions confirmed
        # Holding their agreement is not enough: acting on it starts a game only
        # one side is playing, and the other spends its whole budget pushing at a
        # peer that is already waiting on a turn. (imreeyal's g03, both ways.)
        raise HandshakeError(f"our agreement could not be delivered: {exc}") from exc
    theirs = _await_opponent(rt)
    identity = neg.verify_peer(_attributed(theirs))
    rt.peer_identity = identity
    mine = rt.cfg.private["game"]["group_id"]
    peer_gid = str(identity.get("group_id", "peer"))
    rt.game_id, rt.game_uid = derive_game_ids(neg.terms, mine, peer_gid)
    # The uid never crosses the wire during play, so two peers can complete a
    # whole series under different uids and only discover it when the reports
    # fail to join. If the peer declared one, reconcile it now.
    if (theirs_uid := theirs.get("game_uid")) and theirs_uid != rt.game_uid:
        raise HandshakeError(
            f"game_uid disagreement: ours {rt.game_uid} vs theirs {theirs_uid} — "
            "the two reports would never join")
    return identity
