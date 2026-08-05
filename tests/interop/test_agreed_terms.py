"""The constitution we shake hands on is the one we agreed (F14).

Terms are edited per match (`setting`, `num_games`, …) and an accidental edit is
invisible until a handshake refuses — or worse, until two peers derive different
`game_uid`s, play a whole series, and discover the split when their reports fail
to join. These pin the shipped bytes; changing them should be a deliberate,
mutual act that updates this fixture in the same commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cipherchase.domain.canonical import canonical_json
from cipherchase.domain.game_ids import derive_game_ids
from cipherchase.peer.terms import terms_from_config
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"

# Byte-for-byte as signed: one line, sorted keys, no whitespace. Cross-checked
# against team imreeyal's independently produced canonical form (2026-08-05).
AGREED = (
    '{"axis_origin_corner":"top-left","axis_start_index":0,"barriers_max":14,'
    '"board_size":7,"cop_start":[0,0],"decay_per_step":0.1,"emit_intensity":0.9,'
    '"hint_max_words":15,"max_steps":35,"min_center_intensity":0.5,"num_games":6,'
    '"setting":"New York","smell_grid_size":5,"thief_start":[3,3]}'
)


@pytest.mark.parametrize("role", ["police", "thief"])
def test_both_role_configs_sign_the_same_agreed_terms(role: str) -> None:
    assert canonical_json(terms_from_config(ConfigManager.load(CONFIG / role))) == AGREED


def test_the_pairing_derives_the_uid_the_opponent_derived() -> None:
    # Exchanged in writing before the match: a mismatch here is a terms mismatch,
    # and finding it in CI costs nothing where finding it at report-join costs
    # the window.
    terms = terms_from_config(ConfigManager.load(CONFIG / "police"))
    game_id, game_uid = derive_game_ids(terms, "uoh-sqak", "imreeyal")
    assert game_id == "imreeyal-vs-uoh-sqak"
    assert game_uid == "639db017-607b-1bce-9fae-f5948766a795"
