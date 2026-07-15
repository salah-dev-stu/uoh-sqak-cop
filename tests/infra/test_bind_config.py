"""Server/client bind params come from config, not literals (FR-E1, F13)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_client import McpTransport
from cipherchase.infra.mcp_server import serve_params
from cipherchase.shared.config import ConfigManager

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_serve_params_read_host_and_port_from_config() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    assert serve_params(cfg) == {"transport": "http", "host": "127.0.0.1", "port": 8001}


def test_client_targets_opponent_url_from_config() -> None:
    cfg = ConfigManager.load(CONFIG / "thief")
    transport = McpTransport(cfg.opponent_url, Inboxes(cfg.queue_maxsize), caller=lambda t, m: {})
    assert transport.opponent_url == "http://127.0.0.1:8001"


def test_loopback_needs_no_socket_or_key() -> None:
    from fakes.fake_transport import make_pair

    a, b = make_pair()
    a.send_turn({"step": 1, "sender": "police"})
    assert b.poll_turn(timeout=0.1)["step"] == 1  # no network, no key, no live peer
