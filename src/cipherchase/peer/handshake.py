"""Per-sub-game negotiation handshake (PRD_league_runtime §2.1, F5/F14).

Push our signed ``{terms, nonce, signature, identity}`` (transport retries
until the peer is up), read the peer's from our agreements inbox, verify terms
equality + signature, capture identity, derive the shared game ids.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.game_ids import derive_game_ids
from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError
from cipherchase.peer.terms import identity_from_config, terms_from_config


def negotiate(rt: Any) -> dict[str, Any]:
    neg = Negotiation(terms_from_config(rt.cfg), identity_from_config(rt.cfg))
    rt.transport.exchange_agreement_push(neg.signed())
    theirs = rt.transport.poll_agreement_or_none(rt.cfg.network["connect_timeout_seconds"])
    if theirs is None:
        raise HandshakeError("no agreement received from the peer before the deadline")
    identity = neg.verify_peer(theirs)
    rt.peer_identity = identity
    mine = rt.cfg.private["game"]["group_id"]
    peer_gid = str(identity.get("group_id", "peer"))
    rt.game_id, rt.game_uid = derive_game_ids(neg.terms, mine, peer_gid)
    return identity
