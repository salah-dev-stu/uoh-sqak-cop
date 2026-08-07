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
    theirs = rt.transport.poll_agreement_or_none(rt.cfg.network["connect_timeout_seconds"])
    if theirs is None:
        raise HandshakeError("no agreement received from the peer before the deadline")
    identity = neg.verify_peer(theirs)
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
