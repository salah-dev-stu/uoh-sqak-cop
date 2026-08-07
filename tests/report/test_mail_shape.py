"""The emailed report's shape is pinned by the kit (SPEC §6/§6.1), not by taste.

The grader compares the EMAILS, not just the hashes: one counted series, one
mail, the result JSON as the body in exact canonical bytes, and the same bytes as
a single named attachment. In EX06 two teams' hashes matched and one nearly
scored 0 because its mail was a pretty-printed re-serialization.

Ours attached all six artifacts with no body at all.
"""

from __future__ import annotations

import base64
import email
import json
from pathlib import Path

from cipherchase.domain.canonical import canonical_json
from cipherchase.report.mail_body import build_report_mail

RESULT = {"_schema": "result", "game_id": "imreeyal-vs-uoh-sqak",
          "groups": ["imreeyal", "uoh-sqak"], "hint": "שלום 🎯",
          "mutual_agreement": {"sha256": "ab" * 32}}


def _parse(raw: str):
    return email.message_from_bytes(base64.urlsafe_b64decode(raw))


def test_the_body_is_the_exact_canonical_bytes() -> None:
    raw = build_report_mail("subject", RESULT, recipient="a@b.c", sender="s@b.c")
    msg = _parse(raw)
    body = next(p for p in msg.walk() if p.get_content_type() == "text/plain")
    text = body.get_payload(decode=True).decode("utf-8")
    assert text == canonical_json(RESULT), "never a pretty-printed re-serialization"
    assert json.loads(text) == RESULT


def test_exactly_one_attachment_and_it_is_the_same_bytes() -> None:
    raw = build_report_mail("subject", RESULT, recipient="a@b.c", sender="s@b.c")
    msg = _parse(raw)
    files = [p for p in msg.walk() if p.get_filename()]
    assert len(files) == 1, "one named attachment, not six artifacts"
    assert files[0].get_filename() == "result_imreeyal-vs-uoh-sqak.json"
    attached = files[0].get_payload(decode=True).decode("utf-8")
    body = next(p for p in msg.walk() if p.get_content_type() == "text/plain")
    assert attached == body.get_payload(decode=True).decode("utf-8"), (
        "body and attachment must come from ONE canonical source, or they differ")


def test_non_ascii_survives_the_round_trip() -> None:
    # canonical_json is ensure_ascii=False, so the mail must carry UTF-8 intact.
    raw = build_report_mail("subject", RESULT, recipient="a@b.c", sender="s@b.c")
    body = next(p for p in _parse(raw).walk() if p.get_content_type() == "text/plain")
    assert "שלום 🎯" in body.get_payload(decode=True).decode("utf-8")


def test_the_file_on_disk_is_not_the_source_of_the_bytes(tmp_path: Path) -> None:
    # The trap: our artifacts are stored pretty-printed. Canonicalizing the body
    # while attaching the stored file verbatim yields two different payloads.
    stored = tmp_path / "result_imreeyal-vs-uoh-sqak.json"
    stored.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False), encoding="utf-8")
    assert stored.read_text(encoding="utf-8") != canonical_json(RESULT)
    raw = build_report_mail("subject", RESULT, recipient="a@b.c", sender="s@b.c")
    files = [p for p in _parse(raw).walk() if p.get_filename()]
    assert files[0].get_payload(decode=True).decode("utf-8") == canonical_json(RESULT)
