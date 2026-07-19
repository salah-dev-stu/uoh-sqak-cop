"""Interop tripwire: the REFERENCE peer's strict parser accepts our wire bytes.

Imports the lecturer's actual ``police_thief`` package (if present next to the
repo) and feeds it every message our runtime emits. Runs on every commit when
the reference is available; skipped cleanly elsewhere (CI without the repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fakes.fake_transport import make_pair

from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.state_machine import State
from cipherchase.shared.config import ConfigManager

REFERENCE_SRC = Path(__file__).resolve().parents[3] / "reference-repo" / "src"
pytestmark = pytest.mark.skipif(
    not REFERENCE_SRC.exists(), reason="reference repo not present"
)
CONFIG = Path(__file__).resolve().parents[2] / "config"


def _reference_module(name: str):
    if str(REFERENCE_SRC) not in sys.path:
        sys.path.insert(0, str(REFERENCE_SRC))
    return __import__(f"police_thief.domain.{name}", fromlist=["*"])


def _emit_our_messages() -> list[tuple[str, str, dict]]:
    cfg = ConfigManager.load(CONFIG / "thief")
    a, _b = make_pair()
    rt = PeerRuntime(role="thief", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    rt.take_turn({"claim": [0, 0], "caught": False})
    rt.handle({"step": 3, "sender": "police", "capture_claim": list(rt.me.position)})
    return list(a.sent)


def test_reference_strict_parser_accepts_every_turn_we_send() -> None:
    protocol = _reference_module("protocol")
    for tool, _arg, wire in _emit_our_messages():
        if tool == "receive_turn":
            msg = protocol.TurnMessage.from_dict(wire)  # strict cls(**data) — no extras allowed
            assert msg.commit and msg.timestamp


def test_reference_crypto_verifies_our_sealed_records() -> None:
    crypto = _reference_module("crypto")
    cfg = ConfigManager.load(CONFIG / "police")
    a, _b = make_pair()
    rt = PeerRuntime(role="police", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    for record in rt.book.records():
        # the reference auditor re-hashes our records verbatim — byte-identical formula
        crypto.CommitReveal.verify(record["payload"], record["nonce"], record["commit"])


def test_reference_negotiation_shape_matches_ours() -> None:
    from cipherchase.domain.negotiation import Negotiation
    from cipherchase.peer.terms import identity_from_config, terms_from_config

    cfg = ConfigManager.load(CONFIG / "police")
    signed = Negotiation(terms_from_config(cfg), identity_from_config(cfg)).signed()
    negotiation = _reference_module("negotiation")
    peer_cls = negotiation.Negotiation
    theirs = peer_cls(terms=signed["terms"], identity={"group_id": "ref"})
    theirs.verify_peer(signed)  # the reference verifier accepts our signed agreement
