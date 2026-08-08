"""A stranger must not be able to burn our handshake windows (imreeyal, twelve).

Our endpoint is public and unauthenticated: anyone who has ever had the URL can
call `negotiate`. Twelve agreements we could not attribute to imreeyal consumed
twelve windows and ended the series — most likely a peer we practised against
still holding a stale ngrok URL in its config.

Consuming a stranger's agreement costs a whole window and teaches us nothing. We
discard it and keep listening within the same budget, so a third party is noise
rather than a denial of service. And every refusal now names WHO, so the next one
is attributable instead of a counting argument.
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


def _rt(transport, expect: str = "imreeyal", n: int = 1) -> PeerRuntime:
    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["game"] = {**cfg.private["game"], "opponent_group_id": expect}
    cfg.private["network"] = {**cfg.private["network"], "connect_timeout_seconds": 2, "index_patience_seconds": 3}
    return PeerRuntime(role="police", cfg=cfg, transport=transport, sub_game_number=n)


def _agreement(rt: PeerRuntime, group: str, role: str = "thief", n: int = 1) -> dict:
    ident = {**identity_from_config(rt.cfg), "group_id": group}
    return Negotiation(terms_from_config(rt.cfg), ident,
                       sub_game_number=n, role=role).signed()


def test_a_stranger_is_discarded_and_the_real_peer_still_gets_through() -> None:
    a, b = make_pair()
    rt = _rt(a)
    for _ in range(5):  # a chatty stranger ahead of them in the queue
        b.exchange_agreement_push(_agreement(rt, "najamjad"))
    b.exchange_agreement_push(_agreement(rt, "imreeyal"))
    assert negotiate(rt)["group_id"] == "imreeyal", "the stranger must not cost the window"


def test_a_window_of_only_strangers_still_fails_and_names_them() -> None:
    a, b = make_pair()
    rt = _rt(a)
    b.exchange_agreement_push(_agreement(rt, "najamjad"))
    with pytest.raises(HandshakeError, match="najamjad"):
        negotiate(rt)


def test_with_no_expected_opponent_we_accept_whoever_answers() -> None:
    # Unnamed opponent (a self-test or an unplanned peer) must keep working.
    a, b = make_pair()
    rt = _rt(a, expect="")
    b.exchange_agreement_push(_agreement(rt, "somebody"))
    assert negotiate(rt)["group_id"] == "somebody"


def test_a_refusal_names_the_peer_its_role_and_its_index() -> None:
    # A drained agreement must still be reported by name. Draining stops their
    # other windows filling our inbox; it must not also make them invisible, or
    # we are back to arguing about counts with no evidence.
    a, b = make_pair()
    rt = _rt(a, n=3)
    b.exchange_agreement_push(_agreement(rt, "imreeyal", role="police", n=5))
    with pytest.raises(HandshakeError) as caught:
        negotiate(rt)
    note = str(caught.value)
    assert "imreeyal" in note and "police" in note and "5" in note, note
    assert "drained" in note


def test_a_wrong_index_agreement_is_drained_not_returned() -> None:
    # anrbj666's finding, and the mechanism is joint: their next window re-pushed
    # its agreement every 7s while ours played the current one. We consumed ONE
    # per window and refused it, so their pushes outran our draining, the bounded
    # inbox hit capacity, and `negotiate` then failed for EVERYONE — including the
    # correct counterpart. A full inbox looks "up" to every probe while being
    # unable to start any game.
    a, b = make_pair()
    rt = _rt(a, n=1)
    for _ in range(20):                      # their g02 runner, re-pushing
        b.exchange_agreement_push(_agreement(rt, "imreeyal", role="thief", n=2))
    b.exchange_agreement_push(_agreement(rt, "imreeyal", role="thief", n=1))
    assert negotiate(rt)["group_id"] == "imreeyal", (
        "the correct window must survive a backlog of the peer's other windows")


def test_draining_still_reports_how_far_ahead_the_peer_was() -> None:
    # Draining must not swallow the catch-up signal: if every agreement in the
    # window declares a higher index, we are behind and need to converge.
    a, b = make_pair()
    rt = _rt(a, n=2)
    for _ in range(4):
        b.exchange_agreement_push(_agreement(rt, "imreeyal", role="thief", n=5))
    with pytest.raises(HandshakeError) as caught:
        negotiate(rt)
    assert caught.value.peer_sub_game == 5, "the highest index seen must survive"


def test_a_full_inbox_says_which_channel_and_how_deep() -> None:
    # Their second point: at capacity our negotiate failed for everyone with
    # "agreement inbox at capacity" and no indication of the channel's depth or
    # that a backlog was the cause. A peer in that state answers every probe
    # while being unable to start any game — the worst diagnostic shape there is.
    from cipherchase.exceptions import QueueFullError
    from cipherchase.infra.inboxes import Inboxes

    boxes = Inboxes(2)
    boxes.put_agreement({"a": 1})
    boxes.put_agreement({"a": 2})
    with pytest.raises(QueueFullError) as caught:
        boxes.put_agreement({"a": 3})
    note = str(caught.value)
    assert "agreement" in note and "2" in note, note
    assert "drain" in note.lower() or "backlog" in note.lower(), (
        "the message must point at the cause, not just the symptom")
