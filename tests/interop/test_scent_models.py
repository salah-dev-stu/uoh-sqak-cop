"""Named scent models (SPEC §7) — declare one, and emit exactly what it says.

The smell grid is the one per-step observable no commitment covers, so a model
mismatch cannot void a game — it just quietly degrades the opponent's ability to
find us, which is a way of winning we do not want. Both registered models are
implemented and pinned to the league's own fixtures.

Vectors vendored (MIT) from github.com/Imreec/copthief-league-protocol.
"""

from __future__ import annotations

import json
from pathlib import Path

from cipherchase.domain.canonical import canonical_json, sha256_hex
from cipherchase.domain.smell import SmellField

VECTORS = Path(__file__).parent / "league_vectors"
CORE = json.loads((VECTORS / "pheromone.json").read_text())
REGISTRY = json.loads((VECTORS / "locked_model.json").read_text())["registered"]


def _doc(family: str, name: str) -> dict:
    return next(e["doc"] for e in REGISTRY
                if e["doc"]["family"] == family and e["doc"]["name"] == name)


def _subtractive(board: int, params: dict) -> SmellField:
    return SmellField(
        board, grid_size=params["field_size"], center_intensity=params["emit_intensity"],
        decay=params["decay_per_step"], model="subtractive_chebyshev_v1")


def test_subtractive_emit_matches_the_league_core_fixture() -> None:
    case = CORE["emit"][0] if isinstance(CORE["emit"], list) else CORE["emit"]
    field = _subtractive(case["board_size"],
                         {"field_size": case["grid_size"],
                          "emit_intensity": case["intensity"], "decay_per_step": 0.1})
    field.deposit(tuple(case["center"]))
    assert field.snapshot() == {k: v for k, v in case["field"].items() if v > 0}


def test_subtractive_decay_subtracts_and_only_positive_values_cross_the_wire() -> None:
    case = CORE["decay"][0] if isinstance(CORE["decay"], list) else CORE["decay"]
    field = _subtractive(7, {"field_size": 5, "emit_intensity": 0.9,
                             "decay_per_step": case["decay"]})
    field.load(case["before"])
    field.decay_all()
    assert field.snapshot() == {k: v for k, v in case["after"].items() if v > 0}


def test_a_value_decayed_to_zero_leaves_the_wire_entirely() -> None:
    field = _subtractive(7, {"field_size": 5, "emit_intensity": 0.9, "decay_per_step": 0.1})
    field.load({"0,0": 0.1, "1,1": 0.3})
    field.decay_all()
    assert field.snapshot() == {"1,1": 0.2}


def test_our_declared_registration_hash_is_the_leagues() -> None:
    # Both peers declare `scent_model_sha256`; equal hashes mean equal physics.
    # Recomputed from the registry doc, never copied from a message.
    doc = _doc("scent_model", "subtractive_chebyshev_v1")
    assert sha256_hex(canonical_json(doc)) == (
        "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4")


def test_the_default_model_is_unchanged_and_still_multiplicative() -> None:
    field = SmellField(7, grid_size=5, center_intensity=0.9, decay=0.1, falloff=0.7)
    field.deposit((3, 3))
    snap = field.snapshot()
    assert snap["3,3"] == 0.9
    assert round(snap["3,4"], 3) == 0.63  # 0.9 * 0.7**1 — our own profile


def test_the_live_runtime_emits_the_model_its_config_names() -> None:
    # A match agrees one model; our peer must actually emit it, not just be able to.
    from fakes.fake_transport import make_pair

    from cipherchase.peer.runtime import PeerRuntime
    from cipherchase.shared.config import ConfigManager
    cfg = ConfigManager.load(Path(__file__).resolve().parents[2] / "config" / "thief")
    cfg.private["scent"] = {"model": "subtractive_chebyshev_v1"}
    a, _b = make_pair()
    rt = PeerRuntime(role="thief", cfg=cfg, transport=a, sub_game_number=1)
    rt.my_smell.deposit((3, 3))
    assert rt.my_smell.snapshot()["2,3"] == 0.6  # subtractive ring, not 0.63


def test_our_computed_declaration_equals_the_league_registry_hash() -> None:
    # We COMPUTE what we declare from the params we implement. If our physics
    # and the league's registration ever drift apart, this fails here rather
    # than refusing a peer on match day.
    from cipherchase.domain.model_registry import declared_hash
    assert declared_hash("subtractive_chebyshev_v1") == sha256_hex(
        canonical_json(_doc("scent_model", "subtractive_chebyshev_v1")))
    assert declared_hash("belief") == sha256_hex(canonical_json(_doc("info_mode", "belief")))
    assert declared_hash("multiplicative_cheb"), "our own profile is declarable too"
    assert declared_hash("no_such_model") == "", "declare nothing rather than something wrong"


def test_the_registration_doc_is_readable_so_a_peer_can_diff_it() -> None:
    # We publish the doc, not just its digest — an opponent who hashes to
    # something else can see exactly which parameter we disagree on.
    from cipherchase.domain.model_registry import registration
    doc = registration("subtractive_chebyshev_v1")
    assert doc == _doc("scent_model", "subtractive_chebyshev_v1")
    assert registration("no_such_model") is None
