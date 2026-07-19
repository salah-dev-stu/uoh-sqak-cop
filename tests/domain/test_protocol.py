"""Wire message contract (§2.4). Lenient parse, exact emit, sealed moves."""

from __future__ import annotations

from cipherchase.domain.protocol import AuditPayload, ControlMessage, TurnMessage


def test_turn_message_round_trip() -> None:
    msg = TurnMessage(
        step=1, sender="thief", hint="I'm heading north", smell_grid={"3,3": 0.9},
        commit="abc", timestamp="2026-08-01T00:00:00Z", barrier_placed=None,
    )
    back = TurnMessage.from_dict(msg.to_dict())
    assert back == msg
    assert back.smell_grid == {"3,3": 0.9}


def test_from_dict_ignores_unknown_keys() -> None:
    data = {"step": 2, "sender": "police", "extra": "ignored", "move": "N"}
    msg = TurnMessage.from_dict(data)
    assert msg.step == 2 and msg.sender == "police"
    assert "move" not in msg.to_dict()  # plaintext moves never round-trip to the wire


def test_no_opponent_coordinates_on_the_wire() -> None:
    # F7/FR-B5: only the scent intensity field crosses, never opponent coords.
    wire = TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9}).to_dict()
    assert set(wire["smell_grid"].keys()) == {"3,3"}
    for banned in ("opponent", "opponent_pos", "enemy", "their_position", "move", "intent"):
        assert banned not in wire


def test_control_message_round_trip() -> None:
    ctrl = ControlMessage(kind="enable", sender="police", sub_game_number=2, step_budget=8.0)
    assert ControlMessage.from_dict(ctrl.to_dict()) == ctrl


def test_audit_payload_round_trip() -> None:
    payload = AuditPayload(
        sender="thief",
        records=[{"payload": {"step": 1}, "nonce": "n", "commit": "c"}],
        result_claim="survival",
    )
    assert AuditPayload.from_dict(payload.to_dict()) == payload
