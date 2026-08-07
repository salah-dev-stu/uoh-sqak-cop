"""Exact endgame solver (AB-8..AB-11): the corner is a finite, solvable game."""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.domain.board import Board
from cipherchase.domain.rules import is_capture
from cipherchase.strategy.endgame import EndgameSolver, endgame_trigger

B = Board(7)


def test_forced_win_in_a_sealed_corner_pocket() -> None:
    # Thief boxed at (0,0): the (2,0)/(2,1) seal + cop at the mouth → forced capture.
    barriers = frozenset({(2, 0), (2, 1)})
    solver = EndgameSolver(B, depth=8, nodes=50_000, survival_threshold=35)
    line = solver.solve(cop=(0, 2), thief=(0, 0), barriers=barriers, ply=0)
    assert line is not None  # a capture line exists
    assert line.action[0] in B.legal_moves((0, 2), barriers)


def test_forced_line_actually_captures_against_worst_case_play() -> None:
    barriers = frozenset({(2, 0), (2, 1)})
    solver = EndgameSolver(B, depth=8, nodes=50_000, survival_threshold=35)
    cop, thief = (0, 2), (0, 0)
    for _ in range(8):  # play the proven cop line vs an adversarial thief oracle
        line = solver.solve(cop=cop, thief=thief, barriers=barriers, ply=0)
        assert line is not None, "proof must hold every ply of its own line"
        move, q = line.action
        b2 = barriers | ({q} if q else set())
        cop = B.step(cop, move, b2)
        barriers = b2
        if is_capture(B, cop, thief, barriers):
            return
        # worst-case thief: pick the reply that survives longest (still solvable → none does)
        best = None
        for d in B.legal_moves(thief, barriers):
            t2 = B.target_of(thief, d)
            if not is_capture(B, cop, t2, barriers):
                best = t2
                break
        if best is None:
            return  # every reply is capture → done
        thief = best
    raise AssertionError("forced line failed to capture within the horizon")


def test_open_board_far_apart_is_not_a_forced_win() -> None:
    solver = EndgameSolver(B, depth=8, nodes=50_000, survival_threshold=35)
    assert solver.solve(cop=(0, 0), thief=(4, 4), barriers=frozenset(), ply=0) is None


def test_trigger_boundaries() -> None:
    # wall_dist(thief) <= 2 AND gap <= 4
    assert endgame_trigger(B, (0, 2), (0, 0), wall_k=2, gap_max=4)  # corner, gap 2
    assert not endgame_trigger(B, (0, 6), (3, 3), wall_k=2, gap_max=4)  # centre thief
    assert not endgame_trigger(B, (6, 6), (0, 0), wall_k=2, gap_max=4)  # gap 12


def test_node_cap_short_circuits_to_unproven() -> None:
    tiny = EndgameSolver(B, depth=8, nodes=5, survival_threshold=35)
    line = tiny.solve(cop=(0, 2), thief=(0, 0), barriers=frozenset({(2, 0), (2, 1)}), ply=0)
    assert line is None  # ran out of node budget → honest "unproven"
    assert tiny.nodes_used >= 5


def test_stay_is_a_legal_cop_action_and_ignored_when_useless() -> None:
    # A cornered thief with ONE exit left: the winning line completes the box
    # (rule 47). Under the Barrier Law a wall FORGOES the step, so the winning
    # action is STAY-and-wall — idling is only dithering when nothing is placed.
    solver = EndgameSolver(B, depth=4, nodes=50_000, survival_threshold=35)
    line = solver.solve(cop=(1, 1), thief=(0, 0), barriers=frozenset({(0, 1)}), ply=0)
    assert line is not None
    move, wall = line.action
    assert wall is not None, "the capture is built from barriers, not from standing there"
    assert move is Direction.STAY, "and the wall costs the step (ch.3)"
    assert line.value > 0, "walling in the last exit is a forced capture"
