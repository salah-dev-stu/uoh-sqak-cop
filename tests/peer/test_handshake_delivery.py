"""A handshake needs BOTH directions (imreeyal's g03 defect, checked on our side).

Their peer returned a received agreement even on a lap where its own push had
raised, so it entered a game alone while we were still trying to reach it. They
asked us to confirm we do not do the same. We do not — and now it is pinned,
because the property is invisible until it costs a series.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fakes.fake_transport import make_pair

from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError
from cipherchase.peer.handshake import negotiate
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.terms import identity_from_config, terms_from_config
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


class _PushFails:
    """Their agreement is waiting for us; our own push cannot get out."""

    def __init__(self, inner):
        self._inner = inner

    def exchange_agreement_push(self, signed):
        raise ConnectionError("push never landed")

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_we_never_enter_a_game_our_push_did_not_reach() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    a, b = make_pair()
    b.exchange_agreement_push(Negotiation(
        terms_from_config(cfg), identity_from_config(cfg), role="thief").signed())
    rt = PeerRuntime(role="police", cfg=cfg, transport=_PushFails(a), sub_game_number=1)
    with pytest.raises(HandshakeError, match="could not be delivered"):
        negotiate(rt)


def test_a_delivered_push_plus_their_agreement_completes() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    a, b = make_pair()
    b.exchange_agreement_push(Negotiation(
        terms_from_config(cfg), identity_from_config(cfg), role="thief").signed())
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    assert negotiate(rt)["group_id"] == "uoh-sqak"
    assert rt.game_uid, "ids derived once both directions are confirmed"


def test_the_identity_declares_our_counted_game_count() -> None:
    # Two-channel principle: the handshake says in plaintext what the sealed
    # step-0 proves, so the opponent's artifact never has to guess our count and
    # floor it to zero. Ours was simply absent from the wire.
    #
    # Derive the expected number from the artifact set on disk rather than
    # pinning a literal. This test HELD at 0 through the imreeyal counted
    # series, so anrbj666's aggregate recorded uoh-sqak: 0 from our own
    # declaration and both teams' files agreed on a false value. A number
    # asserted against itself proves nothing; asserted against the games we
    # can show, it fails the build the moment the two drift apart.
    played = sorted(p.name for p in (CONFIG.parent / "docs/league").glob("*-counted"))
    cfg = ConfigManager.load(CONFIG / "police")
    ident = identity_from_config(cfg)
    assert ident["counted_games_played"] == len(played), (
        f"we declare {ident['counted_games_played']} counted series but ship "
        f"artifacts for {len(played)}: {played}")
