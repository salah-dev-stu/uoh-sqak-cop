"""Handshake guards (SPEC §3.7/§3.11): declare the context, refuse a contradiction.

`terms` equality alone cannot catch two peers that both took POLICE, or that are
playing different sub-games of the same series — both complete a *perfect*
handshake and then deadlock or desync. We burned a warm-up window on exactly the
role collision. Omission is never a refusal: an opponent that declares nothing
still gets a game, we just lose the guard.
"""

from __future__ import annotations

import pytest

from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError

TERMS = {"board_size": 7, "num_games": 6}
IDENT = {"group_id": "uoh-sqak"}
CTX = {"sub_game_number": 1, "role": "police", "game_uid": "u-1",
       "scent_model_sha256": "aa", "info_mode_sha256": "bb"}


def _neg(**over) -> Negotiation:
    return Negotiation(TERMS, IDENT, **{**CTX, **over})


def test_the_declaration_carries_the_context_the_league_asks_for() -> None:
    signed = _neg().signed()
    for key, value in CTX.items():
        assert signed[key] == value
    assert set(signed) >= {"terms", "nonce", "signature", "identity", *CTX}


def test_a_role_collision_is_refused_before_a_move_is_played() -> None:
    ours = _neg(role="police")
    theirs = _neg(role="police").signed()  # both peers took POLICE
    with pytest.raises(HandshakeError, match="role"):
        ours.verify_peer(theirs)


def test_opposite_roles_are_accepted() -> None:
    assert _neg(role="police").verify_peer(_neg(role="thief").signed()) == IDENT


def test_a_sub_game_index_disagreement_is_refused() -> None:
    with pytest.raises(HandshakeError, match="sub-game"):
        _neg(sub_game_number=2).verify_peer(_neg(role="thief", sub_game_number=3).signed())


def test_a_differing_game_uid_is_refused() -> None:
    with pytest.raises(HandshakeError, match="game_uid"):
        _neg().verify_peer(_neg(role="thief", game_uid="u-2").signed())


@pytest.mark.parametrize("family", ["scent_model_sha256", "info_mode_sha256"])
def test_two_declared_models_that_differ_refuse(family: str) -> None:
    with pytest.raises(HandshakeError, match="model"):
        _neg().verify_peer(_neg(role="thief", **{family: "zz"}).signed())


@pytest.mark.parametrize("family", ["scent_model_sha256", "info_mode_sha256"])
def test_an_undeclared_model_never_refuses(family: str) -> None:
    theirs = _neg(role="thief").signed()
    del theirs[family]
    assert _neg().verify_peer(theirs) == IDENT
    ours = _neg(**{family: ""})  # we declare nothing either
    assert ours.verify_peer(_neg(role="thief").signed()) == IDENT


def test_a_peer_that_declares_no_context_at_all_still_gets_a_game() -> None:
    bare = Negotiation(TERMS, IDENT).signed()
    assert set(bare) == {"terms", "nonce", "signature", "identity"}
    assert _neg().verify_peer(bare) == IDENT


def test_a_uid_the_peer_derived_differently_is_caught_at_the_handshake() -> None:
    # The uid never crosses the wire during play, so without this check two
    # peers can finish a whole series and only discover the split when their
    # result files fail to join — after the window is gone.
    from pathlib import Path

    from fakes.fake_transport import make_pair

    from cipherchase.peer.handshake import negotiate
    from cipherchase.peer.runtime import PeerRuntime
    from cipherchase.peer.terms import identity_from_config, terms_from_config
    from cipherchase.shared.config import ConfigManager

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    a, b = make_pair()
    theirs = Negotiation(terms_from_config(cfg), identity_from_config(cfg),
                         role="thief", game_uid="a-different-uid").signed()
    b.exchange_agreement_push(theirs)
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    with pytest.raises(HandshakeError, match="never join"):
        negotiate(rt)
