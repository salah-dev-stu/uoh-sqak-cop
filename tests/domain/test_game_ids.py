"""Deterministic shared game_uid + distinct per-peer game_id (FR-B, F11)."""

from __future__ import annotations

from cipherchase.domain.game_ids import game_id, game_uid

SHA = "deadbeef"


def test_game_uid_is_symmetric_across_peers() -> None:
    assert game_uid("uoh-sqak", "uoh-xyz", SHA) == game_uid("uoh-xyz", "uoh-sqak", SHA)


def test_game_uid_depends_on_config_signature() -> None:
    assert game_uid("uoh-sqak", "uoh-xyz", SHA) != game_uid("uoh-sqak", "uoh-xyz", "other")


def test_game_uid_is_deterministic() -> None:
    assert game_uid("a", "b", SHA) == game_uid("a", "b", SHA)


def test_game_id_shares_uid_but_differs_by_role() -> None:
    uid = game_uid("uoh-sqak", "uoh-xyz", SHA)
    cop = game_id("uoh-sqak", "police", uid)
    thief = game_id("uoh-sqak", "thief", uid)
    assert cop != thief
    assert uid[:8] in cop and uid[:8] in thief
