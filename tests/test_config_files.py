"""Committed-config integrity guards (FR-I1/I2, F2, NFR-6)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from cipherchase.shared.version import VERSION

CONFIG = Path(__file__).resolve().parents[1] / "config"
ROLES = ["police", "thief"]


@pytest.mark.parametrize("role", ROLES)
def test_game_toml_version_matches_single_source(role: str) -> None:
    data = tomllib.loads((CONFIG / role / "game.toml").read_text())
    assert data["version"] == VERSION


def test_shared_game_json_is_byte_identical_both_roles() -> None:
    # F2 zero-trust: the signed constitution must match byte-for-byte.
    assert (CONFIG / "police" / "game.json").read_bytes() == (
        CONFIG / "thief" / "game.json"
    ).read_bytes()


def test_game_json_has_mandatory_sections() -> None:
    data = json.loads((CONFIG / "police" / "game.json").read_text())
    for key in (
        "board_and_agents",
        "movement_and_barriers",
        "scoring",
        "pheromones",
        "network_and_league",
        "rate_limiter_gatekeeper",
        "commit_payload_spec",
    ):
        assert key in data, f"missing {key}"
    assert data["board_and_agents"]["board_size"] == 7
    assert data["scoring"]["capture_cop"] == 20


@pytest.mark.parametrize("role", ROLES)
def test_game_toml_role_and_ports(role: str) -> None:
    data = tomllib.loads((CONFIG / role / "game.toml").read_text())
    assert data["game"]["role"] == role
    assert data["network"]["my_port"] != 0
