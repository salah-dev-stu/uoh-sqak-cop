"""Gmail report sender (FR-G2, F11). JSON attachments, gatekept, mocked."""

from __future__ import annotations

import base64

import pytest

from cipherchase.exceptions import ConfigError
from cipherchase.infra.email_sender import GmailSender


class _Gate:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def execute(self, fn, *, service, action):  # type: ignore[no-untyped-def]
        self.calls.append((service, action))
        return fn()


def test_send_attaches_json_and_routes_through_gatekeeper(tmp_path) -> None:
    art = tmp_path / "log_x.json"
    art.write_text('{"a": 1}')
    captured: dict[str, str] = {}
    gate = _Gate()
    sender = GmailSender(
        gate, recipient="rmisegal+uoh26finalgame@gmail.com", sender="uoh-sqak@example.com",
        backend=lambda raw: captured.update(raw=raw) or {"id": "1"},
    )

    result = sender.send("CipherChase report", [art])

    assert result == {"id": "1"}
    assert gate.calls == [("gmail", "send")]
    decoded = base64.urlsafe_b64decode(captured["raw"]).decode()
    assert "log_x.json" in decoded and "attachment" in decoded


def test_send_without_backend_raises_config_error(tmp_path) -> None:
    sender = GmailSender(_Gate(), recipient="x@y.z", backend=None)
    with pytest.raises(ConfigError):
        sender.send("s", [])
