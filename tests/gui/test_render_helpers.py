"""Pure helpers behind the Tkinter Live GUI + Replay Viewer (F12)."""

from __future__ import annotations

import json

from cipherchase.gui.replay import load_records
from cipherchase.gui.window import banner_text


def test_banner_text_shows_role_step_and_belief_peak() -> None:
    text = banner_text(role="police", step=7, believed_cell=(3, 4))
    assert "police" in text and "7" in text and "(3, 4)" in text


def test_load_records_reads_a_log_artifact(tmp_path) -> None:
    log = tmp_path / "log_x_g01.json"
    log.write_text(json.dumps({"records": [{"payload": {"step": 1}}]}))
    assert load_records(log)[0]["payload"]["step"] == 1
