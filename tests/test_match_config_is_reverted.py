"""Match-local config must never reach a test run — or the repo (F14).

Playing a league game means editing the shipped config: the opponent's URL, our
tunnel, `agreed_between`, and turning mail on. Left in place those edits point
the suite at a live remote and at a real inbox, which has now cost three runs —
eleven "failures" that were nothing but a config the operator forgot to revert,
and fifteen minutes of retry timeouts to discover it.

Worse than the wasted time: `enabled = true` with a real token would mail a test
run's artifacts to whoever `recipient` names.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[1] / "config"
ROLES = ("police", "thief")


def _toml(role: str) -> dict:
    return tomllib.loads((CONFIG / role / "game.toml").read_text())


@pytest.mark.parametrize("role", ROLES)
def test_the_opponent_is_localhost_not_a_live_peer(role: str) -> None:
    url = _toml(role)["network"]["opponent_url"]
    assert "127.0.0.1" in url or "localhost" in url, (
        f"config/{role} still points at {url} — revert the match edits "
        "(git checkout -- config/) before committing or testing")


@pytest.mark.parametrize("role", ROLES)
def test_no_tunnel_url_is_committed(role: str) -> None:
    assert _toml(role)["network"]["public_url"] == "", (
        f"config/{role} still advertises a session tunnel; it is dead by now")


@pytest.mark.parametrize("role", ROLES)
def test_mail_is_off_by_default(role: str) -> None:
    # A league run turns this on deliberately, for one series, then turns it off.
    assert _toml(role)["email"]["enabled"] is False, (
        f"config/{role} would auto-mail on any run — including a test run")
