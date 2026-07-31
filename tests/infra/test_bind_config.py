"""Server/client bind params come from config, not literals (FR-E1, F13)."""

from __future__ import annotations

from pathlib import Path

from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_client import McpTransport
from cipherchase.infra.mcp_server import serve_params
from cipherchase.shared.config import ConfigManager
from cipherchase.shared.gatekeeper import ApiGatekeeper

CONFIG = Path(__file__).resolve().parents[2] / "config"


class _AllowAll:
    def allow(self, service: str) -> bool:
        return True


def test_serve_params_read_host_and_port_from_config() -> None:
    cfg = ConfigManager.load(CONFIG / "police")
    assert serve_params(cfg) == {
        "transport": "http", "host": "127.0.0.1", "port": 8001, "show_banner": False,
        "stateless_http": True,  # league interop: accept sessionless JSON-RPC peers too
    }


def test_client_from_config_reads_url_and_timeouts() -> None:
    cfg = ConfigManager.load(CONFIG / "thief")
    gate = ApiGatekeeper(_AllowAll(), sleep=lambda _s: None)
    transport = McpTransport.from_config(
        cfg, Inboxes(cfg.queue_maxsize), gate=gate, caller=lambda *_a: {"ok": True}
    )
    assert transport.opponent_url == "http://127.0.0.1:8001/mcp"  # /mcp path — the contract
    assert transport.connect_timeout == cfg.network["connect_timeout_seconds"]
    assert transport.retry_interval == cfg.network["retry_interval_seconds"]


def test_loopback_needs_no_socket_or_key() -> None:
    from fakes.fake_transport import make_pair

    a, b = make_pair()
    a.send_turn({"step": 1, "sender": "police"})
    assert b.poll_turn_or_none(timeout=0.1)["step"] == 1  # no network, no key, no live peer
