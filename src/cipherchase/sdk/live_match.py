"""Live match control for the arena server (SH-6/7/8) — socket-free, testable core.

The HTTP layer (`scripts/viz_server.py`) is a thin router over this: `spectate()`
tails the active match's JSONL spool (skipping a torn final line), `start()` shape-
validates the request and spawns ONE daemon peer thread at a time (a second start
while alive → 409). The runner is injectable so the control logic is tested without
sockets; the default runner drives a real `run_peer` with a `JsonlListener`.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_ROLES = ("police", "thief")


def valid_opponent_url(url: str) -> bool:
    """Shape check only — scheme http/https, a host, path ending /mcp. No fetch."""
    try:
        parsed = urlparse(url)
    except (ValueError, AttributeError):
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc) \
        and parsed.path.endswith("/mcp")


def read_spool(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    frames: list[dict[str, Any]] = []
    for line in p.read_text().splitlines():
        try:
            frames.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a torn final line (writer mid-flush) — tolerated
    return frames


def _default_runner(role: str, url: str, spool: str) -> None:  # pragma: no cover — sockets
    from cipherchase.sdk.sdk import SimulationSdk
    from cipherchase.sdk.spectate import JsonlListener
    from cipherchase.shared.config import ConfigManager
    cfg = ConfigManager.load(f"config/{role}")
    cfg.private["network"]["opponent_url"] = url
    SimulationSdk.run_peer(cfg, natural_role=role, listener=JsonlListener(spool))


class MatchController:
    def __init__(self, spool: str | Path, runner: Callable | None = None) -> None:
        self.spool = Path(spool)
        self._runner = runner or _default_runner
        self._thread: threading.Thread | None = None

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def spectate(self) -> dict[str, Any]:
        frames = read_spool(self.spool)
        return {"live": self.running() or bool(frames), "frames": frames}

    def start(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if self.running():
            return 409, {"ok": False, "error": "match already running"}
        role, url = body.get("role"), body.get("opponent_url", "")
        if role not in _ROLES or not valid_opponent_url(url):
            return 400, {"ok": False, "error": "bad role or opponent_url"}
        self.spool.write_text("")  # fresh spool for the new match
        self._thread = threading.Thread(
            target=self._runner, args=(role, url, str(self.spool)), daemon=True)
        self._thread.start()
        return 200, {"ok": True, "stream": "/api/spectate"}
