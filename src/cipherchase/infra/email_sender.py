"""Gmail report sender (FR-G2, F11).

Emails the 4 JSON artifacts as **attachments** (plaintext = 0) to the course
address, routed through the gatekeeper (``service="gmail"``). The real OAuth
``gmail.send`` backend is injected; tests inject a fake, so CI never sends.
Both peers send or neither is scored — enforced by the orchestrator.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any

from cipherchase.exceptions import ConfigError

Backend = Callable[[str], dict[str, Any]]


class GmailSender:
    def __init__(
        self, gate: Any, *, recipient: str, sender: str = "", backend: Backend | None = None
    ) -> None:
        self.gate = gate
        self.recipient = recipient
        self.sender = sender
        self.backend = backend

    def build_raw(self, subject: str, attachments: list[str | Path]) -> str:
        message = MIMEMultipart()
        message["To"] = self.recipient
        if self.sender:
            message["From"] = self.sender
        message["Subject"] = subject
        for item in attachments:
            path = Path(item)
            part = MIMEApplication(path.read_bytes(), _subtype="json")
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            message.attach(part)
        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    def send(self, subject: str, attachments: list[str | Path]) -> dict[str, Any]:
        if self.backend is None:
            raise ConfigError("no Gmail backend configured (run scripts/gmail_oauth_setup.py)")
        raw = self.build_raw(subject, attachments)
        backend = self.backend
        return self.gate.execute(lambda: backend(raw), service="gmail", action="send")
