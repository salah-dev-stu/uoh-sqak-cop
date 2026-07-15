"""Milestone S4: scent updates each step, belief follows, game runs at 0 tokens.

Also the F8 hard gate (T196): a full heuristic game never calls the LLM.
"""

from __future__ import annotations

import random
from unittest.mock import patch

from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.smell import SmellField
from cipherchase.infra.llm_provider import TalkContext, TemplateProvider, build_provider
from cipherchase.strategy.police_heuristic import PoliceBrain
from cipherchase.strategy.thief_heuristic import ThiefBrain
from cipherchase.strategy.trash_talk import TrashTalk

EMPTY: frozenset[tuple[int, int]] = frozenset()


def _smell() -> SmellField:
    return SmellField(7, grid_size=5, center_intensity=0.9, decay=0.1, falloff=0.7)


def test_belief_follows_the_scent_each_step() -> None:
    smell, belief = _smell(), BeliefGrid(7, smell_trust=4.0)
    smell.deposit((5, 5))
    belief.observe_smell(smell.snapshot())
    assert belief.most_likely() == (5, 5)


def test_full_mini_game_runs_at_zero_tokens_with_algorithmic_moves() -> None:
    board = Board(7)
    cop_brain, thief_brain = PoliceBrain(board), ThiefBrain(board)
    cop_belief, thief_belief = BeliefGrid(7, smell_trust=4.0), BeliefGrid(7, smell_trust=4.0)
    smell = _smell()
    talk = TrashTalk(
        build_provider({"provider": "template"}), TemplateProvider(),
        every_n_steps=2, rng=random.Random(0),
    )
    cop, thief = OwnState("police", (0, 0)), OwnState("thief", (6, 6))

    with patch("subprocess.run") as run:
        for step in range(1, 6):
            smell.deposit(thief.position)
            smell.decay_all()
            cop_belief.observe_smell(smell.snapshot())
            cop = cop.moved_to(board.step(cop.position, cop_brain.decide(cop, cop_belief, EMPTY).direction, EMPTY))
            thief = thief.moved_to(board.step(thief.position, thief_brain.decide(thief, thief_belief, EMPTY).direction, EMPTY))
            talk.maybe_generate(TalkContext("police", step, intent=talk.choose_intent()))

    assert not run.called  # zero LLM tokens
    assert cop.position != (0, 0)  # cop actually pursued
