"""Config-driven cop-vs-thief self-match engine.

Wires the whole stack (board/rules/scoring, brains, belief, scent, crypto) into
one deterministic game — the offline-provable path (no live peer, ADR-010).
The thief observes the cop each turn (demo simplification); every move is
sealed so the log audits clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cipherchase.constants import Cell, Outcome
from cipherchase.domain import rules
from cipherchase.domain.belief import BeliefGrid
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import can_place_barrier
from cipherchase.domain.scoring import Scoring
from cipherchase.domain.smell import SmellField
from cipherchase.peer.sealing import SealBook, move_payload
from cipherchase.strategy.factory import load_brain


@dataclass
class GameResult:
    outcome: Outcome
    turns: int
    records: list[dict[str, Any]]
    scores: tuple[int, int]


def _cop_belief_of_thief(size: int, trust: float, smell: SmellField) -> BeliefGrid:
    belief = BeliefGrid(size, trust)
    belief.observe_smell(smell.snapshot())
    return belief


def _thief_belief_of_cop(size: int, trust: float, cop: Cell, peak: float) -> BeliefGrid:
    belief = BeliefGrid(size, trust)
    belief.observe_smell({f"{cop[0]},{cop[1]}": peak})
    return belief


def run_game(cfg: Any) -> GameResult:  # noqa: C901
    ba, mb, ph = (cfg.shared[k] for k in ("board_and_agents", "movement_and_barriers", "pheromones"))
    board = Board(ba["board_size"])
    strat, trust = cfg.private["strategy"], cfg.private["belief"]["smell_trust"]
    cop_brain = load_brain(strat["police_class"], board, params=strat)
    thief_brain = load_brain(strat["thief_class"], board, params=strat)
    cop, thief = OwnState("police", tuple(ba["cop_start"])), OwnState("thief", tuple(ba["thief_start"]))
    smell = SmellField(board.size, ph["grid_size"], ph["center_intensity"], ph["decay"], ph["falloff"])
    cop_book, thief_book, barriers = SealBook(), SealBook(), frozenset()
    outcome, turns = Outcome.SURVIVAL, 0
    for step in range(1, mb["max_moves"] + 1):
        turns = step
        smell.deposit(thief.position)
        smell.decay_all()
        cop_belief = _cop_belief_of_thief(board.size, trust, smell)
        decision = cop_brain.decide(cop, cop_belief, barriers)
        cop_book.seal(move_payload(step, cop, decision))
        target = board.step(cop.position, decision.direction, barriers)
        if (
            decision.barrier_cell
            and decision.barrier_cell != target
            and can_place_barrier(board, cop.position, decision.barrier_cell, barriers, mb["max_barriers"])
        ):
            barriers = barriers | {decision.barrier_cell}
        cop = cop.moved_to(target)
        if _terminal(board, cop, thief, barriers, step, mb) is Outcome.CAPTURE:
            outcome = Outcome.CAPTURE
            break
        thief_belief = _thief_belief_of_cop(board.size, trust, cop.position, ph["center_intensity"])
        thief_decision = thief_brain.decide(thief, thief_belief, barriers)
        thief_book.seal(move_payload(step, thief, thief_decision))
        thief = thief.moved_to(board.step(thief.position, thief_decision.direction, barriers))
        reached = _terminal(board, cop, thief, barriers, step, mb)
        if reached is not None:
            outcome = reached
            break
    scores = Scoring(cfg.shared["scoring"]).score(outcome)
    return GameResult(outcome, turns, cop_book.records() + thief_book.records(), scores)


def _terminal(
    board: Board, cop: OwnState, thief: OwnState, barriers: frozenset[Cell], step: int, mb: dict
) -> Outcome | None:
    return rules.outcome(
        board, cop.position, thief.position, barriers, step,
        survival_threshold=mb["survival_threshold"], require_cop_adjacent=mb["require_cop_adjacent"],
    )
