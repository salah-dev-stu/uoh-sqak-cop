"""Auto-firing a league report (rule 32) without ever losing the evidence.

A credential or quota problem must be loud and must not unwind the run: the
artifacts describe a game that really happened and they are the only copy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cipherchase.shared.gatekeeper import ApiGatekeeper

Json = dict[str, Any]

def gmail_backend() -> Any:  # pragma: no cover — real credentials + network
    """The live Gmail sender, or None when no token is configured."""
    token = os.environ.get("CIPHERCHASE_GMAIL_TOKEN", "")
    if not token or not Path(token).expanduser().exists():
        return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(Path(token).expanduser()))
    service = build("gmail", "v1", credentials=creds)
    return lambda raw: service.users().messages().send(
        userId="me", body={"raw": raw}).execute()


def mail_report(cfg: Any, gate: ApiGatekeeper, outcome: Json, paths: list[Path], backend: Any) -> None:
    """Auto-fire the report (rule 32), but never destroy a played series' evidence.

    A credential or quota problem must be loud and must not unwind the run: the
    artifacts describe a game that really happened, and they are the only copy.
    """
    from cipherchase.infra.email_sender import GmailSender

    email = cfg.private["email"]
    try:
        GmailSender(gate, recipient=email["recipient"], sender=email.get("sender", ""),
                    backend=backend).send(
            email["subject_template"].format(game_id=outcome["game_id"]), paths)
    except Exception as exc:  # noqa: BLE001 — any send failure, reported not raised
        print(f"REPORT NOT SENT — {type(exc).__name__}: {exc}\n"
              f"  artifacts are on disk; re-send with scripts/send_sample_report.py")
