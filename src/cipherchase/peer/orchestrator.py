"""Single orchestration gateway (FR-H1, F9).

Drives one move through the legal-transition FSM and routes EVERY outbound MCP
call through the gatekeeper (NFR-3): compute → commit (move hidden) → reveal.
A deadline/silent peer funnels into ``technical_loss`` — never a hang.
"""

from __future__ import annotations

from typing import Any

from cipherchase.domain.brains import Decision
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.sealing import SealBook, move_payload
from cipherchase.peer.state_machine import State, StateMachine


class Orchestrator:
    def __init__(
        self, *, role: str, brain: Any, transport: Any, gate: Any, sealbook: SealBook,
        sm: StateMachine | None = None,
    ) -> None:
        self.role = role
        self.brain = brain
        self.transport = transport
        self.gate = gate
        self.sealbook = sealbook
        self.sm = sm or StateMachine(State.WAITING)

    def _send(self, message: TurnMessage, action: str) -> None:
        self.gate.execute(
            lambda: self.transport.send_turn(message.to_dict()), service="mcp", action=action
        )

    def play_move(
        self, state: OwnState, belief: Any, barriers: frozenset[Any], step: int
    ) -> Decision:
        self.sm.transition(State.COMPUTING)
        decision = self.brain.decide(state, belief, barriers)
        commit, _nonce = self.sealbook.seal(move_payload(step, state, decision))
        self.sm.transition(State.COMMITTING)
        self._send(TurnMessage(step=step, sender=self.role, commit=commit), "send_commit")
        self.sm.transition(State.AWAITING_REVEAL)
        self._send(
            TurnMessage(
                step=step, sender=self.role, commit=commit,
                move=decision.direction.value, intent=decision.intent, hint=decision.hint,
            ),
            "send_reveal",
        )
        self.sm.transition(State.VERIFYING)
        self.sm.transition(State.WAITING)
        return decision

    def technical_loss(self) -> State:
        return self.sm.transition(State.TECHNICAL_LOSS)
