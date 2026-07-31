"""P1 agreement layer (PRD_league_runtime §2.1): terms, signature, ids, handshake."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest

from cipherchase.domain.canonical import canonical_json
from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.game_ids import derive_game_ids
from cipherchase.domain.negotiation import Negotiation
from cipherchase.exceptions import HandshakeError
from cipherchase.peer.terms import identity_from_config, terms_from_config
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
TERMS_KEYS = {
    "board_size", "smell_grid_size", "decay_per_step", "emit_intensity",
    "min_center_intensity", "max_steps", "barriers_max", "setting",
    "hint_max_words", "axis_origin_corner", "axis_start_index",
    "thief_start", "cop_start", "num_games",
}


def _cfg() -> ConfigManager:
    return ConfigManager.load(CONFIG / "police")


def test_terms_exact_reference_keyset_and_values() -> None:
    terms = terms_from_config(_cfg())
    assert set(terms) == TERMS_KEYS
    assert terms["board_size"] == 7 and terms["barriers_max"] == 14
    assert terms["max_steps"] == 35 and terms["thief_start"] == [3, 3]


def test_identity_carries_group_and_spec() -> None:
    identity = identity_from_config(_cfg())
    for key in ("group_id", "group_name", "members", "repos", "mcp_servers", "llm_model", "spec"):
        assert key in identity


def test_signed_agreement_shape_and_signature() -> None:
    neg = Negotiation(terms_from_config(_cfg()), identity_from_config(_cfg()))
    signed = neg.signed()
    assert set(signed) == {"terms", "nonce", "signature", "identity"}
    CommitReveal.verify(signed["terms"], signed["nonce"], signed["signature"])  # no raise


def test_verify_peer_accepts_equal_terms_ignores_identity() -> None:
    mine = Negotiation(terms_from_config(_cfg()), identity_from_config(_cfg()))
    theirs = Negotiation(terms_from_config(_cfg()), {"group_id": "uoh-other"})
    mine.verify_peer(theirs.signed())  # different identity, same terms → fine


def test_verify_peer_rejects_terms_mismatch_and_bad_signature() -> None:
    mine = Negotiation(terms_from_config(_cfg()), {})
    other_terms = dict(terms_from_config(_cfg()), board_size=9)
    with pytest.raises(HandshakeError):
        mine.verify_peer(Negotiation(other_terms, {}).signed())
    forged = mine.signed()
    forged["signature"] = "00" * 32
    with pytest.raises(HandshakeError):
        mine.verify_peer(forged)


def test_derive_game_ids_reference_formula_and_symmetry() -> None:
    terms = terms_from_config(_cfg())
    gid, guid = derive_game_ids(terms, "uoh-zzz", "uoh-aaa")
    assert gid == "uoh-aaa-vs-uoh-zzz"  # sorted min-vs-max
    seed = canonical_json(terms) + "|uoh-aaa|uoh-zzz"
    expected = str(uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]))
    assert guid == expected
    assert derive_game_ids(terms, "uoh-aaa", "uoh-zzz") == (gid, guid)  # order-independent


def test_identity_advertises_the_public_url_when_configured() -> None:
    # najamjad warm-up finding (rule 49): the declaration's mcp_servers carried
    # 127.0.0.1 — the lecturer-facing address must be the public tunnel when set.
    cfg = ConfigManager.load(CONFIG / "thief")
    assert "127.0.0.1" in identity_from_config(cfg)["mcp_servers"]["thief"]  # local fallback
    cfg.private["network"]["public_url"] = "https://example.ngrok-free.app/mcp"
    assert identity_from_config(cfg)["mcp_servers"] == {
        "thief": "https://example.ngrok-free.app/mcp"}
