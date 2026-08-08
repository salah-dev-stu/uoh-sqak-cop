"""Real MCP client to the opponent's FastMCP server (FR-B3, F1).

Outbound calls retry every ``retry_interval_seconds`` until
``connect_timeout_seconds`` (peers start seconds apart — never fail on the
first refused connection), are gatekept (``service="mcp"``), and send the
audit under the reference's ``payload`` arg key. The live HTTP caller is
excluded from coverage (needs a running peer).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from cipherchase.exceptions import TransportError
from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.transport_base import BaseTransport, Message

Caller = Callable[[str, str, Message], Message]


def _http_caller(url_of: Callable[[], str]) -> Caller:  # pragma: no cover
    from fastmcp import Client

    def call(tool: str, arg_key: str, message: Message) -> Message:
        async def _go() -> Message:
            async with Client(url_of()) as client:  # re-read: it changes per sub-game
                result = await client.call_tool(tool, {arg_key: message})
            return dict(result.data) if result.data is not None else {}

        return asyncio.run(_go())

    return call


class McpTransport(BaseTransport):
    def __init__(
        self,
        opponent_url: str,
        inboxes: Inboxes,
        *,
        gate: Any,
        connect_timeout: float,
        retry_interval: float,
        caller: Caller | None = None,
        now: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(inboxes)
        self.opponent_url = opponent_url
        self.gate = gate
        self.connect_timeout = connect_timeout
        self.retry_interval = retry_interval
        self._caller = caller or _http_caller(lambda: self.opponent_url)
        import time as _time

        self._now = now or _time.monotonic
        self._sleep = sleep or _time.sleep

    @classmethod
    def from_config(cls, cfg: Any, inboxes: Inboxes, *, gate: Any, caller: Caller | None = None):
        net = cfg.network
        return cls(
            net["opponent_url"], inboxes, gate=gate,
            connect_timeout=net["connect_timeout_seconds"],
            retry_interval=net["retry_interval_seconds"], caller=caller,
        )

    def _send(self, tool: str, arg_key: str, message: Message) -> Message:
        deadline = self._now() + self.connect_timeout
        while True:
            try:
                return self.gate.execute(
                    lambda: self._caller(tool, arg_key, message), service="mcp", action=tool
                )
            except Exception as exc:
                if self._now() >= deadline:
                    raise TransportError(f"{tool} -> {self.opponent_url}: {exc}") from exc
                self._sleep(self.retry_interval)
