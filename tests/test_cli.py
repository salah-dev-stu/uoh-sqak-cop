"""CLI entry — delegates to the SDK, holds no game logic (R1)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.cli import main

CONFIG = Path(__file__).resolve().parents[1] / "config"


def test_self_match_command_writes_four_reports(tmp_path, capsys) -> None:
    code = main(
        ["self-match", "--config", str(CONFIG / "police"), "--out", str(tmp_path),
         "--at", "2026-08-01T00:00:00Z"]
    )
    assert code == 0
    assert len(list(tmp_path.glob("*.json"))) == 4
    assert "result_" in capsys.readouterr().out


def test_unknown_command_errors() -> None:
    import pytest

    with pytest.raises(SystemExit):
        main(["nope"])


def test_main_module_is_importable() -> None:
    import cipherchase.__main__  # noqa: F401
