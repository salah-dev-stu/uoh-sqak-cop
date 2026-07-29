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


def test_verify_command_prints_verdict_and_exit_codes(tmp_path, capsys) -> None:
    import json
    from pathlib import Path
    sample = sorted((Path("docs/sample-run")).glob("log_*police*_g01.json"))[0]
    assert main(["verify", "--log", str(sample)]) == 0
    assert "Verified OK" in capsys.readouterr().out
    log = json.loads(sample.read_text())
    log["records"][0]["nonce"] = "0" * 32  # forged nonce
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(log))
    assert main(["verify", "--log", str(bad)]) == 1
    assert "TAMPERED" in capsys.readouterr().out
