"""Tabular Q-learning cop (learning seam): policy lookup + greedy fallback."""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.strategy.qbrain import N_STATES, QBrain, encode_state

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()


def _belief(cell):
    g = BeliefGrid(7, smell_trust=1e6)
    g.observe_smell({f"{cell[0]},{cell[1]}": 1.0})
    return g


def test_state_encoding_is_a_clamped_relative_grid() -> None:
    assert N_STATES == 49
    assert encode_state((3, 3), (3, 3), B) == 24  # centred (dr=dc=0)
    assert encode_state((0, 0), (6, 6), B) == 48  # clamped to (+3,+3)
    assert encode_state((6, 6), (0, 0), B) == 0   # clamped to (-3,-3)
    # far apart clamps to the same state as exactly 3 away
    assert encode_state((0, 0), (0, 6), B) == encode_state((0, 0), (0, 3), B)


def test_qbrain_follows_its_policy_when_the_action_is_legal() -> None:
    brain = QBrain(B, {"policy": [4] * N_STATES})  # 4 == STAY, always legal
    assert brain._pick_move(OwnState("police", (3, 3)), _belief((0, 0)), EMPTY) is Direction.STAY


def test_qbrain_falls_back_to_greedy_pursuit_for_an_unseen_state() -> None:
    brain = QBrain(B, {"policy": []})  # empty table → always fall back
    move = brain._pick_move(OwnState("police", (3, 3)), _belief((3, 6)), EMPTY)
    # greedy pursuit of a thief due east must not move away (west)
    assert move is not Direction.W and move in B.legal_moves((3, 3), EMPTY)


def test_qbrain_loads_a_policy_from_a_json_file(tmp_path) -> None:
    import json
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"policy": [4] * N_STATES}))  # all STAY
    brain = QBrain(B, {"qbrain_policy_path": str(path)})
    assert len(brain.policy) == N_STATES
    assert brain._pick_move(OwnState("police", (2, 2)), _belief((5, 5)), EMPTY) is Direction.STAY


def test_qbrain_with_no_policy_source_is_pure_greedy() -> None:
    brain = QBrain(B, {})  # no inline policy, no path → empty table
    assert brain.policy == []


def test_qbrain_ignores_an_illegal_policy_action_and_falls_back() -> None:
    # policy says N everywhere; from the top edge N is illegal → greedy fallback picks a legal move
    brain = QBrain(B, {"policy": [0] * N_STATES})  # 0 == N
    move = brain._pick_move(OwnState("police", (0, 3)), _belief((6, 3)), EMPTY)
    assert move in B.legal_moves((0, 3), EMPTY) and move is not Direction.N
