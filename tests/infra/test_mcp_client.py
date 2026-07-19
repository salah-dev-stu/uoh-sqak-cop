"""McpTransport — gated, retrying, reference arg keys (FR-B3, R3)."""

from __future__ import annotations

import pytest

from cipherchase.exceptions import TransportError
from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.mcp_client import McpTransport
from cipherchase.shared.gatekeeper import ApiGatekeeper


class _AllowAll:
    def allow(self, service: str) -> bool:
        return True


def _gate() -> ApiGatekeeper:
    return ApiGatekeeper(_AllowAll(), sleep=lambda _s: None)


def _transport(caller, now=None, sleep=None) -> McpTransport:
    return McpTransport(
        "http://peer:8002/mcp", Inboxes(maxsize=10), gate=_gate(),
        connect_timeout=1.0, retry_interval=0.1,
        caller=caller, now=now or (lambda: 0.0), sleep=sleep or (lambda _s: None),
    )


def test_sends_map_to_reference_tools_and_arg_keys() -> None:
    calls: list[tuple[str, str]] = []
    t = _transport(lambda tool, key, msg: calls.append((tool, key)) or {"ok": True})
    t.send_turn({"step": 1})
    t.send_audit({"sender": "thief"})
    t.exchange_agreement_push({"terms": {}})
    t.send_control({"kind": "enable"})
    assert calls == [
        ("receive_turn", "message"), ("submit_audit", "payload"),
        ("negotiate", "message"), ("receive_control", "message"),
    ]


def test_every_send_is_ledgered_by_the_gate() -> None:
    t = _transport(lambda *_a: {"ok": True})
    t.send_turn({"step": 1})
    assert t.gate.ledger[-1] == {"service": "mcp", "action": "receive_turn", "status": "ok"}


def test_retries_until_deadline_then_raises_transport_error() -> None:
    clock = {"t": 0.0}
    slept: list[float] = []

    def now() -> float:
        return clock["t"]

    def sleep(s: float) -> None:
        slept.append(s)
        clock["t"] += s

    def flaky(*_a):  # opponent not up yet — always refused
        raise ConnectionError("refused")

    t = _transport(flaky, now=now, sleep=sleep)
    with pytest.raises(TransportError):
        t.send_turn({"step": 1})
    assert len(slept) >= 9  # kept retrying every retry_interval until the deadline


def test_poll_reads_own_inboxes() -> None:
    t = _transport(lambda *_a: {"ok": True})
    t.inboxes.put_turn({"step": 9})
    assert t.poll_turn_or_none(0.1)["step"] == 9
    assert t.poll_turn_or_none(0.01) is None
