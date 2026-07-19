#!/usr/bin/env python3
"""Serve the live 3D arena + generate a FRESH game per request.

Run from the repo root:  uv run python scripts/viz_server.py
Then open http://localhost:8777 — "New match" plays a brand-new game in 3D.
"""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
from make_replay_data import capture  # noqa: E402

PORT = 8777


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory="viz", **kwargs)

    def end_headers(self) -> None:  # dev server: never let modules go stale
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/game"):
            body = json.dumps(capture(randomize=True)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args) -> None:  # keep the console quiet
        return


if __name__ == "__main__":
    print(f"CipherChase 3D arena → http://localhost:{PORT}  (Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
