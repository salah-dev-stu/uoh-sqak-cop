"""Config-driven cop-vs-thief self-match engine (single source — viz hooks in).

Every knob comes from config; every move is sealed with the mover's REAL
decision-time barrier view (IH-1); bluff hints + committed intent fire from a
seeded rng (IH-5/IH-11); ``on_frame`` streams per-turn frames to instrumentation
(replay data, benchmarks) so no second engine exists (IH-19). BOTH sides now
see only legal information: each agent's belief comes from decoding the
opponent's broadcast scent field (WB §8 realism rule — matches the live runtime).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cipherchase.constants import Cell, Outcome
from cipherchase.domain import rules
from cipherchase.domain.board import Board
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.rules import can_place_barrier
from cipherchase.domain.scent_decode import ScentDecoder
from cipherchase.domain.scoring import Scoring
from cipherchase.domain.smell import SmellField
from cipherchase.infra.llm_provider import TalkContext, TemplateProvider, build_provider
from cipherchase.peer.sealing import SealBook, move_payload
from cipherchase.strategy.factory import load_brain
from cipherchase.strategy.trash_talk import TrashTalk

OnFrame = Callable[[dict[str, Any]], None]


@dataclass
class GameResult:
    outcome: Outcome
    turns: int
    records: list[dict[str, Any]]
    scores: tuple[int, int]


def _build_talk(cfg: Any, rng: random.Random, gate: Any) -> TrashTalk:
    tt = cfg.private["trash_talk"]
    provider = build_provider({**cfg.private.get("llm", {}), **tt}, gate=gate)
    return TrashTalk(
        provider, TemplateProvider(),
        every_n_steps=tt["every_n_steps"], lie_probability=tt["lie_probability"], rng=rng,
    )


def _talk_for(talk: TrashTalk, role: str, step: int) -> tuple[str, str]:
    intent = talk.choose_intent()
    hint = talk.maybe_generate(TalkContext(role=role, step=step, intent=intent))
    return (intent if hint else "truth"), hint


def _frame(step: int, cop: OwnState, thief: OwnState, barriers: frozenset[Cell],
           smell: SmellField, belief: Any, thief_belief: Any, hint: str,
           intent: str) -> dict[str, Any]:
    return {
        "turn": step, "cop": list(cop.position), "thief": list(thief.position),
        "barriers": sorted([list(b) for b in barriers]), "scent": smell.snapshot(),
        "belief": belief.as_matrix(),
        "thief_belief": thief_belief.as_matrix() if thief_belief else None,
        "hint": hint, "intent": intent,
    }


def run_game(cfg: Any, on_frame: OnFrame | None = None, gate: Any = None) -> GameResult:  # noqa: C901
    ba, mb, ph = (cfg.shared[k] for k in ("board_and_agents", "movement_and_barriers", "pheromones"))
    board = Board(ba["board_size"])
    strat = {**cfg.private["strategy"], "max_barriers": mb["max_barriers"]}
    bel = cfg.private["belief"]
    rng = random.Random(cfg.private["play"]["seed"])
    talk = _build_talk(cfg, rng, gate)
    cop_brain = load_brain(strat["police_class"], board, params=strat, rng=rng)
    thief_brain = load_brain(strat["thief_class"], board, params=strat, rng=rng)
    cop = OwnState("police", tuple(ba["cop_start"]))
    thief = OwnState("thief", tuple(ba["thief_start"]))
    smell = SmellField(
        board.size, ph["grid_size"], ph["center_intensity"], ph["decay"], ph["falloff"],
        min_center=ph["min_center_intensity"], absorb_gain=ph["absorb_gain"],
    )
    cop_smell = SmellField(
        board.size, ph["grid_size"], ph["center_intensity"], ph["decay"], ph["falloff"],
        min_center=ph["min_center_intensity"], absorb_gain=ph["absorb_gain"],
    )
    cop_decoder = ScentDecoder(board.size, bel["smell_trust"], bel["alpha"], ph)
    thief_decoder = ScentDecoder(board.size, bel["smell_trust"], bel["alpha"], ph)
    cop_book, thief_book = SealBook(), SealBook()
    barriers: frozenset[Cell] = frozenset()
    prev_thief_belief: Any = None
    outcome: Outcome | None = None
    turns = 0
    for step in range(1, mb["max_moves"] + 1):
        turns = step
        smell.decay_all()
        smell.deposit(thief.position)
        cop_belief = cop_decoder.update(smell.snapshot())
        intent, hint = _talk_for(talk, "police", step)
        if on_frame:
            on_frame(_frame(step, cop, thief, barriers, smell, cop_belief,
                            prev_thief_belief, hint, intent))
        decision = cop_brain.decide(cop, cop_belief, barriers)
        decision.intent, decision.hint = intent, hint
        cop_book.seal(move_payload(step, cop, decision))
        target = board.step(cop.position, decision.direction, barriers)
        q = decision.barrier_cell
        if q and q != target and can_place_barrier(board, cop.position, q, barriers, mb["max_barriers"]):
            barriers = barriers | {q}
            cop, thief = cop.with_barrier(q), thief.with_barrier(q)
        cop = cop.moved_to(target)
        if _terminal(board, cop, thief, barriers, step, mb) is Outcome.CAPTURE:
            outcome = Outcome.CAPTURE
            break
        cop_smell.decay_all()
        cop_smell.deposit(cop.position)
        thief_belief = thief_decoder.update(cop_smell.snapshot())  # legal info only
        prev_thief_belief = thief_belief
        t_intent, t_hint = _talk_for(talk, "thief", step)
        t_decision = thief_brain.decide(thief, thief_belief, barriers)
        t_decision.intent, t_decision.hint = t_intent, t_hint
        thief_book.seal(move_payload(step, thief, t_decision))
        thief = thief.moved_to(board.step(thief.position, t_decision.direction, barriers))
        reached = _terminal(board, cop, thief, barriers, step, mb)
        if reached is not None:
            outcome = reached
            break
    if outcome is None:
        outcome = Outcome.SURVIVAL if turns >= mb["survival_threshold"] else Outcome.TIE
    scores = Scoring(cfg.shared["scoring"]).score(outcome)
    return GameResult(outcome, turns, cop_book.records() + thief_book.records(), scores)


def _terminal(
    board: Board, cop: OwnState, thief: OwnState, barriers: frozenset[Cell], step: int, mb: dict
) -> Outcome | None:
    return rules.outcome(
        board, cop.position, thief.position, barriers, step,
        survival_threshold=mb["survival_threshold"], require_cop_adjacent=mb["require_cop_adjacent"],
    )
