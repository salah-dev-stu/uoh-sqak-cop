"""Legal-transition state machine (FR-H2, F9)."""

from __future__ import annotations

import pytest

from cipherchase.exceptions import IllegalTransitionError
from cipherchase.peer.state_machine import State, StateMachine


def test_happy_path_through_a_turn_to_reporting() -> None:
    sm = StateMachine()
    for state in (
        State.WAITING, State.COMPUTING, State.COMMITTING, State.AWAITING_REVEAL,
        State.VERIFYING, State.AUDIT, State.REPORTING,
    ):
        sm.transition(state)
    assert sm.state is State.REPORTING


def test_illegal_transition_raises() -> None:
    sm = StateMachine()
    with pytest.raises(IllegalTransitionError):
        sm.transition(State.AUDIT)  # HANDSHAKE can't jump to AUDIT


def test_any_active_state_can_fall_to_technical_loss() -> None:
    sm = StateMachine()
    sm.transition(State.WAITING)
    sm.transition(State.TECHNICAL_LOSS)  # silent peer / deadline
    sm.transition(State.REPORTING)  # even a loss still reports
    assert sm.state is State.REPORTING


def test_reporting_is_terminal() -> None:
    sm = StateMachine(State.REPORTING)
    with pytest.raises(IllegalTransitionError):
        sm.transition(State.WAITING)
