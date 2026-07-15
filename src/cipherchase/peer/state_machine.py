"""Legal-transition state machine (FR-H2, F9).

Only declared transitions are allowed; anything else raises. Every active state
may fall to ``TECHNICAL_LOSS`` (silent peer / deadline / error), which still
reports. ``REPORTING`` is terminal.
"""

from __future__ import annotations

from enum import Enum, auto

from cipherchase.exceptions import IllegalTransitionError


class State(Enum):
    HANDSHAKE = auto()
    WAITING = auto()
    COMPUTING = auto()
    COMMITTING = auto()
    AWAITING_REVEAL = auto()
    VERIFYING = auto()
    AUDIT = auto()
    REPORTING = auto()
    TECHNICAL_LOSS = auto()


_LOSS = State.TECHNICAL_LOSS
_LEGAL: dict[State, set[State]] = {
    State.HANDSHAKE: {State.WAITING, _LOSS},
    State.WAITING: {State.COMPUTING, _LOSS},
    State.COMPUTING: {State.COMMITTING, _LOSS},
    State.COMMITTING: {State.AWAITING_REVEAL, _LOSS},
    State.AWAITING_REVEAL: {State.VERIFYING, _LOSS},
    State.VERIFYING: {State.WAITING, State.AUDIT, _LOSS},
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
