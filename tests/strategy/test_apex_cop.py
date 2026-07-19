"""ApexCop layered brain (AB-1,2,6,7,12..15): best-response + endgame proof."""

from __future__ import annotations

import random

from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import is_capture
from cipherchase.strategy.apex_cop import ApexCop, escape_value

B = Board(7)
EMPTY: frozenset[tuple[int, int]] = frozenset()
CFG = {"opponent_model": "thief_v1", "apex_lock_mass": 0.5}


def _locked(cell):
    g = BeliefGrid(7, smell_trust=1e6)
    g.observe_smell({f"{cell[0]},{cell[1]}": 1.0})
    return g


def _diffuse():
    return BeliefGrid(7, smell_trust=4.0)  # uniform-ish, no observation → not locked


def test_apex_is_a_police_brain() -> None:
    from cipherchase.strategy.police_heuristic import PoliceBrain
    assert issubclass(ApexCop, PoliceBrain)
    assert ApexCop.role == "police"


def test_decide_is_always_legal() -> None:
    cop = ApexCop(B, dict(CFG))
    for seed in range(30):
        rng = random.Random(seed)
        c = (rng.randrange(7), rng.randrange(7))
        t = (rng.randrange(7), rng.randrange(7))
        if c == t:
            continue
        d = cop.decide(OwnState("police", c), _locked(t), EMPTY)
        assert d.direction in B.legal_moves(c, EMPTY)
        if d.barrier_cell is not None:
            assert d.barrier_cell in B.neighbors(c, frozenset())


def test_best_response_picks_the_min_worst_escape_move() -> None:
    # L2: with a fixed thief model, the chosen move must minimise the worst-case
    # escape value over the model's predicted replies (the brain's own contract).
    cop = ApexCop(B, {"opponent_model": "thief_v1", "apex_lock_mass": 0.5,
                      "apex_barrier_topk": 0})  # disable barriers to isolate the move
    c, t = (3, 5), (3, 1)
    d = cop.decide(OwnState("police", c), _locked(t), EMPTY)
    chosen = B.target_of(c, d.direction)
    worst = cop._worst_escape(chosen, t, EMPTY)
    for direction in B.legal_moves(c, EMPTY):
        alt = B.target_of(c, direction)
        assert worst <= cop._worst_escape(alt, t, EMPTY) + 1e-9


def test_endgame_proof_captures_a_cornered_thief() -> None:
    # L3: locked belief + corner geometry → ApexCop finishes a boxable thief.
    cop = ApexCop(B, dict(CFG))
    c, t = (0, 2), (0, 0)
    barriers = frozenset({(2, 0), (2, 1)})
    thief = t
    for _ in range(10):
        d = cop.decide(OwnState("police", c), _locked(thief), barriers)
        b2 = barriers | ({d.barrier_cell} if d.barrier_cell else set())
        c = B.step(c, d.direction, b2)
        barriers = b2
        if is_capture(B, c, thief, barriers):
            assert cop.last_layer == "endgame"
            return
        moves = [m for m in B.legal_moves(thief, barriers)
                 if not is_capture(B, c, B.target_of(thief, m), barriers)]
        if not moves:
            return
        thief = B.target_of(thief, moves[0])
    raise AssertionError("ApexCop failed to close a proven corner")


def test_endgame_is_gated_by_lock() -> None:
    # Diffuse belief in the same geometry: the proof is unsafe → fall to L2.
    cop = ApexCop(B, dict(CFG))
    cop.decide(OwnState("police", (0, 2)), _diffuse(), frozenset({(2, 0), (2, 1)}))
    assert cop.last_layer != "endgame"


def test_pick_move_and_barrier_delegators_agree_with_decide() -> None:
    cop = ApexCop(B, dict(CFG))
    state, belief = OwnState("police", (3, 5)), _locked((3, 1))
    d = cop.decide(state, belief, EMPTY)
    assert cop._pick_move(state, belief, EMPTY) == d.direction
    assert cop._pick_barrier(state, belief, EMPTY) == d.barrier_cell


def test_escape_value_rewards_boxing_and_closing() -> None:
    # Fewer reachable cells / closer cop / nearer a wall → lower escape value.
    open_far = escape_value(B, (6, 6), (3, 3), EMPTY, 1.0, 0.6, 0.8)
    boxed_near = escape_value(B, (0, 1), (0, 0), frozenset({(1, 0), (0, 1)}), 1.0, 0.6, 0.8)
    assert boxed_near < open_far
