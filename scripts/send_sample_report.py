#!/usr/bin/env python3
"""The ONE real ``gmail.send`` (F11) — NOT part of pytest/CI.

Emails the committed ``docs/sample-run/`` 4 JSON artifacts as attachments to the
course address, routed through the gatekeeper. Requires a token.json from
scripts/gmail_oauth_setup.py. Run:
    uv run --extra real python scripts/send_sample_report.py
Both peers must send (or neither is scored) — run this from each repo.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("src")))
from cipherchase.infra.email_sender import GmailSender  # noqa: E402
from cipherchase.shared.config import ConfigManager  # noqa: E402
from cipherchase.shared.gatekeeper import ApiGatekeeper  # noqa: E402


def _real_backend(token_path: str):  # pragma: no cover - real network + creds
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path)
    service = build("gmail", "v1", credentials=creds)
    return lambda raw: service.users().messages().send(userId="me", body={"raw": raw}).execute()


def main() -> int:  # pragma: no cover - real send
    cfg = ConfigManager.load(os.environ.get("CIPHERCHASE_CONFIG", "config/police"))
    token = os.environ["CIPHERCHASE_GMAIL_TOKEN"]
    gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)
    email = cfg.private["email"]
    sender = GmailSender(
        gate, recipient=email["recipient"], sender=email.get("sender", ""),
        backend=_real_backend(token),
    )
    files = sorted(Path("docs/sample-run").glob("*.json"))
    result = sender.send(f"CipherChase report {cfg.role}", files)
    print("sent", len(files), "attachments →", email["recipient"], "|", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
