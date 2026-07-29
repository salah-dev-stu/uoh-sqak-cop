"""P1 turn engine (PRD_league_runtime §2.2-2.4): sealed turns, claims, spec record."""

from __future__ import annotations

from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.sealing import SealBook, sealed_spec_record
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def _runtime(role: str, transport) -> PeerRuntime:
    cfg = ConfigManager.load(CONFIG / ("police" if role == "police" else "thief"))
    rt = PeerRuntime(role=role, cfg=cfg, transport=transport, sub_game_number=1)
    rt.sm.transition(State.WAITING)  # tests drive turns directly, post-handshake
    return rt


def test_spec_record_is_sealed_step0() -> None:
    book = SealBook()
    cfg = ConfigManager.load(CONFIG / "police")
    sealed_spec_record(book, cfg, sub_game_number=2)
    record = book.records()[0]
    assert record["payload"]["step"] == 0
    assert record["payload"]["type"] == "system_spec"
    assert record["payload"]["sub_game_number"] == 2
    CommitReveal.verify(record["payload"], record["nonce"], record["commit"])


def test_thief_first_turn_is_one_sealed_wire_message() -> None:
    a, _b = make_pair()
    rt = _runtime("thief", a)
    result = rt.take_turn(None)
    assert result is None  # game continues
    tool, arg_key, wire = a.sent[-1]
    assert (tool, arg_key) == ("receive_turn", "message")
    msg = TurnMessage.from_dict(wire)
    assert msg.sender == "thief" and msg.step == 1
    assert msg.commit and msg.timestamp and msg.hint is not None
    assert "move" not in wire and "intent" not in wire  # sealed until audit
    assert rt.book.records()[-1]["payload"]["step"] == 1  # sealed locally


def test_police_move_attaches_capture_claim_at_new_cell() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)
    rt.take_turn(None)
    wire = a.sent[-1][2]
    if wire["capture_claim"] is not None:  # MOVE turn → claim == own new cell
        assert wire["capture_claim"] == list(rt.me.position)


def test_thief_answers_claims_honestly_and_final_message_on_capture() -> None:
    a, _b = make_pair()
    rt = _runtime("thief", a)
    # wrong-cell claim → honest "not caught", attached to my next turn
    outcome = rt.handle(TurnMessage(step=1, sender="police", capture_claim=[0, 0]).to_dict())
    assert outcome.result is None
    assert outcome.claim_response == {"claim": [0, 0], "caught": False}
    # exact-cell claim → caught: final "You got me." + result capture/police
    outcome = rt.handle(
        TurnMessage(step=2, sender="police", capture_claim=list(rt.me.position)).to_dict()
    )
    assert outcome.result == ("capture", "police")
    wire = a.sent[-1][2]
    assert wire["hint"] == "You got me."
    assert wire["claim_response"]["caught"] is True


def test_police_ends_on_caught_response_or_win_claim() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)
    out = rt.handle(
        TurnMessage(step=1, sender="thief",
                    claim_response={"claim": [1, 1], "caught": True}).to_dict()
    )
    assert out.result == ("capture", "police")
    rt2 = _runtime("police", a)
    rt2.last_seen_step = 8  # mid-game: step 9 is the next expected inbound
    out2 = rt2.handle(
        TurnMessage(step=9, sender="thief", win_claim={"type": "survival"}).to_dict()
    )
    assert out2.result == ("survival", "thief")


def test_thief_survival_win_claim_at_max_steps() -> None:
    a, _b = make_pair()
    rt = _runtime("thief", a)
    rt.step_number = rt.max_steps - 1  # next take_turn reaches the threshold
    result = rt.take_turn(None)
    assert result == ("survival", "thief")
    assert a.sent[-1][2]["win_claim"] == {"type": "survival"}


def test_duplicate_step_is_ignored_idempotently() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)
    msg = TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9}).to_dict()
    assert rt.handle(msg).result is None
    assert rt.handle(msg).duplicate is True  # second arrival: no double-processing


def test_bluff_channel_off_by_default_is_inert() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)  # ships with bluff_weight 0.0
    assert rt.bluff_weight == 0.0
    rt.handle(TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9},
                          hint="Heading north, promise.").to_dict())
    assert rt.honesty.p_honest() == 0.5  # never calibrated → words ignored
    assert rt.last_claim is None


def test_bluff_channel_calibrates_honesty_and_nudges_belief() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)
    rt.bluff_weight = 0.6  # enable the Bayesian hint-fusion layer (F6/F7)
    rt.handle(TurnMessage(step=1, sender="thief", smell_grid={"3,3": 0.9},
                          hint="I'm heading north.").to_dict())
    assert rt.last_claim is not None  # a claim was extracted and remembered
    control = rt.belief.as_matrix()
    rt.handle(TurnMessage(step=2, sender="thief", smell_grid={"1,3": 0.9},
                          hint="Still heading north.").to_dict())
    assert rt.honesty.p_honest() > 0.5  # the peak really moved north → honest
    assert rt.belief.as_matrix() != control  # fusion changed the belief


def test_strategic_deception_lies_by_rule_not_dice() -> None:
    a, _b = make_pair()
    rt = _runtime("police", a)
    rt.deception_mode = "strategic"  # opt-in rule-based bluffing (F8)
    rt.me = rt.me.moved_to((3, 3))
    rt.belief.reweight([(3, 5)], 1e6)  # believe the thief is 2 cells away → close
    from cipherchase.strategy.deception import choose_intent
    assert choose_intent(rt) == "lie"  # cop bluffs when it has closed the gap
    rt.belief.reweight([(3, 5)], 0.0)
    rt.belief.reweight([(6, 6)], 1e6)  # now believe it is far
    assert choose_intent(rt) == "truth"  # nothing to gain from lying when distant

