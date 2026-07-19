"""Legal-transition state machine (FR-H2, F9) — sealed-turn choreography.

One send per turn (PRD_league_runtime §1.1): COMPUTING→COMMITTING→WAITING; the
old AWAITING_REVEAL/VERIFYING states died with the per-turn reveal. Every
active state may fall to TECHNICAL_LOSS (silent peer / error), which still
reports. REPORTING is terminal.
"""

from __future__ import annotations

from enum import Enum, auto

from cipherchase.exceptions import IllegalTransitionError


class State(Enum):
    HANDSHAKE = auto()
    WAITING = auto()
    COMPUTING = auto()
    COMMITTING = auto()
    AUDIT = auto()
    REPORTING = auto()
    TECHNICAL_LOSS = auto()


_LOSS = State.TECHNICAL_LOSS
_LEGAL: dict[State, set[State]] = {
    State.HANDSHAKE: {State.WAITING, _LOSS},
    State.WAITING: {State.COMPUTING, State.AUDIT, _LOSS},
    State.COMPUTING: {State.COMMITTING, _LOSS},
    State.COMMITTING: {State.WAITING, _LOSS},
    State.AUDIT: {State.REPORTING, _LOSS},
    State.TECHNICAL_LOSS: {State.REPORTING},
    State.REPORTING: set(),
}


class StateMachine:
    def __init__(self, initial: State = State.HANDSHAKE) -> None:
        self.state = initial

    def can(self, target: State) -> bool:
        return target in _LEGAL[self.state]

    def transition(self, target: State) -> State:
        if not self.can(target):
            raise IllegalTransitionError(f"{self.state.name} -> {target.name}")
        self.state = target
        return self.state
