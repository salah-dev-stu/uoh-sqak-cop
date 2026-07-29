#!/usr/bin/env python3
"""Serve the live 3D arena: fresh replay per request + live league match room.

Run from the repo root:  uv run python scripts/viz_server.py
Then open http://localhost:8777 — "New match" plays a fresh game in 3D, and the
match-room panel starts a real league match against a peer URL and streams it
live. Bound to 127.0.0.1 only (SH-8): the match room is never a remote hole.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
from make_replay_data import capture  # noqa: E402

from cipherchase.sdk.live_match import MatchController  # noqa: E402

PORT = 8777
# per-process spool: two instances on one machine never clobber each other's stream
MATCH = MatchController(
    Path(tempfile.gettempdir()) / f"cipherchase_spectate_{os.getpid()}.jsonl")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory="viz", **kwargs)

    def end_headers(self) -> None:  # dev server: never let modules go stale
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/game"):
            self._json(200, capture(randomize=True))
        elif self.path.startswith("/api/spectate"):
            self._json(200, MATCH.spectate())
        else:
            super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/match"):
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            status, resp = MATCH.start(json.loads(self.rfile.read(length) or b"{}"))
        except (ValueError, json.JSONDecodeError):
            status, resp = 400, {"ok": False, "error": "bad json"}
        except Exception as exc:  # never leak an HTML traceback
            status, resp = 500, {"ok": False, "error": str(exc)}
        self._json(status, resp)

    def log_message(self, *args) -> None:  # keep the console quiet
        return


def serve(port: int = PORT, tries: int = 10) -> None:
    """Bind 127.0.0.1 on the first free port from ``port`` — never a raw traceback."""
    for candidate in range(port, port + tries):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
        except OSError:
            print(f"port {candidate} busy — trying {candidate + 1}")
            continue
        print(f"CipherChase 3D arena → http://localhost:{candidate}  (Ctrl-C to stop)")
        server.serve_forever()
        return
    raise SystemExit(f"no free port in {port}-{port + tries - 1} — close another instance")


if __name__ == "__main__":
    serve()
