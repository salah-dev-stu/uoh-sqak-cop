"""Replay Viewer (FR-G5, F12) — re-verify a logged game, show OK/TAMPERED.

``load_records`` is unit-tested; ``run_replay`` renders with Tkinter and is
excluded from coverage (needs a display — screenshot captured manually).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cipherchase.gui.replay_data import BAD, replay_verdict, verify_records


def load_records(log_path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(log_path).read_text(encoding="utf-8"))["records"]


def run_replay(log_path: str | Path) -> Any:  # pragma: no cover
    import tkinter as tk

    records = load_records(log_path)
    verdict = replay_verdict(records)
    root = tk.Tk()
    root.title("CipherChase — Replay Viewer")
    colour = "#c0392b" if verdict == BAD else "#27ae60"
    tk.Label(root, text=verdict, bg=colour, fg="white", font=("Menlo", 24)).pack(fill="x")
    for step in verify_records(records):
        tk.Label(root, text=f"step {step['step']}: {step['status']}").pack(anchor="w")
    root.mainloop()
    return root
