"""Orchestrator: gated commit-reveal turn driven by the FSM (FR-H1/H2, F9, NFR-3)."""

from __future__ import annotations

from fakes.fake_transport import make_pair

from cipherchase.constants import Direction
from cipherchase.domain.brains import Decision
from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.orchestrator import Orchestrator
from cipherchase.peer.sealing import SealBook
from cipherchase.peer.state_machine import State
from cipherchase.shared.gatekeeper import ApiGatekeeper


class _AllowAll:
    def allow(self, service: str) -> bool:
        return True


class _StubBrain:
    def decide(self, state, belief, barriers):  # type: ignore[no-untyped-def]
        return Decision(direction=Direction.S, intent="truth", hint="northward, honest")


def _orchestrator():
    a, b = make_pair()
    gate = ApiGatekeeper(_AllowAll(), sleep=lambda _s: None)
    orch = Orchestrator(role="police", brain=_StubBrain(), transport=a, gate=gate, sealbook=SealBook())
    return orch, b, gate


def test_play_move_commits_then_reveals_through_the_gate() -> None:
    from cipherchase.domain.own_state import OwnState

    orch, opponent, gate = _orchestrator()
    orch.play_move(OwnState("police", (0, 0)), belief=None, barriers=frozenset(), step=1)

    commit_msg = TurnMessage.from_dict(opponent.poll_turn(0.5))
    reveal_msg = TurnMessage.from_dict(opponent.poll_turn(0.5))
    assert commit_msg.commit and commit_msg.move is None      # commit hides the move
    assert reveal_msg.move == "S" and reveal_msg.commit == commit_msg.commit
    assert [c["action"] for c in gate.ledger] == ["send_commit", "send_reveal"]
    assert orch.sm.state is State.WAITING


def test_technical_loss_transition() -> None:
    orch, _opp, _gate = _orchestrator()
    orch.technical_loss()
    assert orch.sm.state is State.TECHNICAL_LOSS
