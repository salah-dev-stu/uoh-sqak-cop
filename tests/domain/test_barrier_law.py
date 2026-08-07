"""The Barrier Law (book ch.3): a wall costs the cop its step that turn.

    בתור שבו השוטר מוותר על תנועה הוא רשאי להציב מחסום בכל תא שבמרחק צעד אחד ממנו
    "in a turn in which the cop FORGOES MOVEMENT, he may place a barrier in any
    cell within one step of him — the cell he stands on, or one of the four
    orthogonal neighbours"

Stated twice in chapter 3, once in the body and once in the boxed rule of the
same name, and implemented by the reference as an exclusive MoveType:
MOVE | BARRIER | HOLD, "the three legal actions an agent may take in a turn".

We were taking two: our cop stepped AND walled on 13 of 14 turns. imreeyal found
it in the messages we had sent them. An extra action every turn against an
opponent taking one is the whole of the asymmetry the law exists to price.
"""

from __future__ import annotations

from cipherchase.constants import Direction
from cipherchase.domain.brains import Decision, under_barrier_law


def test_placing_a_wall_forgoes_the_step() -> None:
    walled = under_barrier_law(Decision(direction=Direction.N, barrier_cell=(2, 3)))
    assert walled.direction is Direction.STAY, "a wall costs the move"
    assert walled.barrier_cell == (2, 3), "and the wall still goes down"


def test_a_plain_move_is_untouched() -> None:
    moved = under_barrier_law(Decision(direction=Direction.E))
    assert moved.direction is Direction.E and moved.barrier_cell is None


def test_already_forgone_movement_is_untouched() -> None:
    held = under_barrier_law(Decision(direction=Direction.STAY, barrier_cell=(1, 1)))
    assert held.direction is Direction.STAY and held.barrier_cell == (1, 1)


def test_the_law_preserves_everything_else_about_the_decision() -> None:
    # The sealed payload commits to intent and hint; the law must not disturb them.
    d = Decision(direction=Direction.W, intent="lie", hint="heading north",
                 barrier_cell=(0, 1), reasoning="seal the corner")
    out = under_barrier_law(d)
    assert (out.intent, out.hint, out.reasoning) == ("lie", "heading north", "seal the corner")


def test_no_brain_can_take_two_actions_in_one_turn() -> None:
    # Enforced at the one choke point every strategy passes through, so a brain
    # that returns both a step and a wall still only spends one action.
    import random

    from cipherchase.domain.board import Board
    from cipherchase.domain.brains import BrainBase
    from cipherchase.domain.own_state import OwnState

    class Greedy(BrainBase):
        role = "police"
        def _pick_move(self, state, belief, barriers): return Direction.N
        def _pick_barrier(self, state, belief, barriers): return (2, 3)

    brain = Greedy(Board(7), params={}, rng=random.Random(0))
    out = brain.decide(OwnState("police", (3, 3)), None, frozenset())
    assert out.direction is Direction.STAY and out.barrier_cell == (2, 3)


def test_on_the_wire_a_walling_cop_does_not_move() -> None:
    # The observable form of the law, checked where the opponent sees it: the
    # turn that carries `barrier_placed` must leave the cop where it started.
    # imreeyal caught our violation in exactly this data — a wall on 13 of 14
    # turns while the cop still walked (0,0) to (0,4).
    from pathlib import Path

    from fakes.fake_transport import make_pair

    from cipherchase.peer.runtime import PeerRuntime
    from cipherchase.peer.state_machine import State
    from cipherchase.shared.config import ConfigManager

    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "police")
    cfg.private["strategy"] = {**cfg.private["strategy"],
                               "min_gain": 1, "apex_barrier_cost": 0.0}
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    walled = False
    for _ in range(6):
        before = rt.me.position
        rt.take_turn(None)
        wire = [w for (_t, _k, w) in a.sent if w.get("sender") == "police"][-1]
        if wire.get("barrier_placed"):
            walled = True
            assert rt.me.position == before, "a wall costs the step — the cop must not move"
    assert walled, "this fixture must produce at least one barrier"
