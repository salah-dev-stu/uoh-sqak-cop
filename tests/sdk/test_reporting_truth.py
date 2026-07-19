"""P0 reporting truth (IH-6/7, IH-13..16): gate wired, Step-0 real, email real."""

from __future__ import annotations

from pathlib import Path

import pytest

from cipherchase.exceptions import IncompatibleVersionError
from cipherchase.peer.declaration import verify_declaration
from cipherchase.sdk.sdk import SimulationSdk
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"
AT = "2026-08-01T00:00:00Z"


def test_config_load_runs_the_startup_version_check(tmp_path) -> None:
    src = CONFIG / "police"
    bad = tmp_path / "police"
    bad.mkdir()
    for name in ("game.json", "rate_limits.json"):
        (bad / name).write_bytes((src / name).read_bytes())
    toml = (src / "game.toml").read_text().replace('version = "1.00"', 'version = "9.99"')
    (bad / "game.toml").write_text(toml)
    with pytest.raises(IncompatibleVersionError):
        ConfigManager.load(bad)


def test_declaration_artifact_embeds_a_verifiable_step0() -> None:
    arts = SimulationSdk.run_self_match(ConfigManager.load(CONFIG / "police"), generated_at=AT)
    step0 = arts["declaration"]["step0"]
    assert verify_declaration(step0) is True
    assert step0["team"] == "uoh-sqak"
    assert step0["git_commit"]  # bound per-game commit hash (F5)
    assert step0["system"]["os"]
    assert step0["llm"]["provider"] == "template"


def test_git_probe_degrades_to_unknown_when_gated_out() -> None:
    from unittest.mock import MagicMock

    from cipherchase.sdk.sdk import _git_commit

    gate = MagicMock()
    gate.execute.side_effect = RuntimeError("no git here")
    assert _git_commit(gate) == "unknown"


def test_log_artifact_carries_the_gatekeeper_ledger() -> None:
    arts = SimulationSdk.run_self_match(ConfigManager.load(CONFIG / "police"), generated_at=AT)
    ledger = arts["log"]["summary"]["gatekeeper_ledger"]
    assert any(e["service"] == "subprocess" for e in ledger)  # git hash went through the gate


def test_email_step_fires_through_the_gate_when_enabled(tmp_path) -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    cfg.private["email"]["enabled"] = True
    sent: dict = {}
    paths = SimulationSdk.write_reports(
        cfg, tmp_path, generated_at=AT, email_backend=lambda raw: sent.update(raw=raw) or {"id": "1"}
    )
    assert len(paths) == 4
    assert sent, "enabled email must send the 4 attachments"


def test_email_step_skipped_when_disabled(tmp_path) -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    sent: dict = {}
    SimulationSdk.write_reports(
        cfg, tmp_path, generated_at=AT, email_backend=lambda raw: sent.update(raw=raw)
    )
    assert not sent
