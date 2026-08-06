"""Signed control channel: reference-compatible enable/status/restart/quit —
and, beyond the reference, every control message is SEALED into the audit book."""

from __future__ import annotations

from fakes.fake_transport import make_pair

from cipherchase.domain.crypto import CommitReveal
from cipherchase.peer.control_link import ControlLink
from cipherchase.peer.sealing import SealBook


def _pair():
    a, b = make_pair()
    return (ControlLink("police", a, SealBook()), ControlLink("thief", b, SealBook()), a, b)


def test_channel_is_active_only_when_both_peers_enabled() -> None:
    ours, theirs, _a, _b = _pair()
    assert not ours.active
    ours.enable()
    theirs.drain()          # they see our enable
    theirs.enable()
    ours.drain()            # we see theirs
    assert ours.active and theirs.active


def test_status_broadcasts_only_on_change_and_updates_opponent_view() -> None:
    ours, theirs, a, _b = _pair()
    ours.enable()
    theirs.drain()
    sent_before = len(a.sent)
    ours.broadcast_status("PLAYING", sub_game_number=2, step_budget=1.5)
    ours.broadcast_status("PLAYING", sub_game_number=2, step_budget=1.5)  # duplicate: silent
    assert len(a.sent) == sent_before + 1  # never spam the wire
    theirs.drain()
    assert theirs.opponent["status"] == "PLAYING"
    assert theirs.opponent["sub_game_number"] == 2


def test_restart_is_auto_approved_only_when_active() -> None:
    ours, theirs, _a, _b = _pair()
    ours.enable()
    theirs.drain()
    ours.send_restart()
    theirs.drain()
    assert theirs.take_pending_restart() is False  # channel not active → refused
    theirs.enable()
    ours.drain()
    ours.send_restart()
    theirs.drain()
    assert theirs.take_pending_restart() is True   # both enabled → auto-approved
    assert theirs.take_pending_restart() is False  # consumed exactly once


def test_quit_marks_the_opponent_gone() -> None:
    ours, theirs, _a, _b = _pair()
    ours.send_quit()
    theirs.drain()
    assert theirs.opponent_quit and theirs.opponent["status"] == "QUIT"


def test_every_control_message_is_sealed_into_the_audit_book() -> None:
    ours, theirs, _a, _b = _pair()
    ours.enable()
    theirs.drain()
    ours.broadcast_status("THINKING", sub_game_number=1, step_budget=0.5)
    theirs.drain()
    for book in (ours.book, theirs.book):
        control = [r for r in book.records() if r["payload"].get("type") == "control"]
        assert control, "control history must be part of the sealed audit trail"
        for record in control:  # each control record verifies like a move record
            CommitReveal.verify(record["payload"], record["nonce"], record["commit"])
            assert record["payload"]["direction"] in ("sent", "received")
    kinds = [r["payload"]["kind"] for r in ours.book.records()
             if r["payload"].get("type") == "control"]
    assert "enable" in kinds and "status" in kinds


def test_unknown_control_kind_is_reported_not_crashed() -> None:
    ours, theirs, _a, _b = _pair()
    ours.transport.send_control({"kind": "dance", "sender": "police"})
    events = theirs.drain()
    assert events == [{"type": "control_unknown", "kind": "dance"}]


def test_control_wire_carries_exactly_the_reference_key_set() -> None:
    # najamjad warm-up finding: a strict peer parses controls with cls(**data) —
    # our internal `payload` field must never leak onto the wire.
    reference_keys = {"kind", "sender", "sub_game_number", "status", "step_budget"}
    ours, _theirs, a, _b = _pair()
    ours.enable()
    ours.broadcast_status("PLAYING", sub_game_number=2, step_budget=30.0)
    ours.send_restart()
    ours.send_quit()
    control_wires = [w for (tool, _k, w) in a.sent if tool == "receive_control"]
    assert len(control_wires) == 4
    for wire in control_wires:
        assert set(wire) == reference_keys, wire


def test_control_records_never_share_the_game_step_numbering() -> None:
    # imreeyal's s1 audit refusal: our sealed control records were numbered 1,2
    # in the SAME space as moves, so their continuity check read the revealed
    # chain as [1,2,1,2,3,…] and refused. A counterparty reconstructing the game
    # from step numbers has no way to know our 1 is not a move — unless the
    # numbering itself says so. Negative steps are self-evident to a peer that
    # has never seen our code, and still order the control history.
    ours, _theirs, _a, _b = _pair()
    ours.enable()
    ours.broadcast_status("PLAYING", sub_game_number=1, step_budget=30.0)
    control = [r["payload"] for r in ours.book.records()
               if r["payload"].get("type") == "control"]
    assert control, "control history is still sealed"
    assert all(r["step"] < 1 for r in control), "control steps must be outside the game chain"
    game_steps = [r["payload"]["step"] for r in ours.book.records()
                  if "type" not in r["payload"]]
    assert not set(game_steps) & {r["step"] for r in control}
