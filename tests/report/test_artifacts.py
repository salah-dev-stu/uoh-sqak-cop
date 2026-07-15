"""The 4 signed JSON artifact builders (FR-G1, F11)."""

from __future__ import annotations

from cipherchase.report import artifacts

COMMON = {"game_id": "uoh-sqak-police-abc", "game_uid": "abc123", "generated_at": "2026-08-01T00:00:00Z"}


def test_declaration_artifact_shape() -> None:
    art = artifacts.build_declaration(
        **COMMON, groups=["uoh-sqak", "uoh-xyz"], num_sub_games=6, max_tokens=200000, links={}
    )
    assert art["_schema"] == "declaration"
    assert art["timezone"] == "Asia/Jerusalem"
    assert art["num_sub_games"] == 6


def test_config_artifact_carries_sha_and_sub_game() -> None:
    art = artifacts.build_config(
        **COMMON, sub_game=1, shared_config={"board_size": 7}, config_sha256="deadbeef", links={}
    )
    assert art["_schema"] == "config"
    assert art["sub_game"] == 1
    assert art["config_sha256"] == "deadbeef"


def test_log_artifact_holds_records_and_agreement() -> None:
    art = artifacts.build_log(
        **COMMON, sub_game=1, summary={"turns": 12}, records=[{"step": 1}],
        mutual_agreement={"signature": "s"}, links={},
    )
    assert art["_schema"] == "log"
    assert art["records"] == [{"step": 1}]
    assert art["mutual_agreement"]["signature"] == "s"


def test_result_artifact_holds_final_result() -> None:
    art = artifacts.build_result(
        **COMMON, sub_games=[{"sub_game": 1, "outcome": "capture"}], final_result="police",
        mutual_agreement={"signature": "s"}, links={},
    )
    assert art["_schema"] == "result"
    assert art["final_result"] == "police"
