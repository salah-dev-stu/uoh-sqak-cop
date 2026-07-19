"""ConfigManager: load + merge private TOML with signed JSON (FR-I1/I2)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.domain.negotiation import config_sha256
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_load_reads_all_three_files() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    assert cfg.shared["board_and_agents"]["board_size"] == 7
    assert cfg.private["network"]["my_port"] == 8001
    assert cfg.rate_limits["gmail"]["capacity"] == 30


def test_config_sha_matches_signed_shared() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    assert cfg.config_sha256 == config_sha256(cfg.shared)


def test_role_and_network_helpers() -> None:
    cfg = ConfigManager.load(CONFIG / "thief")
    assert cfg.role == "thief"
    assert cfg.opponent_url == "http://127.0.0.1:8001/mcp"
    assert cfg.my_port == 8002
    assert cfg.queue_maxsize == 100


def test_private_toml_never_overrides_signed_json() -> None:
    # A malicious private key must not win over the signed constitution.
    shared = {"board_and_agents": {"board_size": 7}}
    private = {"board_and_agents": {"board_size": 99}, "network": {"my_port": 8001}}
    cfg = ConfigManager(shared, private, {})
    assert cfg.merged["board_and_agents"]["board_size"] == 7
