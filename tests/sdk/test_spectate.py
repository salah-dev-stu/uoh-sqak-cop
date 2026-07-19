"""Spectate stream (SH-2/4): own-knowledge frames only — never opponent truth."""

from __future__ import annotations

import json
from pathlib import Path

from fakes.fake_transport import make_pair

from cipherchase.domain.protocol import TurnMessage
from cipherchase.peer.runtime import PeerRuntime
from cipherchase.peer.sealing import sealed_spec_record
from cipherchase.sdk.spectate import JsonlListener, build_frame
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
_KEYS = {"spectate_schema", "turn", "role", "phase", "me", "belief", "known_barriers",
         "last_hint", "last_intent", "claims", "commit8", "sub_game", "outcome", "ts"}


def _rt(role="police"):
    a, _b = make_pair()
    rt = PeerRuntime(role=role, cfg=ConfigManager.load(CONFIG / role),
                     transport=a, sub_game_number=3)
    sealed_spec_record(rt.book, rt.cfg, sub_game_number=3)  # give it one sealed record
    return rt


def test_frame_has_every_key_and_a_seven_by_seven_belief() -> None:
    f = build_frame(_rt(), "sent")
    assert set(f) == _KEYS
    assert f["spectate_schema"] == 1
    assert len(f["belief"]) == 7 and all(len(row) == 7 for row in f["belief"])
    assert len(f["commit8"]) == 8
    assert f["me"] == list(_rt().me.position)
    assert f["sub_game"] == 3 and f["role"] == "police"
    assert f["last_intent"] is None  # own intent is sealed, never streamed


def test_received_frame_carries_claims_but_no_opponent_position() -> None:
    rt = _rt("police")
    wire = TurnMessage(step=1, sender="thief", hint="north",
                       capture_claim=[2, 2]).to_dict()
    f = build_frame(rt, "received", wire)
    assert f["phase"] == "received"
    assert f["claims"]["capture_claim"] == [2, 2]  # a claim is not ground truth
    assert f["last_hint"] == "north"


def test_outcome_frame_carries_the_verdict() -> None:
    f = build_frame(_rt(), "ended", None, outcome={"result": "capture", "winner": "police"})
    assert f["outcome"] == {"result": "capture", "winner": "police"}


def test_jsonl_listener_appends_valid_lines_and_readers_skip_a_torn_tail(tmp_path) -> None:
    path = tmp_path / "spool.jsonl"
    listener = JsonlListener(path)
    listener(build_frame(_rt(), "sent"))
    listener(build_frame(_rt(), "sent"))
    with path.open("a") as fh:
        fh.write('{"partial": ')  # a torn final line (writer mid-flush)
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # tolerate the torn tail
    assert len(rows) == 2 and all(r["spectate_schema"] == 1 for r in rows)
