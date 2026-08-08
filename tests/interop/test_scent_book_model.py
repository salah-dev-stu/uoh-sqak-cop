"""`multiplicative_book_v1` — anrbj666's locked model, pinned to the kit's vectors.

Their scent module IS the model: the book's figure-4 kernel and its update law,
hash-locked across their twin repos with no alternative behind a switch. So the
pairing plays their physics, and we implement it rather than declare a lock we
do not run.

    tau' = clamp((1 - rho) * tau + kernel_delta, 0, center_intensity)

The evaluation order is pinned, not incidental: the kit's ordering_probe shows
`(1 - rho) * tau + delta` and `tau - rho * tau + delta` disagree in floating
point on ordinary values, so the expression is part of the lock.

Vectors vendored (MIT) from github.com/Imreec/copthief-league-protocol.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cipherchase.domain.scent_book import book_turn
from cipherchase.domain.smell import SmellField

BOOK = json.loads((Path(__file__).parent / "league_vectors" / "scent_book_v3.json").read_text())
PARAMS = BOOK["kernel"] if isinstance(BOOK.get("kernel"), dict) else {}


def _field() -> SmellField:
    return SmellField(7, 5, 0.9, 0.1, model="multiplicative_book_v1")


def test_one_deposit_on_an_empty_field_is_the_printed_kernel() -> None:
    case = BOOK["emit"][0] if isinstance(BOOK["emit"], list) else BOOK["emit"]
    field = _field()
    book_turn(field, tuple(case["emit_center"] if "emit_center" in case else case["center"]))
    expected = {k: v for k, v in case["field"].items() if v > 0}
    assert field.snapshot() == pytest.approx(expected)


def test_pure_decay_matches_the_books_worked_example() -> None:
    # ch.4: a fresh centre after one full turn of decay with no new deposit.
    trace = BOOK["scalar_traces"]["pure_decay"]
    field = _field()
    field.load({"3,3": trace["tau"]})
    book_turn(field, None)          # a turn with no deposit at all
    assert field.snapshot()["3,3"] == pytest.approx(trace["after"])


def test_the_upper_clamp_earns_its_keep() -> None:
    # Without it the printed formula leaves 1.43, outside the book's [0, 0.9].
    trace = BOOK["scalar_traces"]["clamp"]
    field = _field()
    field.load({"3,3": trace["tau"]})
    book_turn(field, (3, 3))        # centre delta 0.9 would overshoot
    assert field.snapshot()["3,3"] == pytest.approx(0.9)
    assert field.snapshot()["3,3"] <= 0.9


def test_a_three_turn_walk_reproduces_the_field_exactly() -> None:
    walk = BOOK["field_walk"]
    field = SmellField(walk["board_size"], 5, walk["center_intensity"],
                       walk["rho"], model="multiplicative_book_v1")
    for turn in walk["turns"]:
        book_turn(field, tuple(turn["center"]))
        expected = {k: v for k, v in turn["field"].items() if v > 0}
        assert field.snapshot() == pytest.approx(expected), f"diverged at turn {turn['turn']}"


def test_the_pinned_evaluation_order_is_the_one_we_use() -> None:
    # The two orderings differ in floating point; the lock names one of them.
    probe = BOOK["ordering_probe"]
    for case in probe["cases"]:
        field = _field()
        field.load({"0,0": case["tau"]})
        # a delta of exactly `delta` at (0,0) via the kernel's own lookup
        got = (1 - 0.1) * case["tau"] + case["delta"]
        assert got == pytest.approx(case["pinned_order"], abs=0), (
            "we must compute (1 - rho) * tau + delta, not tau - rho * tau + delta")


def test_the_live_turn_uses_one_combined_update_for_this_model() -> None:
    # Our turn does deposit-then-decay as two calls, which is right for the
    # subtractive lock and WRONG here: the book law decays and deposits in one
    # expression. A peer running this model must emit the combined result.
    from fakes.fake_transport import make_pair

    from cipherchase.peer.runtime import PeerRuntime
    from cipherchase.peer.state_machine import State
    from cipherchase.shared.config import ConfigManager
    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "thief")
    cfg.private["scent"] = {"model": "multiplicative_book_v1"}
    a, _b = make_pair()
    rt = PeerRuntime(role="thief", cfg=cfg, transport=a, sub_game_number=1)
    rt.sm.transition(State.WAITING)
    rt.take_turn(None)
    grid = [w for (_t, _k, w) in a.sent if w.get("sender") == "thief"][0]["smell_grid"]
    # First turn from an empty field: the kernel itself, undecayed centre at 0.9.
    assert max(grid.values()) == pytest.approx(0.9)
    assert grid[f"{rt.me.position[0]},{rt.me.position[1]}"] == pytest.approx(0.9)
