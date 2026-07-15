#!/usr/bin/env python3
"""One-time Gmail OAuth consent (scope ``gmail.send`` ONLY) → token.json (F10/F11).

Run once locally:  ``uv run --extra real python scripts/gmail_oauth_setup.py``
Opens a browser for consent and writes the revocable token the report sender
reuses. ``credentials.json`` + ``token.json`` are git-ignored — NEVER committed.
Lives in scripts/ (outside the package) so the google import can't trip the
gatekeeper meta-test, and it is never run in CI.
"""

from __future__ import annotations

import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> int:  # pragma: no cover - interactive browser consent, real creds
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = os.environ.get("CIPHERCHASE_GMAIL_CREDENTIALS", "credentials.json")
    token_path = os.environ.get("CIPHERCHASE_GMAIL_TOKEN", "token.json")
    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)
    Path(token_path).write_text(creds.to_json(), encoding="utf-8")
    print(f"saved Gmail token to {token_path} (git-ignored, scope gmail.send).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
