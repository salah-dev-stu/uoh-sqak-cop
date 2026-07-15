"""Real MCP client to the opponent's FastMCP server (FR-B3).

The transport is split from its wire mechanism: ``_caller`` performs the actual
tool call. Tests inject a stub caller; production uses ``_http_caller`` (a live
FastMCP HTTP client — excluded from coverage as it needs a running peer).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from cipherchase.exceptions import TransportError
from cipherchase.infra.inboxes import Inboxes
from cipherchase.infra.transport_base import BaseTransport, Message

Caller = Callable[[str, Message], Message]


def _http_caller(opponent_url: str, timeout: float) -> Caller:  # pragma: no cover
    from fastmcp import Client

    def call(tool: str, message: Message) -> Message:
        async def _go() -> Message:
            async with Client(opponent_url) as client:
                result = await client.call_tool(tool, {"message": message})
            return dict(result.data) if result.data is not None else {}

        try:
            return asyncio.run(_go())
        except Exception as exc:
            raise TransportError(f"{tool} -> {opponent_url} failed: {exc}") from exc

    return call


class McpTransport(BaseTransport):
    def __init__(
        self,
        opponent_url: str,
        inboxes: Inboxes,
        *,
        caller: Caller | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(inboxes)
        self.opponent_url = opponent_url
        self.timeout = timeout
        self._caller = caller or _http_caller(opponent_url, timeout)

    def _send(self, tool: str, message: Message) -> Message:
        return self._caller(tool, message)
