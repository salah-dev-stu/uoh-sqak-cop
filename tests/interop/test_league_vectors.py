"""Cross-team byte conformance (F3/F14) — the league interop kit's CORE vectors.

The audit is mutual: at end-of-game the OPPONENT re-hashes our log with THEIR
code. Two honest implementations whose canonical JSON differs by one escaped
character each conclude the other cheated, and the rules score that 0/0 for
both. These fixtures pin the shared constructions so that failure mode is
caught here, in CI, instead of in a counted match.

Vectors vendored (MIT, see LICENSE-copthief-league-protocol) from the
Cop-Thief League Interop Kit — github.com/Imreec/copthief-league-protocol —
published by teams ImreEyal + anrbj666. Our own crypto is unchanged: these
assert that what we already ship reproduces the league fixtures exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cipherchase.domain.canonical import canonical_json, sha256_hex
from cipherchase.domain.crypto import CommitReveal
from cipherchase.domain.game_ids import derive_game_ids

VECTORS = Path(__file__).parent / "league_vectors"


def _load(name: str) -> list[dict]:
    return json.loads((VECTORS / f"{name}.json").read_text())["vectors"]


@pytest.mark.parametrize("case", _load("canonical_json"))
def test_our_canonical_json_matches_the_league_fixture(case) -> None:
    text = canonical_json(case["object"])
    assert text == case["canonical"], case.get("note", "")
    assert sha256_hex(text) == case["sha256"]


@pytest.mark.parametrize("case", _load("commit_reveal"))
def test_our_commit_seal_matches_the_league_fixture(case) -> None:
    # sha256(canonical_json(payload) + "|" + nonce) — the opponent recomputes
    # exactly this over our revealed log at audit time.
    assert CommitReveal.commit_of(case["payload"], case["nonce"]) == case["commit"]


@pytest.mark.parametrize("case", _load("terms_signature"))
def test_our_agreement_signature_matches_the_league_fixture(case) -> None:
    # Same construction as a commit, over the agreed terms: the pre-game gate.
    assert CommitReveal.commit_of(case["terms"], case["nonce"]) == case["signature"]


@pytest.mark.parametrize("case", _load("game_uid"))
def test_both_peers_derive_the_same_ids_without_a_round_trip(case) -> None:
    game_id, game_uid = derive_game_ids(case["terms"], case["group_a"], case["group_b"])
    assert game_uid == case["game_uid"], case.get("note", "")
    assert game_id == case["game_id"]


def test_reversing_the_group_pair_changes_nothing() -> None:
    # Both sides sort the pair, so A-vs-B and B-vs-A agree with no negotiation.
    for c in _load("game_uid"):
        forward = derive_game_ids(c["terms"], c["group_a"], c["group_b"])
        backward = derive_game_ids(c["terms"], c["group_b"], c["group_a"])
        assert forward == backward
