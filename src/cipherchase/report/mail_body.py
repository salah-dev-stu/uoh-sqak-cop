"""The counted-series report mail, in the shape the league pins (SPEC §6/§6.1).

One mail per team per counted series: the result JSON as the BODY in exact
canonical bytes, and the same bytes as a single named attachment. The other
artifacts are never mailed — the grader reaches them through the result's
``links``.

The rule that costs points is the canonical one: the grader compares the emails,
not just the hashes, so a pretty-printed re-serialization can fail even when two
teams' signatures agree. Both parts are therefore rendered from ONE call to
``canonical_json`` — reading the stored artifact back would reintroduce exactly
that bug, because we store artifacts pretty-printed for human review.
"""

from __future__ import annotations

import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from cipherchase.domain.canonical import canonical_json


def report_filename(result: dict[str, Any]) -> str:
    """``result_<a>-vs-<b>.json`` — both teams derive the same name."""
    return f"result_{result['game_id']}.json"


def build_report_mail(
    subject: str, result: dict[str, Any], *, recipient: str, sender: str = ""
) -> str:
    """Base64url-encoded RFC-822 message carrying the result once, canonically."""
    payload = canonical_json(result)  # the single source of body AND attachment
    message = MIMEMultipart()
    message["To"] = recipient
    if sender:
        message["From"] = sender
    message["Subject"] = subject
    message.attach(MIMEText(payload, "plain", "utf-8"))
    part = MIMEApplication(payload.encode("utf-8"), _subtype="json")
    part.add_header("Content-Disposition", "attachment", filename=report_filename(result))
    message.attach(part)
    return base64.urlsafe_b64encode(message.as_bytes()).decode()
