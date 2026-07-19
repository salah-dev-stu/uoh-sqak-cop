"""PeerRuntime — one agent, one sub-game, live (PRD_league_runtime §3.1, F1/F9).

Negotiate → Step-0 spec record → (thief) first move → poll/process/respond loop
with deadline + watchdog (silent peer = OUR technical win, never a hang) →
audit exchange via ``summary.finish``.
"""

from __future__ import annotations

import random
import time
from typing import Any

from cipherchase.domain.board import Board
from cipherchase.domain.hint_belief import HonestyTracker
from cipherchase.domain.own_state import OwnState
from cipherchase.domain.scent_decode import ScentDecoder
from cipherchase.domain.smell import SmellField
from cipherchase.infra.llm_provider import TalkContext, TemplateProvider, build_provider
from cipherchase.peer import handshake, summary, turn_handler, turn_sender
from cipherchase.peer.deadline import Deadline
from cipherchase.peer.sealing import SealBook, sealed_spec_record
from cipherchase.peer.state_machine import State, StateMachine
from cipherchase.peer.watchdog import Watchdog
from cipherchase.strategy.factory import load_brain
from cipherchase.strategy.trash_talk import TrashTalk


class PeerRuntime:
    def __init__(self, *, role: str, cfg: Any, transport: Any, sub_game_number: int,
                 gate: Any = None, now: Any = None) -> None:
        ba = cfg.shared["board_and_agents"]
        mb = cfg.shared["movement_and_barriers"]
        ph = cfg.shared["pheromones"]
        self.role, self.cfg, self.transport = role, cfg, transport
        self.opp_role = "thief" if role == "police" else "police"
        self.sub_game_number = sub_game_number
        self.board = Board(ba["board_size"])
        strat = {**cfg.private["strategy"], "max_barriers": mb["max_barriers"]}
        rng = random.Random(cfg.private["play"]["seed"] + sub_game_number)
        spec = strat["police_class"] if role == "police" else strat["thief_class"]
        self.brain = load_brain(spec, self.board, params=strat, rng=rng)
        start = ba["cop_start"] if role == "police" else ba["thief_start"]
        self.me = OwnState(role, tuple(start))
        bel = cfg.private["belief"]
        self.decoder = ScentDecoder(self.board.size, bel["smell_trust"], bel["alpha"], ph)
        self.belief = self.decoder.grid
        self.honesty = HonestyTracker()  # Bayesian trust in the opponent's words (F6)
        self.bluff_weight = float(strat.get("bluff_weight", 0.0))
        self.last_claim: Any = None
        self.my_smell = SmellField(
            self.board.size, ph["grid_size"], ph["center_intensity"], ph["decay"],
            ph["falloff"], min_center=ph["min_center_intensity"],
            absorb_gain=ph["absorb_gain"],
        )
        tt = cfg.private["trash_talk"]
        self.talk = TrashTalk(
            build_provider({**cfg.private.get("llm", {}), **tt}, gate=gate), TemplateProvider(),
            every_n_steps=tt["every_n_steps"], lie_probability=tt["lie_probability"], rng=rng,
        )
        self.max_steps = mb["survival_threshold"]
        self.barriers_max = mb["max_barriers"]
        self.hint_max_words = cfg.shared["world"]["hint_max_words"]
        self.book, self.history = SealBook(), []
        self.barriers: frozenset = frozenset()
        self.step_number, self.last_seen_step = 0, 0
        self.game_id, self.game_uid, self.peer_identity = "", "", {}
        self.sm = StateMachine(State.HANDSHAKE)
        self.now = now or time.monotonic

    def talk_for(self, step: int) -> tuple[str, str]:
        intent = self.talk.choose_intent()
        hint = self.talk.maybe_generate(TalkContext(role=self.role, step=step, intent=intent))
        return (intent if hint else "truth"), hint

    def take_turn(self, claim_response: dict | None) -> tuple[str, str] | None:
        self.sm.transition(State.COMPUTING)
        result = turn_sender.take_turn(self, claim_response)
        self.sm.transition(State.COMMITTING)
        self.sm.transition(State.WAITING)
        return result

    def handle(self, wire: dict) -> turn_handler.Incoming:
        return turn_handler.process(self, wire)

    def run(self) -> dict[str, Any]:
        try:
            return self._run()
        except Exception as exc:  # crash boundary (F9): a result, never a hung port
            return summary.finish(self, ("error", "-"), note=repr(exc))

    def _run(self) -> dict[str, Any]:
        net = self.cfg.network
        try:
            handshake.negotiate(self)
        except Exception as exc:
            return summary.finish(self, ("handshake_failed", "-"), note=str(exc))
        self.sm.transition(State.WAITING)
        sealed_spec_record(self.book, self.cfg, self.sub_game_number)
        result = self.take_turn(None) if self.role == "thief" else None
        deadline = Deadline(net["turn_timeout_seconds"], self.now)
        watchdog = Watchdog(net["turn_timeout_seconds"], self.now)
        while result is None:
            if deadline.expired() or watchdog.expired():
                result = ("timeout", self.role)  # silent peer → our technical win
                break
            control = self.transport.poll_control_or_none(0.0)
            if control and control.get("kind") == "quit":
                result = ("opponent_quit", self.role)
                break
            wire = self.transport.poll_turn_or_none(net["poll_interval_seconds"])
            if wire is None:
                continue
            outcome = self.handle(wire)
            if outcome.duplicate or outcome.malformed:
                continue  # neither resets the deadline
            deadline.reset()
            watchdog.beat()
            result = outcome.result or self.take_turn(outcome.claim_response)
        return summary.finish(self, result)
