"""Auto-firing a league report (rule 32) without ever losing the evidence.

A credential or quota problem must be loud and must not unwind the run: the
artifacts describe a game that really happened and they are the only copy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cipherchase.exceptions import ConfigError
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


def mail_report(cfg: Any, gate: ApiGatekeeper, result: Json, backend: Any) -> None:
    """Auto-fire the report (rule 32), but never destroy a played series' evidence.

    The mail carries the RESULT only, in the kit's shape (SPEC §6.1): canonical
    bytes as body and as one named attachment. The other artifacts live in the
    repo and are reached through the result's links.

    A credential or quota problem must be loud and must not unwind the run: the
    artifacts describe a game that really happened, and they are the only copy.
    """
    from cipherchase.report.mail_body import build_report_mail

    email = cfg.private["email"]
    try:
        raw = build_report_mail(
            email["subject_template"].format(game_id=result["game_id"]), result,
            recipient=email["recipient"], sender=email.get("sender", ""))
        if backend is None:
            raise ConfigError("no Gmail backend configured (run scripts/gmail_oauth_setup.py)")
        gate.execute(lambda: backend(raw), service="gmail", action="send")
    except Exception as exc:  # noqa: BLE001 — any send failure, reported not raised
        print(f"REPORT NOT SENT — {type(exc).__name__}: {exc}\n"
              f"  artifacts are on disk; re-send with scripts/send_sample_report.py")
