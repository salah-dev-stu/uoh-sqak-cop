"""Artifact filenames + on-disk write (FR-G1, F11)."""

from __future__ import annotations

import json

from cipherchase.report import artifacts
from cipherchase.report.emit import write_all

ID = "uoh-sqak-police-abc"
COMMON = {"game_id": ID, "game_uid": "abc123", "generated_at": "2026-08-01T00:00:00Z"}


def _four() -> list[dict]:
    return [
        artifacts.build_declaration(**COMMON, groups=["a", "b"], num_sub_games=1, max_tokens=1, links={}),
        artifacts.build_config(**COMMON, sub_game=1, shared_config={}, config_sha256="s", links={}),
        artifacts.build_log(**COMMON, sub_game=1, summary={}, records=[], mutual_agreement={}, links={}),
        artifacts.build_result(**COMMON, sub_games=[], final_result="tie", mutual_agreement={}, links={}),
    ]


def test_write_all_uses_the_four_canonical_filenames(tmp_path) -> None:
    names = {p.name for p in write_all(tmp_path, _four())}
    assert names == {
        f"declaration_{ID}.json",
        f"config_{ID}_g01.json",
        f"log_{ID}_g01.json",
        f"result_{ID}.json",
    }


def test_written_files_are_valid_json(tmp_path) -> None:
    paths = write_all(tmp_path, _four())
    schemas = {json.loads(p.read_text())["_schema"] for p in paths}
    assert schemas == {"declaration", "config", "log", "result"}
